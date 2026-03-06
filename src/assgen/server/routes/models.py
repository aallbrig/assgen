"""Models REST routes.

GET    /models           — list all models (catalog + install status)
POST   /models/install   — trigger download of all (or specific) models
GET    /models/{id}      — single model status
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/models", tags=["models"])


class ModelStatusResponse(BaseModel):
    model_id: str
    name: str
    installed: bool
    local_path: str | None
    installed_at: str | None
    last_used_at: str | None
    size_bytes: int | None
    job_types: list[str]


class InstallRequest(BaseModel):
    model_ids: list[str] | None = None  # None = install all


@router.get("", response_model=list[ModelStatusResponse])
async def list_models(request: Request) -> list[dict]:
    mm = request.app.state.model_manager
    return mm.list_status()


@router.get("/{model_id:path}", response_model=ModelStatusResponse)
async def get_model(model_id: str, request: Request) -> dict:
    mm = request.app.state.model_manager
    statuses = mm.list_status()
    for s in statuses:
        if s["model_id"] == model_id:
            return s
    raise HTTPException(status_code=404, detail=f"Model {model_id!r} not in catalog")


@router.post("/install", status_code=202)
async def install_models(
    body: InstallRequest,
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict:
    mm = request.app.state.model_manager
    if body.model_ids:
        for mid in body.model_ids:
            background_tasks.add_task(mm.ensure_model, mid)
        return {"queued": body.model_ids}
    else:
        background_tasks.add_task(mm.install_all)
        return {"queued": "all"}
