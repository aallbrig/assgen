"""Catalog loader — merges the built-in catalog.yaml with any user overrides."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from assgen.config import get_config_dir

_BUILTIN_CATALOG = Path(__file__).parent / "catalog.yaml"


@lru_cache(maxsize=1)
def load_catalog() -> dict[str, dict[str, Any]]:
    """Return merged catalog: built-in + user overrides."""
    with _BUILTIN_CATALOG.open() as f:
        data = yaml.safe_load(f) or {}
    catalog: dict[str, Any] = data.get("catalog", {})

    user_path = get_config_dir() / "models.yaml"
    if user_path.exists():
        with user_path.open() as f:
            user_data = yaml.safe_load(f) or {}
        catalog.update(user_data.get("catalog", {}))

    return catalog


def get_model_for_job(job_type: str) -> dict[str, Any] | None:
    return load_catalog().get(job_type)


def all_job_types() -> list[str]:
    return sorted(load_catalog().keys())


def all_model_ids() -> list[str]:
    """Return deduplicated list of all HF model IDs referenced in the catalog."""
    seen: set[str] = set()
    result: list[str] = []
    for entry in load_catalog().values():
        mid = entry.get("model_id")
        if mid and mid not in seen:
            seen.add(mid)
            result.append(mid)
    return result
