"""Health check route."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from assgen.version import get_version_info

router = APIRouter(tags=["health"])

# Bump this integer only on breaking API changes (removed/renamed fields,
# changed semantics).  Additive changes (new optional fields) are non-breaking.
API_VERSION: int = 1


class HealthResponse(BaseModel):
    status: str
    version: str
    commit: str | None = None
    api_version: int = Field(
        default=API_VERSION,
        description="API contract version.  Incremented only on breaking changes.",
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Server health check",
    description="Returns `ok` when the server is running. Includes version and git commit.",
)
def health() -> dict:
    info = get_version_info()
    return {
        "status": "ok",
        "version": info["version"],
        "commit": info.get("commit"),
        "api_version": API_VERSION,
    }
