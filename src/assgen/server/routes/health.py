"""Health check route."""
from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from assgen.version import get_version_info

router = APIRouter(tags=["health"])

# Bump this integer only on breaking API changes (removed/renamed fields,
# changed semantics).  Additive changes (new optional fields) are non-breaking.
API_VERSION: int = 1


class InferenceCapabilities(BaseModel):
    torch: bool = False
    diffusers: bool = False
    transformers: bool = False
    audiocraft: bool = False
    trimesh: bool = False
    device: str = "cpu"


class HealthResponse(BaseModel):
    status: str
    version: str
    commit: str | None = None
    api_version: int = Field(
        default=API_VERSION,
        description="API contract version.  Incremented only on breaking changes.",
    )
    inference: InferenceCapabilities | None = None


def _check_inference(device: str) -> dict:
    """Probe which ML libraries are importable."""
    caps: dict = {"device": device}
    for lib in ("torch", "diffusers", "transformers", "audiocraft", "trimesh"):
        try:
            __import__(lib)
            caps[lib] = True
        except ImportError:
            caps[lib] = False
    return caps


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Server health check",
    description="Returns `ok` when the server is running. Includes version, git commit, and inference capabilities.",
)
def health(request: Request) -> dict:
    info = get_version_info()
    device = "cpu"
    if mm := getattr(request.app.state, "model_manager", None):
        device = getattr(mm, "device", "cpu")
    return {
        "status": "ok",
        "version": info["version"],
        "commit": info.get("commit"),
        "api_version": API_VERSION,
        "inference": _check_inference(device),
    }
