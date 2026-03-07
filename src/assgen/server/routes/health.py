"""Health check route."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from assgen.version import get_version_info

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    commit: str | None = None


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Server health check",
    description="Returns `ok` when the server is running. Includes version and git commit.",
)
def health() -> dict:
    info = get_version_info()
    return {"status": "ok", "version": info["version"], "commit": info.get("commit")}
