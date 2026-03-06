"""FastAPI application factory for assgen-server."""
from __future__ import annotations

import logging
import sqlite3
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from assgen.config import load_server_config
from assgen.db import init_db, reset_stale_running_jobs
from assgen.server.model_manager import ModelManager
from assgen.server.routes.health import router as health_router
from assgen.server.routes.jobs import router as jobs_router
from assgen.server.routes.models import router as models_router
from assgen.server.worker import WorkerThread

logger = logging.getLogger(__name__)


def create_app(server_config: dict | None = None) -> FastAPI:
    cfg = server_config or load_server_config()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
        logger.info("assgen-server starting up", extra={"config": cfg})

        from assgen.config import get_db_path

        conn: sqlite3.Connection = init_db()
        application.state.conn = conn
        application.state.server_cfg = cfg

        stale = reset_stale_running_jobs(conn)
        if stale:
            logger.warning("Reset %d stale RUNNING job(s) to FAILED on startup", stale)

        mm = ModelManager(conn, device=cfg.get("device", "auto"), server_cfg=cfg)
        application.state.model_manager = mm

        db_path = str(get_db_path())

        def _make_worker_conn() -> sqlite3.Connection:
            import sqlite3 as _s
            worker_conn = _s.connect(db_path)
            worker_conn.row_factory = _s.Row
            worker_conn.execute("PRAGMA journal_mode=WAL")
            worker_conn.execute("PRAGMA foreign_keys=ON")
            return worker_conn

        worker = WorkerThread(
            conn_factory=_make_worker_conn,
            model_manager=mm,
        )
        worker.start()
        application.state.worker = worker
        logger.info("Worker thread started")

        yield

        logger.info("assgen-server shutting down")
        if w := getattr(application.state, "worker", None):
            w.stop()
        if c := getattr(application.state, "conn", None):
            c.close()

    app = FastAPI(
        title="assgen-server",
        description="AI game asset generation server — part of the assgen pipeline",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(jobs_router)
    app.include_router(models_router)

    return app
