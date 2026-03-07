"""Tests for assgen.catalog — built-in catalog loading and model resolution."""
from __future__ import annotations


def test_load_catalog_returns_nonempty_dict() -> None:
    from assgen.catalog import load_catalog

    catalog = load_catalog()
    assert isinstance(catalog, dict)
    assert len(catalog) > 0


def test_known_job_types_present() -> None:
    from assgen.catalog import load_catalog

    catalog = load_catalog()
    required = [
        "visual.model.create",
        "audio.sfx.generate",
        "audio.music.compose",
        "visual.rig.auto",
        "scene.lighting.hdri",
        "pipeline.integrate.export",
    ]
    for jt in required:
        assert jt in catalog, f"Missing job type in catalog: {jt}"


def test_each_entry_has_required_fields() -> None:
    from assgen.catalog import load_catalog

    catalog = load_catalog()
    for job_type, entry in catalog.items():
        assert isinstance(entry, dict), f"{job_type}: entry must be a dict"
        assert "name" in entry, f"{job_type}: missing 'name' field"
        # model_id may be None (for data-processing tasks), but key must exist
        assert "model_id" in entry, f"{job_type}: missing 'model_id' field"


def test_get_model_for_known_job() -> None:
    from assgen.catalog import get_model_for_job

    entry = get_model_for_job("visual.model.create")
    assert entry is not None
    assert entry["model_id"] == "tencent/Hunyuan3D-2"
    assert entry["name"] == "Hunyuan3D-2"


def test_get_model_for_unknown_job_returns_none() -> None:
    from assgen.catalog import get_model_for_job

    assert get_model_for_job("nonexistent.job.type") is None


def test_catalog_task_field_values() -> None:
    """task field should be a non-empty string or absent."""
    from assgen.catalog import load_catalog

    catalog = load_catalog()
    for job_type, entry in catalog.items():
        task = entry.get("task")
        if task is not None:
            assert isinstance(task, str) and task, (
                f"{job_type}: 'task' must be a non-empty string if present"
            )


def test_model_ids_are_org_slash_repo() -> None:
    """All non-null model_ids must be in 'org/repo' format."""
    from assgen.catalog import load_catalog

    catalog = load_catalog()
    for job_type, entry in catalog.items():
        mid = entry.get("model_id")
        if mid:
            assert "/" in mid, (
                f"{job_type}: model_id '{mid}' is not in 'org/repo' format"
            )
