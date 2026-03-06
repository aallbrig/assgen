"""Catalog loader — merges the built-in catalog.yaml with any user overrides.

The catalog maps every game-dev *job type* (e.g. ``visual.model.create``) to a
HuggingFace model ID and associated metadata.  The built-in defaults live in
``catalog.yaml`` alongside this module; users can override any entry by adding
the same key to ``~/.config/assgen/models.yaml`` under the ``catalog:`` key.

Example:
    >>> from assgen.catalog import load_catalog, get_model_for_job
    >>> catalog = load_catalog()
    >>> entry = get_model_for_job("visual.model.create")
    >>> entry["model_id"]
    'stabilityai/TripoSR'
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from assgen.config import get_config_dir

_BUILTIN_CATALOG = Path(__file__).parent / "catalog.yaml"


@lru_cache(maxsize=1)
def load_catalog() -> dict[str, dict[str, Any]]:
    """Load and return the merged job-type → model catalog.

    Reads the built-in ``catalog.yaml`` first, then overlays any entries
    found in ``~/.config/assgen/models.yaml``.  The result is cached; call
    ``load_catalog.cache_clear()`` after modifying the user catalog.

    Returns:
        A dict mapping job-type strings to catalog entry dicts.  Each entry
        contains at least ``model_id`` (str | None) and ``name`` (str).

    Example:
        >>> catalog = load_catalog()
        >>> "visual.model.create" in catalog
        True
    """
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
    """Return the catalog entry for *job_type*, or ``None`` if unknown.

    Args:
        job_type: Dot-separated task identifier, e.g. ``"visual.model.create"``.

    Returns:
        A dict with keys ``model_id``, ``name``, ``task``, and optional
        ``notes``; or ``None`` if the job type is not in the catalog.

    Example:
        >>> get_model_for_job("audio.sfx.generate")["name"]
        'AudioGen Medium'
    """
    return load_catalog().get(job_type)


def all_job_types() -> list[str]:
    """Return a sorted list of every job type in the catalog.

    Returns:
        Alphabetically sorted list of job-type strings.
    """
    return sorted(load_catalog().keys())


def all_model_ids() -> list[str]:
    """Return a deduplicated list of every HF model ID referenced in the catalog.

    Returns:
        List of ``org/repo`` model ID strings, in catalog order, without
        duplicates (multiple job types often share the same base model).
    """
    seen: set[str] = set()
    result: list[str] = []
    for entry in load_catalog().values():
        mid = entry.get("model_id")
        if mid and mid not in seen:
            seen.add(mid)
            result.append(mid)
    return result
