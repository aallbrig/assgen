"""HuggingFace model manager.

Responsible for:
- Resolving which model to use for a given job type (catalog lookup)
- Downloading models from the Hub into the local cache
- Tracking installed models in the SQLite database
- Reporting model status (configured / downloading / installed)
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from assgen.catalog import get_model_for_job, load_catalog
from assgen.config import get_models_cache_dir
from assgen.db import upsert_model

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[float, str], None]


# ---------------------------------------------------------------------------
# HuggingFace download progress helpers
# ---------------------------------------------------------------------------

def _make_hf_tqdm_class(cb: ProgressCallback, start_frac: float, end_frac: float) -> type:
    """Return a tqdm subclass that translates per-file download progress into *cb* calls.

    Each ``snapshot_download`` creates one tqdm instance per file.  We track
    how many files have been seen / completed to derive an overall 0–1 fraction
    within the [start_frac, end_frac] window and forward it to *cb*.

    Console output is suppressed (``disable=True``) — progress surfaces only
    through the callback.
    """
    try:
        from tqdm import tqdm as _TqdmBase
    except ImportError:
        return None  # type: ignore[return-value]

    state: dict[str, int] = {"files_seen": 0, "files_done": 0}

    class _HFTqdm(_TqdmBase):  # type: ignore[misc]
        def __init__(self, *args: object, **kwargs: object) -> None:
            kwargs["disable"] = True
            super().__init__(*args, **kwargs)
            state["files_seen"] += 1
            self._file_label: str = str(self.desc or "").split("/")[-1]

        def update(self, n: int = 1) -> None:
            super().update(n)
            if self.total:
                file_frac = min(1.0, self.n / self.total)
                total = max(state["files_seen"], state["files_done"] + 1)
                overall = (state["files_done"] + file_frac) / total
                frac = start_frac + overall * (end_frac - start_frac)
                label = self._file_label
                msg = f"Downloading {label}…" if label else "Downloading model files…"
                cb(round(frac, 4), msg)

        def close(self) -> None:
            super().close()
            state["files_done"] += 1

    return _HFTqdm

# ---------------------------------------------------------------------------
# Device detection
# ---------------------------------------------------------------------------

def detect_device(preference: str = "auto") -> str:
    if preference != "auto":
        return preference
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return "mps"
    except ImportError:
        pass
    return "cpu"


# ---------------------------------------------------------------------------
# Model manager
# ---------------------------------------------------------------------------

class ModelManager:
    """Manage HuggingFace model downloads, caching, and status tracking.

    One ``ModelManager`` is instantiated per server process and shared across
    all worker threads via the ``server_cfg`` stored in ``app.state``.

    Attributes:
        conn: SQLite connection used to persist model metadata.
        device: Resolved device string — ``"cuda"``, ``"mps"``, or ``"cpu"``.
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        device: str = "auto",
        server_cfg: dict | None = None,
    ) -> None:
        """Initialise the manager.

        Args:
            conn: An open SQLite connection (must have ``row_factory = sqlite3.Row``).
            device: Preferred device — ``"auto"`` detects CUDA/MPS/CPU at runtime.
            server_cfg: The loaded server configuration dict (used for allow-list
                enforcement).
        """
        self.conn = conn
        self.device = detect_device(device)
        self._cache_dir = get_models_cache_dir()
        self._server_cfg: dict = server_cfg or {}
        logger.info("ModelManager initialised", extra={"device": self.device})

    # ------------------------------------------------------------------
    # Download / install
    # ------------------------------------------------------------------

    def ensure_model(
        self,
        model_id: str,
        progress_cb: "ProgressCallback | None" = None,
    ) -> Path:
        """Download model if not already cached; return the local cache path.

        Args:
            model_id: HuggingFace model identifier in ``org/repo`` format.
            progress_cb: Optional ``(fraction: float, message: str) -> None``
                callback for surfacing download/check progress to the caller
                (e.g. to forward to the client via :func:`assgen.db.update_job_status`).

        Returns:
            Local ``Path`` to the directory containing the downloaded model.

        Raises:
            ValueError: If ``model_id`` is ``None`` or blocked by the allow-list.
            Exception: Re-raised from ``huggingface_hub.snapshot_download`` on
                network or authentication errors.
        """
        def _cb(frac: float, msg: str) -> None:
            if progress_cb:
                progress_cb(frac, msg)

        if model_id is None:
            raise ValueError("model_id is None — job type may not require a model")

        # Enforce allow-list before any I/O
        from assgen.server.validation import check_allow_list
        check_allow_list(model_id, self._server_cfg)

        cache_path = self._cache_dir / _safe_name(model_id)

        if cache_path.exists() and any(cache_path.iterdir()):
            logger.info("Model already cached", extra={"model_id": model_id})
            _cb(0.15, f"Model {model_id} already cached ✓")
            return cache_path

        _cb(0.05, f"Downloading {model_id} from HuggingFace Hub…")
        logger.info(
            "Downloading model from HuggingFace Hub",
            extra={"model_id": model_id, "cache_dir": str(cache_path)},
        )
        try:
            from huggingface_hub import snapshot_download
            tqdm_cls = _make_hf_tqdm_class(_cb, start_frac=0.05, end_frac=0.18)
            dl_kwargs: dict = dict(
                repo_id=model_id,
                local_dir=str(cache_path),
                local_dir_use_symlinks=False,
                ignore_patterns=["*.msgpack", "*.h5", "flax_*"],
            )
            if tqdm_cls is not None:
                dl_kwargs["tqdm_class"] = tqdm_cls
            snapshot_download(**dl_kwargs)
        except Exception as exc:
            logger.error("Model download failed", extra={"model_id": model_id, "error": str(exc)})
            raise

        _cb(0.20, f"Model {model_id} downloaded successfully ✓")

        now = datetime.now(timezone.utc).isoformat()
        size = _dir_size(cache_path)
        upsert_model(
            self.conn,
            model_id=model_id,
            local_path=str(cache_path),
            installed_at=now,
            size_bytes=size,
        )
        logger.info(
            "Model downloaded successfully",
            extra={"model_id": model_id, "size_bytes": size},
        )
        return cache_path

    def ensure_for_job_type(
        self,
        job_type: str,
        progress_cb: "ProgressCallback | None" = None,
    ) -> tuple[str | None, Path | None]:
        """Resolve the catalog model for *job_type* and ensure it is cached.

        Args:
            job_type: Dot-separated task identifier, e.g. ``"visual.model.create"``.
            progress_cb: Optional progress callback forwarded to :meth:`ensure_model`.

        Returns:
            A ``(model_id, local_path)`` tuple.  Both elements are ``None`` if
            the job type has no associated model (e.g. pure format-conversion).

        Raises:
            ValueError: If *job_type* is not found in the catalog.
        """
        entry = get_model_for_job(job_type)
        if not entry:
            raise ValueError(f"No catalog entry for job type: {job_type!r}")
        model_id = entry.get("model_id")
        if not model_id:
            return None, None  # e.g., format-conversion tasks
        path = self.ensure_model(model_id, progress_cb=progress_cb)
        return model_id, path

    # ------------------------------------------------------------------
    # Status / listing
    # ------------------------------------------------------------------

    def list_status(self) -> list[dict[str, Any]]:
        """Return status of every model in the catalog."""
        catalog = load_catalog()
        seen: dict[str, dict[str, Any]] = {}
        for job_type, entry in catalog.items():
            mid = entry.get("model_id") or "(none)"
            if mid not in seen:
                row = self.conn.execute(
                    "SELECT * FROM models WHERE model_id = ?", (mid,)
                ).fetchone()
                installed = bool(row and row["local_path"] and Path(row["local_path"]).exists())
                seen[mid] = {
                    "model_id": mid,
                    "name": entry.get("name", mid),
                    "installed": installed,
                    "local_path": row["local_path"] if row else None,
                    "installed_at": row["installed_at"] if row else None,
                    "last_used_at": row["last_used_at"] if row else None,
                    "size_bytes": row["size_bytes"] if row else None,
                    "job_types": [],
                }
            seen[mid]["job_types"].append(job_type)
        return list(seen.values())

    def install_all(self) -> None:
        """Download every model referenced in the catalog."""
        for mid in set(
            e["model_id"]
            for e in load_catalog().values()
            if e.get("model_id")
        ):
            try:
                self.ensure_model(mid)
            except Exception as exc:
                logger.error("Failed to install model", extra={"model_id": mid, "error": str(exc)})


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _safe_name(model_id: str) -> str:
    """Convert 'org/repo' to 'org--repo' for use as a directory name."""
    return model_id.replace("/", "--")


def _dir_size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
