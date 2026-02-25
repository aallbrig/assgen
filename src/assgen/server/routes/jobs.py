"""Jobs REST routes.

POST   /jobs            — enqueue a new job
GET    /jobs            — list jobs (with optional status filter)
GET    /jobs/{id}       — get single job
DELETE /jobs/{id}       — cancel a queued or running job
"""
from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from assgen.catalog import get_model_for_job
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


# ---------------------------------------------------------------------------
# Dependency: DB connection from app state
# ---------------------------------------------------------------------------

def _get_conn(request: Any = None):  # noqa: ANN001
    """Injected by app.py via request.app.state.conn."""
    from fastapi import Request
    # This will be overridden in app.py — stub here for typing
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("", response_model=JobResponse, status_code=201)
async def enqueue_job(body: JobRequest, request: Request) -> dict:
    conn = request.app.state.conn

    # Validate job_type against catalog
    if not get_model_for_job(body.job_type):
        raise HTTPException(
            status_code=422,
            detail=f"Unknown job_type {body.job_type!r}. Run `assgen models list` to see valid types.",
        )

    job_id = create_job(
        conn,
        job_type=body.job_type,
        params=body.params,
        priority=body.priority,
        tags=body.tags,
    )
    logger.info("Job enqueued", extra={"job_id": job_id, "job_type": body.job_type})
    job = get_job(conn, job_id)
    return _normalise(job)


@router.get("", response_model=list[JobResponse])
async def list_jobs_route(
    request: Request,
    status: Annotated[list[str] | None, Query()] = None,
    limit: int = Query(default=50, ge=1, le=500),
) -> list[dict]:
    conn = request.app.state.conn
    jobs = list_jobs(conn, statuses=status, limit=limit)
    return [_normalise(j) for j in jobs]


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_route(job_id: str, request: Request) -> dict:
    conn = request.app.state.conn
    job = get_job(conn, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id!r} not found")
    return _normalise(job)


@router.delete("/{job_id}", status_code=204)
async def cancel_job(job_id: str, request: Request) -> None:
    conn = request.app.state.conn
    job = get_job(conn, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id!r} not found")
    if job["status"] in JobStatus.TERMINAL:
        raise HTTPException(status_code=409, detail=f"Job already in terminal state: {job['status']}")
    update_job_status(conn, job_id, JobStatus.CANCELLED)
    logger.info("Job cancelled", extra={"job_id": job_id})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise(job: dict | None) -> dict:
    if not job:
        return {}
    job.setdefault("tags", [])
    return job
