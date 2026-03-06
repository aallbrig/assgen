"""Tests for assgen.db — schema, CRUD helpers, and crash-recovery utilities."""
from __future__ import annotations

import pytest
from pathlib import Path


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

def test_init_creates_all_tables(tmp_path: Path) -> None:
    from assgen.db import init_db

    conn = init_db(tmp_path / "test.db")
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert {"jobs", "models", "model_usage", "schema_version"} <= tables


def test_schema_version_is_two(tmp_path: Path) -> None:
    from assgen.db import init_db

    conn = init_db(tmp_path / "test.db")
    version = conn.execute("SELECT version FROM schema_version").fetchone()["version"]
    assert version == 2


def test_idempotent_init(tmp_path: Path) -> None:
    """Calling init_db twice on the same file should not raise."""
    from assgen.db import init_db

    db = tmp_path / "test.db"
    init_db(db)
    init_db(db)  # should not raise


# ---------------------------------------------------------------------------
# Job CRUD
# ---------------------------------------------------------------------------

def test_create_job_returns_uuid(tmp_path: Path) -> None:
    from assgen.db import init_db, create_job

    conn = init_db(tmp_path / "test.db")
    jid = create_job(conn, job_type="visual.model.create", params={"prompt": "sword"})
    assert len(jid) == 36  # UUID format
    assert "-" in jid


def test_get_job_by_full_id(tmp_path: Path) -> None:
    from assgen.db import init_db, create_job, get_job, JobStatus

    conn = init_db(tmp_path / "test.db")
    jid = create_job(conn, job_type="audio.sfx.generate", params={"prompt": "laser"})
    job = get_job(conn, jid)
    assert job is not None
    assert job["id"] == jid
    assert job["job_type"] == "audio.sfx.generate"
    assert job["status"] == JobStatus.QUEUED


def test_get_job_by_prefix(tmp_path: Path) -> None:
    """8-char prefix lookup should resolve to the correct job."""
    from assgen.db import init_db, create_job, get_job

    conn = init_db(tmp_path / "test.db")
    jid = create_job(conn, job_type="visual.model.create", params={})
    prefix = jid[:8]

    job = get_job(conn, prefix)
    assert job is not None
    assert job["id"] == jid


def test_get_job_prefix_no_match(tmp_path: Path) -> None:
    from assgen.db import init_db, get_job

    conn = init_db(tmp_path / "test.db")
    assert get_job(conn, "00000000") is None


def test_get_job_prefix_ambiguous_returns_none(tmp_path: Path) -> None:
    """When multiple jobs share the prefix, get_job must not guess."""
    from assgen.db import init_db, get_job

    conn = init_db(tmp_path / "test.db")
    # Force two UUIDs that share the same 8-char prefix by patching uuid4
    fixed_prefix = "aabbccdd"
    uid_a = f"{fixed_prefix}-0000-0000-0000-000000000001"
    uid_b = f"{fixed_prefix}-0000-0000-0000-000000000002"

    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    for uid in (uid_a, uid_b):
        conn.execute(
            "INSERT INTO jobs (id, job_type, status, params, priority, created_at, tags) "
            "VALUES (?, 'visual.model.create', 'QUEUED', '{}', 0, ?, '[]')",
            (uid, now),
        )
    conn.commit()

    # Ambiguous — should return None (not raise)
    result = get_job(conn, fixed_prefix)
    assert result is None


def test_list_jobs_empty(tmp_path: Path) -> None:
    from assgen.db import init_db, list_jobs

    conn = init_db(tmp_path / "test.db")
    assert list_jobs(conn) == []


def test_list_jobs_status_filter(tmp_path: Path) -> None:
    from assgen.db import init_db, create_job, list_jobs, update_job_status, JobStatus

    conn = init_db(tmp_path / "test.db")
    jid1 = create_job(conn, "visual.model.create", {})
    jid2 = create_job(conn, "audio.sfx.generate", {})
    update_job_status(conn, jid1, JobStatus.RUNNING)

    running = list_jobs(conn, statuses=[JobStatus.RUNNING])
    assert len(running) == 1
    assert running[0]["id"] == jid1

    queued = list_jobs(conn, statuses=[JobStatus.QUEUED])
    assert len(queued) == 1
    assert queued[0]["id"] == jid2


def test_update_job_status_progress(tmp_path: Path) -> None:
    from assgen.db import init_db, create_job, get_job, update_job_status, JobStatus

    conn = init_db(tmp_path / "test.db")
    jid = create_job(conn, "visual.model.create", {})
    update_job_status(conn, jid, JobStatus.RUNNING, progress=0.5, progress_message="halfway")

    job = get_job(conn, jid)
    assert job["status"] == JobStatus.RUNNING
    assert job["progress"] == pytest.approx(0.5)
    assert job["progress_message"] == "halfway"
    assert job["started_at"] is not None


def test_terminal_state_sets_completed_at(tmp_path: Path) -> None:
    from assgen.db import init_db, create_job, get_job, update_job_status, JobStatus

    conn = init_db(tmp_path / "test.db")
    jid = create_job(conn, "visual.model.create", {})
    update_job_status(conn, jid, JobStatus.COMPLETED, progress=1.0, output={"path": "/out.glb"})

    job = get_job(conn, jid)
    assert job["status"] == JobStatus.COMPLETED
    assert job["completed_at"] is not None
    assert job["output"]["path"] == "/out.glb"


# ---------------------------------------------------------------------------
# Crash recovery
# ---------------------------------------------------------------------------

def test_reset_stale_running_jobs(tmp_path: Path) -> None:
    from assgen.db import (
        init_db, create_job, update_job_status,
        reset_stale_running_jobs, get_job, JobStatus,
    )

    conn = init_db(tmp_path / "test.db")
    jid = create_job(conn, "visual.model.create", {})
    update_job_status(conn, jid, JobStatus.RUNNING)

    count = reset_stale_running_jobs(conn)
    assert count == 1

    job = get_job(conn, jid)
    assert job["status"] == JobStatus.FAILED
    assert "restarted" in job["error"].lower()


def test_reset_stale_leaves_terminal_jobs(tmp_path: Path) -> None:
    from assgen.db import (
        init_db, create_job, update_job_status,
        reset_stale_running_jobs, get_job, JobStatus,
    )

    conn = init_db(tmp_path / "test.db")
    jid = create_job(conn, "visual.model.create", {})
    update_job_status(conn, jid, JobStatus.COMPLETED, progress=1.0)

    count = reset_stale_running_jobs(conn)
    assert count == 0

    job = get_job(conn, jid)
    assert job["status"] == JobStatus.COMPLETED


# ---------------------------------------------------------------------------
# Model upsert
# ---------------------------------------------------------------------------

def test_upsert_model_insert_and_update(tmp_path: Path) -> None:
    from assgen.db import init_db, upsert_model

    conn = init_db(tmp_path / "test.db")
    upsert_model(conn, "stabilityai/TripoSR", name="TripoSR", local_path="/models/triposr")
    row = conn.execute(
        "SELECT * FROM models WHERE model_id = ?", ("stabilityai/TripoSR",)
    ).fetchone()
    assert row is not None
    assert row["local_path"] == "/models/triposr"

    # Update
    upsert_model(conn, "stabilityai/TripoSR", local_path="/models/triposr-v2")
    row = conn.execute(
        "SELECT * FROM models WHERE model_id = ?", ("stabilityai/TripoSR",)
    ).fetchone()
    assert row["local_path"] == "/models/triposr-v2"
