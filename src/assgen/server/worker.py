"""Background job worker.

Runs in a dedicated thread alongside the FastAPI server.  Jobs are pulled
from the SQLite `jobs` table by polling; this keeps the stack simple and
dependency-free (no Celery / Redis required for local use).

Architecture:
  WorkerThread → polls DB for QUEUED jobs (highest priority first)
               → dispatches to JobDispatcher
               → JobDispatcher imports the appropriate handler module and calls run()
               → handler updates progress via a provided callback
               → WorkerThread marks the job COMPLETED or FAILED
"""
from __future__ import annotations

import logging
import sqlite3
import threading
import time
import traceback
from typing import Any, Callable

from assgen.db import (
    JobStatus,
    record_model_usage,
    update_job_status,
)
from assgen.server.model_manager import ModelManager

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[float, str], None]


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

class JobDispatcher:
    """Maps job_type → handler and invokes it."""

    def dispatch(
        self,
        job: dict[str, Any],
        model_manager: ModelManager,
        progress_cb: ProgressCallback,
        conn: sqlite3.Connection,
    ) -> dict[str, Any]:
        job_type: str = job["job_type"]
        params: dict[str, Any] = job.get("params") or {}

        # Resolve the effective model (client override or catalog default)
        override_model = params.get("_model_id_override")
        if override_model:
            progress_cb(0.05, f"Checking model {override_model}…")
            model_path = model_manager.ensure_model(override_model, progress_cb=progress_cb)
            model_id = override_model
            record_model_usage(conn, model_id, job["id"])
        else:
            progress_cb(0.05, "Resolving model from catalog…")
            model_id, model_path = model_manager.ensure_for_job_type(
                job_type, progress_cb=progress_cb
            )
            if model_id:
                record_model_usage(conn, model_id, job["id"])

        if model_id:
            logger.info(
                "Dispatching job",
                extra={"job_id": job["id"], "job_type": job_type, "model_id": model_id},
            )

        progress_cb(0.22, "Model ready — starting inference…")

        # Try to find a specific handler; fall back to the stub handler
        handler = _load_handler(job_type)
        result = handler(
            job_type=job_type,
            params=params,
            model_id=model_id,
            model_path=str(model_path) if model_path else None,
            device=model_manager.device,
            progress_cb=progress_cb,
        )
        return result


def _load_handler(job_type: str) -> Callable[..., dict[str, Any]]:
    """
    Try to import assgen.server.handlers.<domain>_<subdomain>_<action>.
    Falls back to the generic stub handler if not found.
    """
    module_name = "assgen.server.handlers." + job_type.replace(".", "_")
    try:
        import importlib
        mod = importlib.import_module(module_name)
        return mod.run  # type: ignore[attr-defined]
    except ModuleNotFoundError:
        return _stub_handler


def _stub_handler(
    job_type: str,
    params: dict[str, Any],
    model_id: str | None,
    model_path: str | None,
    device: str,
    progress_cb: ProgressCallback,
) -> dict[str, Any]:
    """Placeholder handler used when a real handler hasn't been implemented yet."""
    logger.warning(
        "No concrete handler found — using stub",
        extra={"job_type": job_type},
    )
    for i in range(1, 6):
        progress_cb(0.10 + i * 0.18, f"Stub inference step {i}/5")
        time.sleep(0.2)
    return {
        "status": "stub",
        "job_type": job_type,
        "model_id": model_id,
        "note": "Stub handler — implement assgen/server/handlers/<job_type>.py to add real inference",
    }


# ---------------------------------------------------------------------------
# Worker thread
# ---------------------------------------------------------------------------

class WorkerThread(threading.Thread):
    """Single background worker that processes one job at a time."""

    POLL_INTERVAL = 2.0   # seconds between DB polls when idle
    WORKER_ID = "local-worker-0"

    def __init__(self, conn_factory: Callable[[], sqlite3.Connection], model_manager: ModelManager) -> None:
        super().__init__(name="assgen-worker", daemon=True)
        self._conn_factory = conn_factory
        self._model_manager = model_manager
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        logger.info("Worker started", extra={"worker_id": self.WORKER_ID})
        while not self._stop_event.is_set():
            conn = self._conn_factory()
            try:
                self._process_next(conn)
            except Exception:
                logger.error("Unexpected worker error:\n" + traceback.format_exc())
            finally:
                conn.close()
            self._stop_event.wait(timeout=self.POLL_INTERVAL)
        logger.info("Worker stopped", extra={"worker_id": self.WORKER_ID})

    def _process_next(self, conn: sqlite3.Connection) -> None:
        row = conn.execute(
            """
            SELECT * FROM jobs
            WHERE status = 'QUEUED'
            ORDER BY priority DESC, created_at ASC
            LIMIT 1
            """
        ).fetchone()
        if not row:
            return

        from assgen.db import _row_to_job  # avoid circular at module level
        job = _row_to_job(row)
        job_id = job["id"]

        update_job_status(conn, job_id, JobStatus.RUNNING, worker_id=self.WORKER_ID, progress=0.0)
        logger.info("Job started", extra={"job_id": job_id, "job_type": job["job_type"]})

        def progress_cb(pct: float, msg: str) -> None:
            update_job_status(conn, job_id, JobStatus.RUNNING, progress=pct, progress_message=msg)

        try:
            dispatcher = JobDispatcher()
            output = dispatcher.dispatch(job, self._model_manager, progress_cb, conn)
            update_job_status(conn, job_id, JobStatus.COMPLETED, progress=1.0, output=output)
            logger.info("Job completed", extra={"job_id": job_id})
        except Exception as exc:
            error_msg = traceback.format_exc()
            update_job_status(conn, job_id, JobStatus.FAILED, error=error_msg)
            logger.error("Job failed", extra={"job_id": job_id, "error": str(exc)})
