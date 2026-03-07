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
from assgen.version import get_version_info

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OpenAPI tag descriptions — shown in the /docs UI sidebar
# ---------------------------------------------------------------------------

_OPENAPI_TAGS = [
    {
        "name": "health",
        "description": "Server liveness and version check.",
    },
    {
        "name": "jobs",
        "description": (
            "Enqueue, inspect, and cancel asset-generation jobs.  "
            "Each job runs a HuggingFace model on the server GPU and "
            "writes output files that can be downloaded once the job "
            "reaches `COMPLETED` status."
        ),
    },
    {
        "name": "models",
        "description": (
            "Inspect the model catalog and trigger pre-download of "
            "HuggingFace model weights to the server cache directory."
        ),
    },
]

_DESCRIPTION = """\
## assgen-server

REST API for the **assgen** AI game-asset generation pipeline.

Clients enqueue *jobs* specifying a [game-dev task](../tasks) and optional parameters.
The server downloads the required HuggingFace model (if not already cached),
runs inference on the GPU, and stores the output files in the server's outputs
directory.  Clients can poll for completion and then download the files.

### Quick start

```bash
# Start the server (or let the client auto-start it)
assgen-server start

# Submit a job and wait for it
assgen gen visual model create --prompt "low-poly sword" --wait
```

### Docs & source

* Interactive docs: [`/docs`](/docs) (Swagger UI) or [`/redoc`](/redoc) (ReDoc)
* OpenAPI schema: [`/openapi.json`](/openapi.json)
* Source: <https://github.com/aallbrig/assgen>
"""


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

    version = get_version_info()["version"] or "0.0.0.dev"

    app = FastAPI(
        title="assgen-server",
        summary="AI game asset generation pipeline server",
        description=_DESCRIPTION,
        version=version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        openapi_tags=_OPENAPI_TAGS,
        contact={
            "name": "assgen project",
            "url": "https://github.com/aallbrig/assgen",
        },
        license_info={
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT",
        },
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
