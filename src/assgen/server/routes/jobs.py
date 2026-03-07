"""Jobs REST routes.

POST   /jobs                         — enqueue a new job
GET    /jobs                         — list jobs (with optional status filter)
GET    /jobs/{id}                    — get single job
DELETE /jobs/{id}                    — cancel a queued or running job
GET    /jobs/{id}/files              — list output files for a completed job
GET    /jobs/{id}/files/{filename}   — download a specific output file
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from assgen.catalog import get_model_for_job
from assgen.config import get_outputs_dir
from assgen.db import (
    JobStatus,
    create_job,
    get_job,
    list_jobs,
    update_job_status,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class JobRequest(BaseModel):
    job_type: str = Field(..., description="e.g. 'visual.model.create'")
    params: dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=0, ge=0, le=100)
    tags: list[str] = Field(default_factory=list)
    # Optional client-side model override.  When provided the server validates
    # this model against the task before accepting the job.
    model_id: str | None = Field(
        default=None,
        description=(
            "Override the catalog model for this job. "
            "The server will validate the model's HF pipeline_tag against the task "
            "unless skip_model_validation is set in server config."
        ),
    )


class JobResponse(BaseModel):
    id: str
    job_type: str
    status: str
    params: dict[str, Any]
    output: Any
    error: str | None
    progress: float
    progress_message: str | None
    priority: int
    created_at: str
    started_at: str | None
    completed_at: str | None
    tags: list[str]
    model_id: str | None = None


# ---------------------------------------------------------------------------
# Dependency: DB connection from app state
# ---------------------------------------------------------------------------

def _get_conn(request: Any = None):  # noqa: ANN001
    """Injected by app.py via request.app.state.conn."""
    # This will be overridden in app.py — stub here for typing
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=JobResponse,
    status_code=201,
    summary="Enqueue a new asset-generation job",
    responses={
        201: {"description": "Job created and queued for processing"},
        422: {"description": "Unknown job_type, model not in allow-list, or task/model mismatch"},
    },
)
async def enqueue_job(body: JobRequest, request: Request) -> dict:
    conn = request.app.state.conn
    server_cfg: dict[str, Any] = getattr(request.app.state, "server_cfg", {})

    # Validate job_type against catalog
    entry = get_model_for_job(body.job_type)
    if not entry:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown job_type {body.job_type!r}. Run `assgen tasks` to see valid types.",
        )

    # Resolve which model will be used (client override > catalog)
    effective_model_id = body.model_id or entry.get("model_id")
    catalog_task = entry.get("task")

    if effective_model_id:
        # Validate model against allow-list and task compatibility
        from assgen.server.validation import validate_job_model
        try:
            validate_job_model(effective_model_id, catalog_task, server_cfg)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Stash the resolved model_id in params so the worker can retrieve it
    params = dict(body.params)
    if body.model_id:
        params["_model_id_override"] = body.model_id

    job_id = create_job(
        conn,
        job_type=body.job_type,
        params=params,
        priority=body.priority,
        tags=body.tags,
    )
    logger.info(
        "Job enqueued",
        extra={"job_id": job_id, "job_type": body.job_type, "model_id": effective_model_id},
    )
    job = get_job(conn, job_id)
    return _normalise(job)


@router.get(
    "",
    response_model=list[JobResponse],
    summary="List jobs",
    description="Return jobs ordered by creation time descending. Filter by `status` (repeatable).",
)
async def list_jobs_route(
    request: Request,
    status: Annotated[list[str] | None, Query()] = None,
    limit: int = Query(default=50, ge=1, le=500),
) -> list[dict]:
    conn = request.app.state.conn
    jobs = list_jobs(conn, statuses=status, limit=limit)
    return [_normalise(j) for j in jobs]


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get a single job",
    description="Look up a job by its full UUID or an 8-character prefix.",
    responses={404: {"description": "Job not found"}},
)
async def get_job_route(job_id: str, request: Request) -> dict:
    conn = request.app.state.conn
    job = get_job(conn, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id!r} not found")
    return _normalise(job)


@router.delete(
    "/{job_id}",
    status_code=204,
    summary="Cancel a job",
    responses={
        204: {"description": "Job cancelled"},
        404: {"description": "Job not found"},
        409: {"description": "Job already in a terminal state"},
    },
)
async def cancel_job(job_id: str, request: Request) -> None:
    conn = request.app.state.conn
    job = get_job(conn, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id!r} not found")
    if job["status"] in JobStatus.TERMINAL:
        raise HTTPException(status_code=409, detail=f"Job already in terminal state: {job['status']}")
    update_job_status(conn, job_id, JobStatus.CANCELLED)
    logger.info("Job cancelled", extra={"job_id": job_id})


@router.get(
    "/{job_id}/files",
    response_model=list[str],
    summary="List output files",
    description="Returns the filenames produced by a COMPLETED job. Use the download endpoint to retrieve each file.",
    responses={
        200: {"description": "List of output filenames"},
        404: {"description": "Job not found"},
        409: {"description": "Job is not yet COMPLETED"},
    },
)
async def list_job_files(job_id: str, request: Request) -> list[str]:
    """List the names of output files produced by a completed job."""
    conn = request.app.state.conn
    job = get_job(conn, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id!r} not found")
    if job["status"] != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=409,
            detail=f"Job is not completed (status={job['status']}). Output files are only available for COMPLETED jobs.",
        )
    output = job.get("output") or {}
    if isinstance(output, str):
        try:
            output = json.loads(output)
        except Exception:
            output = {}
    files: list[str] = output.get("files", [])
    # Also check the filesystem in case the output record is stale
    job_out_dir: Path = get_outputs_dir() / job_id
    if job_out_dir.exists():
        on_disk = {f.name for f in job_out_dir.iterdir() if f.is_file()}
        # Merge: keep ordering from DB record, append any extras on disk
        recorded = set(files)
        files = files + [f for f in sorted(on_disk) if f not in recorded]
    return files


@router.get(
    "/{job_id}/files/{filename}",
    summary="Download an output file",
    responses={
        200: {"description": "File bytes", "content": {"application/octet-stream": {}}},
        400: {"description": "Invalid filename (path traversal attempt)"},
        404: {"description": "Job or file not found"},
        409: {"description": "Job is not COMPLETED"},
    },
)
async def download_job_file(job_id: str, filename: str, request: Request) -> FileResponse:
    """Download a specific output file from a completed job.

    The *filename* must be a plain filename (no path separators) to prevent
    directory traversal attacks.
    """
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    conn = request.app.state.conn
    job = get_job(conn, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id!r} not found")
    if job["status"] != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=409,
            detail=f"Job is not completed (status={job['status']})",
        )
    file_path: Path = get_outputs_dir() / job_id / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"File {filename!r} not found for job {job_id[:8]}")
    return FileResponse(path=str(file_path), filename=filename)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise(job: dict | None) -> dict:
    if not job:
        return {}
    job.setdefault("tags", [])
    job.setdefault("model_id", job.get("params", {}).get("_model_id_override"))
    return job
