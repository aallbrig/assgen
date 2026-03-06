"""Integration tests for the FastAPI server routes.

Uses FastAPI's ``TestClient`` (backed by ``httpx``) which runs the full ASGI
app including startup/shutdown lifecycle hooks — the SQLite DB is wired up, the
worker thread starts, and requests flow through the real route handlers.

A temporary database (isolated per test module via a module-scoped fixture)
prevents interference with any real user data.
"""
from __future__ import annotations

from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from assgen.server.app import create_app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def tmp_db_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Return a path inside a temp directory for the test DB."""
    return tmp_path_factory.mktemp("assgen_test") / "test.db"


@pytest.fixture(scope="module")
def client(tmp_db_path: Path) -> Generator[TestClient, None, None]:
    """TestClient wired to a throw-away SQLite DB with no allow-list."""
    server_cfg = {
        "host": "127.0.0.1",
        "port": 8742,
        "device": "cpu",
        "allow_list": [],
        "skip_model_validation": True,  # skip HF Hub calls in tests
    }

    # Patch the DB path so the server uses our temp file
    with patch("assgen.db.get_db_path", return_value=tmp_db_path):
        with patch("assgen.config.get_db_path", return_value=tmp_db_path):
            app = create_app(server_config=server_cfg)
            with TestClient(app, raise_server_exceptions=True) as tc:
                yield tc


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_returns_ok(self, client: TestClient) -> None:
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert "version" in body

    def test_health_has_version_string(self, client: TestClient) -> None:
        r = client.get("/health")
        version = r.json()["version"]
        assert isinstance(version, str)
        assert len(version) > 0


# ---------------------------------------------------------------------------
# POST /jobs — enqueue
# ---------------------------------------------------------------------------

class TestEnqueueJob:
    def test_enqueue_known_job_type_returns_201(self, client: TestClient) -> None:
        r = client.post("/jobs", json={"job_type": "visual.model.create"})
        assert r.status_code == 201

    def test_enqueue_returns_job_id(self, client: TestClient) -> None:
        r = client.post("/jobs", json={"job_type": "visual.model.create"})
        body = r.json()
        assert "id" in body
        assert len(body["id"]) == 36  # UUID

    def test_enqueue_returns_queued_status(self, client: TestClient) -> None:
        r = client.post("/jobs", json={"job_type": "visual.model.create"})
        assert r.json()["status"] == "QUEUED"

    def test_enqueue_stores_params(self, client: TestClient) -> None:
        r = client.post("/jobs", json={
            "job_type": "visual.model.create",
            "params": {"prompt": "medieval sword"},
        })
        assert r.json()["params"]["prompt"] == "medieval sword"

    def test_enqueue_stores_tags(self, client: TestClient) -> None:
        r = client.post("/jobs", json={
            "job_type": "audio.sfx.generate",
            "tags": ["test", "sfx"],
        })
        assert set(r.json()["tags"]) == {"test", "sfx"}

    def test_enqueue_custom_priority(self, client: TestClient) -> None:
        r = client.post("/jobs", json={
            "job_type": "audio.music.compose",
            "priority": 10,
        })
        assert r.json()["priority"] == 10

    def test_enqueue_unknown_job_type_returns_422(self, client: TestClient) -> None:
        r = client.post("/jobs", json={"job_type": "not.a.real.task"})
        assert r.status_code == 422

    def test_enqueue_with_model_id_override(self, client: TestClient) -> None:
        r = client.post("/jobs", json={
            "job_type": "visual.model.create",
            "model_id": "stabilityai/TripoSR",
        })
        assert r.status_code == 201
        # Override is stashed in params
        assert r.json()["params"].get("_model_id_override") == "stabilityai/TripoSR"


# ---------------------------------------------------------------------------
# GET /jobs — list
# ---------------------------------------------------------------------------

class TestListJobs:
    def test_list_returns_200(self, client: TestClient) -> None:
        r = client.get("/jobs")
        assert r.status_code == 200

    def test_list_returns_array(self, client: TestClient) -> None:
        r = client.get("/jobs")
        assert isinstance(r.json(), list)

    def test_list_contains_previously_created_job(self, client: TestClient) -> None:
        r_create = client.post("/jobs", json={"job_type": "visual.texture.generate"})
        job_id = r_create.json()["id"]
        job_ids = [j["id"] for j in client.get("/jobs").json()]
        assert job_id in job_ids

    def test_list_filter_by_status(self, client: TestClient) -> None:
        r = client.get("/jobs", params={"status": "QUEUED"})
        assert r.status_code == 200
        for job in r.json():
            assert job["status"] == "QUEUED"

    def test_list_limit_respected(self, client: TestClient) -> None:
        # Create 3 extra jobs
        for _ in range(3):
            client.post("/jobs", json={"job_type": "visual.model.create"})
        r = client.get("/jobs", params={"limit": 2})
        assert r.status_code == 200
        assert len(r.json()) <= 2


# ---------------------------------------------------------------------------
# GET /jobs/{id}
# ---------------------------------------------------------------------------

class TestGetJob:
    def test_get_by_full_id(self, client: TestClient) -> None:
        r_create = client.post("/jobs", json={"job_type": "visual.rig.auto"})
        job_id = r_create.json()["id"]
        r = client.get(f"/jobs/{job_id}")
        assert r.status_code == 200
        assert r.json()["id"] == job_id

    def test_get_by_prefix(self, client: TestClient) -> None:
        r_create = client.post("/jobs", json={"job_type": "visual.rig.auto"})
        job_id = r_create.json()["id"]
        prefix = job_id[:8]
        r = client.get(f"/jobs/{prefix}")
        assert r.status_code == 200
        assert r.json()["id"] == job_id

    def test_get_unknown_id_returns_404(self, client: TestClient) -> None:
        r = client.get("/jobs/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /jobs/{id} — cancel
# ---------------------------------------------------------------------------

class TestCancelJob:
    def test_cancel_queued_job_returns_204(self, client: TestClient) -> None:
        r_create = client.post("/jobs", json={"job_type": "audio.sfx.generate"})
        job_id = r_create.json()["id"]
        r = client.delete(f"/jobs/{job_id}")
        assert r.status_code == 204

    def test_cancelled_job_status_is_cancelled(self, client: TestClient) -> None:
        r_create = client.post("/jobs", json={"job_type": "audio.sfx.generate"})
        job_id = r_create.json()["id"]
        client.delete(f"/jobs/{job_id}")
        r = client.get(f"/jobs/{job_id}")
        assert r.json()["status"] == "CANCELLED"

    def test_cancel_same_job_twice_returns_409(self, client: TestClient) -> None:
        r_create = client.post("/jobs", json={"job_type": "audio.sfx.generate"})
        job_id = r_create.json()["id"]
        client.delete(f"/jobs/{job_id}")
        r2 = client.delete(f"/jobs/{job_id}")
        assert r2.status_code == 409

    def test_cancel_unknown_job_returns_404(self, client: TestClient) -> None:
        r = client.delete("/jobs/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Allow-list enforcement
# ---------------------------------------------------------------------------

class TestAllowList:
    def test_allow_list_blocks_unlisted_model(self, tmp_db_path: Path) -> None:
        cfg = {
            "device": "cpu",
            "allow_list": ["stabilityai/TripoSR"],
            "skip_model_validation": True,
        }
        with patch("assgen.db.get_db_path", return_value=tmp_db_path):
            with patch("assgen.config.get_db_path", return_value=tmp_db_path):
                app = create_app(server_config=cfg)
                with TestClient(app) as tc:
                    r = tc.post("/jobs", json={
                        "job_type": "audio.sfx.generate",
                        "model_id": "facebook/audiogen-medium",
                    })
                    assert r.status_code == 422
                    assert "allow_list" in r.json()["detail"]

    def test_allow_list_permits_listed_model(self, tmp_db_path: Path) -> None:
        cfg = {
            "device": "cpu",
            "allow_list": ["stabilityai/TripoSR"],
            "skip_model_validation": True,
        }
        with patch("assgen.db.get_db_path", return_value=tmp_db_path):
            with patch("assgen.config.get_db_path", return_value=tmp_db_path):
                app = create_app(server_config=cfg)
                with TestClient(app) as tc:
                    r = tc.post("/jobs", json={
                        "job_type": "visual.model.create",
                        "model_id": "stabilityai/TripoSR",
                    })
                    assert r.status_code == 201
