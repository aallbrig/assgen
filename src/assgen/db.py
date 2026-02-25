"""SQLite database schema and helpers for assgen.

Tables:
  jobs        — all submitted jobs and their lifecycle state
  model_usage — record of which model was used for each job (analytics)
  models      — locally installed model metadata

Migrations are handled by a simple version table; new columns/tables are
added incrementally so existing databases are upgraded automatically.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

from assgen.config import get_db_path

# ---------------------------------------------------------------------------
# Schema version — bump when adding migrations
# ---------------------------------------------------------------------------
SCHEMA_VERSION = 2


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Open a connection with WAL mode and foreign-key enforcement."""
    path = db_path or get_db_path()
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Generator[sqlite3.Connection, None, None]:
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


# ---------------------------------------------------------------------------
# Schema migrations
# ---------------------------------------------------------------------------

_SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id                TEXT PRIMARY KEY,
    job_type          TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'QUEUED',
    params            TEXT NOT NULL DEFAULT '{}',
    output            TEXT,
    error             TEXT,
    progress          REAL NOT NULL DEFAULT 0.0,
    progress_message  TEXT,
    priority          INTEGER NOT NULL DEFAULT 0,
    created_at        TEXT NOT NULL,
    started_at        TEXT,
    completed_at      TEXT,
    worker_id         TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_status   ON jobs (status);
CREATE INDEX IF NOT EXISTS idx_jobs_created  ON jobs (created_at);
CREATE INDEX IF NOT EXISTS idx_jobs_job_type ON jobs (job_type);

CREATE TABLE IF NOT EXISTS models (
    model_id          TEXT PRIMARY KEY,
    name              TEXT NOT NULL,
    job_types         TEXT NOT NULL DEFAULT '[]',
    local_path        TEXT,
    installed_at      TEXT,
    last_used_at      TEXT,
    size_bytes        INTEGER,
    hf_revision       TEXT
);

CREATE TABLE IF NOT EXISTS model_usage (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id    TEXT NOT NULL,
    job_id      TEXT NOT NULL,
    used_at     TEXT NOT NULL,
    FOREIGN KEY (job_id) REFERENCES jobs (id)
);

CREATE INDEX IF NOT EXISTS idx_model_usage_model ON model_usage (model_id);
CREATE INDEX IF NOT EXISTS idx_model_usage_job   ON model_usage (job_id);
"""

_SCHEMA_V2_ADDITIONS = """
-- v2: add tags column for user-defined labels on jobs
ALTER TABLE jobs ADD COLUMN tags TEXT NOT NULL DEFAULT '[]';
"""


def init_db(db_path: Path | None = None) -> sqlite3.Connection:
    """Ensure the database is initialised and migrated; return an open connection."""
    conn = get_connection(db_path)
    with transaction(conn):
        conn.executescript(_SCHEMA_V1)
        row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
        current = row["version"] if row else 0
        if current == 0:
            conn.execute("INSERT INTO schema_version VALUES (?)", (1,))
            current = 1
        if current < 2:
            try:
                conn.executescript(_SCHEMA_V2_ADDITIONS)
            except sqlite3.OperationalError:
                pass  # column may already exist
            conn.execute("UPDATE schema_version SET version = 2")
    return conn


# ---------------------------------------------------------------------------
# Job helpers
# ---------------------------------------------------------------------------

class JobStatus:
    QUEUED    = "QUEUED"
    RUNNING   = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED    = "FAILED"
    CANCELLED = "CANCELLED"

    TERMINAL = {COMPLETED, FAILED, CANCELLED}


def create_job(
    conn: sqlite3.Connection,
    job_type: str,
    params: dict[str, Any],
    priority: int = 0,
    tags: list[str] | None = None,
) -> str:
    """Insert a new QUEUED job and return its ID."""
    job_id = str(uuid.uuid4())
    with transaction(conn):
        conn.execute(
            """
            INSERT INTO jobs (id, job_type, status, params, priority, created_at, tags)
            VALUES (?, ?, 'QUEUED', ?, ?, ?, ?)
            """,
            (job_id, job_type, json.dumps(params), priority, _now_iso(), json.dumps(tags or [])),
        )
    return job_id


def get_job(conn: sqlite3.Connection, job_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return _row_to_job(row) if row else None


def list_jobs(
    conn: sqlite3.Connection,
    statuses: list[str] | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    if statuses:
        placeholders = ",".join("?" * len(statuses))
        rows = conn.execute(
            f"SELECT * FROM jobs WHERE status IN ({placeholders}) ORDER BY created_at DESC LIMIT ?",
            (*statuses, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_row_to_job(r) for r in rows]


def update_job_status(
    conn: sqlite3.Connection,
    job_id: str,
    status: str,
    progress: float | None = None,
    progress_message: str | None = None,
    output: dict[str, Any] | None = None,
    error: str | None = None,
    worker_id: str | None = None,
) -> None:
    now = _now_iso()
    fields: list[str] = ["status = ?"]
    values: list[Any] = [status]

    if progress is not None:
        fields.append("progress = ?")
        values.append(progress)
    if progress_message is not None:
        fields.append("progress_message = ?")
        values.append(progress_message)
    if output is not None:
        fields.append("output = ?")
        values.append(json.dumps(output))
    if error is not None:
        fields.append("error = ?")
        values.append(error)
    if worker_id is not None:
        fields.append("worker_id = ?")
        values.append(worker_id)
    if status == JobStatus.RUNNING:
        fields.append("started_at = ?")
        values.append(now)
    if status in JobStatus.TERMINAL:
        fields.append("completed_at = ?")
        values.append(now)

    values.append(job_id)
    with transaction(conn):
        conn.execute(f"UPDATE jobs SET {', '.join(fields)} WHERE id = ?", values)


def record_model_usage(conn: sqlite3.Connection, model_id: str, job_id: str) -> None:
    with transaction(conn):
        conn.execute(
            "INSERT INTO model_usage (model_id, job_id, used_at) VALUES (?, ?, ?)",
            (model_id, job_id, _now_iso()),
        )
        conn.execute(
            "UPDATE models SET last_used_at = ? WHERE model_id = ?",
            (_now_iso(), model_id),
        )


def upsert_model(conn: sqlite3.Connection, model_id: str, **kwargs: Any) -> None:
    """Insert or update a model row."""
    existing = conn.execute(
        "SELECT model_id FROM models WHERE model_id = ?", (model_id,)
    ).fetchone()
    if existing:
        fields = ", ".join(f"{k} = ?" for k in kwargs)
        with transaction(conn):
            conn.execute(
                f"UPDATE models SET {fields} WHERE model_id = ?",
                (*kwargs.values(), model_id),
            )
    else:
        kwargs["model_id"] = model_id
        cols = ", ".join(kwargs.keys())
        placeholders = ", ".join("?" * len(kwargs))
        with transaction(conn):
            conn.execute(f"INSERT INTO models ({cols}) VALUES ({placeholders})", list(kwargs.values()))


def _row_to_job(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    for field in ("params", "output", "tags"):
        if d.get(field):
            try:
                d[field] = json.loads(d[field])
            except (json.JSONDecodeError, TypeError):
                pass
    return d
