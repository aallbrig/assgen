"""Health check route."""
from __future__ import annotations

from fastapi import APIRouter
from assgen.version import get_version_info

router = APIRouter()


@router.get("/health")
def health() -> dict:
    info = get_version_info()
    return {"status": "ok", "version": info["version"], "commit": info.get("commit")}
