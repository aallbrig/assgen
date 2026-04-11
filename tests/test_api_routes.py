"""Integration tests for the FastAPI server routes.

Uses FastAPI's ``TestClient`` (backed by ``httpx``) which runs the full ASGI
app including startup/shutdown lifecycle hooks — the SQLite DB is wired up, the
worker thread starts, and requests flow through the real route handlers.

A temporary database (isolated per test module via a module-scoped fixture)
prevents interference with any real user data.
"""
from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
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

    def test_health_includes_api_version(self, client: TestClient) -> None:
        r = client.get("/health")
        body = r.json()
        assert "api_version" in body
        assert isinstance(body["api_version"], int)
        assert body["api_version"] >= 1

    def test_api_version_header_present(self, client: TestClient) -> None:
        r = client.get("/health")
        assert "X-AssGen-API-Version" in r.headers
        assert r.headers["X-AssGen-API-Version"] == str(r.json()["api_version"])

    def test_api_version_header_on_other_routes(self, client: TestClient) -> None:
        r = client.get("/jobs")
        assert "X-AssGen-API-Version" in r.headers


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


# ---------------------------------------------------------------------------
# GET /jobs/{id}/files  and  GET /jobs/{id}/files/{filename}
# ---------------------------------------------------------------------------

class TestJobFiles:
    """Tests for the file-download endpoints.

    We manually set a job to COMPLETED and plant a file in the outputs dir
    to simulate a finished job without running the real worker/inference.
    """

    def _make_completed_job(
        self,
        client: TestClient,
        tmp_path: Path,
        filenames: list[str],
    ) -> tuple[str, Path]:
        """Create a job, manually set it COMPLETED, and write stub output files."""
        from unittest.mock import patch as _patch

        from assgen.db import update_job_status

        # Enqueue a job
        r = client.post("/jobs", json={"job_type": "visual.model.create"})
        assert r.status_code == 201
        job_id = r.json()["id"]

        # Write fake output files into a tmp outputs dir
        job_out_dir = tmp_path / job_id
        job_out_dir.mkdir(parents=True, exist_ok=True)
        for fname in filenames:
            (job_out_dir / fname).write_text(f"stub content for {fname}")

        # Set the job to COMPLETED via direct DB update (bypass the worker)
        with _patch("assgen.db.get_db_path"):
            conn = client.app.state.conn
            update_job_status(conn, job_id, "COMPLETED", output={"files": filenames})

        return job_id, job_out_dir

    def test_list_files_returns_200_for_completed_job(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        from unittest.mock import patch as _patch

        job_id, job_out_dir = self._make_completed_job(client, tmp_path, ["model.glb"])
        with _patch("assgen.server.routes.jobs.get_outputs_dir", return_value=tmp_path):
            r = client.get(f"/jobs/{job_id}/files")
        assert r.status_code == 200
        assert "model.glb" in r.json()

    def test_list_files_returns_409_for_non_completed_job(self, client: TestClient) -> None:
        r = client.post("/jobs", json={"job_type": "visual.model.create"})
        job_id = r.json()["id"]
        # Cancel it so it's terminal but not COMPLETED
        client.delete(f"/jobs/{job_id}")
        r_files = client.get(f"/jobs/{job_id}/files")
        assert r_files.status_code == 409

    def test_list_files_returns_404_for_unknown_job(self, client: TestClient) -> None:
        r = client.get("/jobs/00000000-0000-0000-0000-000000000000/files")
        assert r.status_code == 404

    def test_download_file_returns_200(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        from unittest.mock import patch as _patch

        job_id, job_out_dir = self._make_completed_job(client, tmp_path, ["mesh.glb"])
        with _patch("assgen.server.routes.jobs.get_outputs_dir", return_value=tmp_path):
            r = client.get(f"/jobs/{job_id}/files/mesh.glb")
        assert r.status_code == 200
        assert b"stub content" in r.content

    def test_download_unknown_file_returns_404(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        from unittest.mock import patch as _patch

        job_id, job_out_dir = self._make_completed_job(client, tmp_path, ["exists.txt"])
        with _patch("assgen.server.routes.jobs.get_outputs_dir", return_value=tmp_path):
            r = client.get(f"/jobs/{job_id}/files/does_not_exist.txt")
        assert r.status_code == 404

    def test_download_path_traversal_returns_400(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        from unittest.mock import patch as _patch

        job_id, job_out_dir = self._make_completed_job(client, tmp_path, ["x.txt"])
        with _patch("assgen.server.routes.jobs.get_outputs_dir", return_value=tmp_path):
            r = client.get(f"/jobs/{job_id}/files/../secret")
        # FastAPI URL-decodes paths; the router should either 404 or 400
        assert r.status_code in (400, 404)


# ---------------------------------------------------------------------------
# SSE — GET /jobs/{id}/events
# ---------------------------------------------------------------------------

class TestJobEvents:
    """Tests for the SSE progress-streaming endpoint.

    All tests use terminal-state jobs so the SSE stream always closes promptly.
    """

    def _make_terminal_job(self, client: TestClient, status: str = "COMPLETED") -> str:
        """Enqueue a job and immediately set it to the requested terminal state."""
        from assgen.db import update_job_status

        r = client.post("/jobs", json={"job_type": "visual.model.create"})
        assert r.status_code == 201
        job_id = r.json()["id"]
        conn = client.app.state.conn
        update_job_status(conn, job_id, status, progress=1.0, output={"files": []})
        return job_id

    def _collect_events(self, client: TestClient, job_id: str) -> tuple[int, list[dict]]:
        """Open the SSE stream, collect all events, and return (status_code, events)."""
        import json as _json

        events: list[dict] = []
        with client.stream("GET", f"/jobs/{job_id}/events") as resp:
            status_code = resp.status_code
            for raw_line in resp.iter_lines():
                if raw_line.startswith("data: "):
                    try:
                        events.append(_json.loads(raw_line[6:]))
                    except _json.JSONDecodeError:
                        pass
                    # Stop reading once we see a terminal event (stream also closes naturally)
                    if events and events[-1].get("status") in {"COMPLETED", "FAILED", "CANCELLED"}:
                        break
        return status_code, events

    def test_events_returns_200_for_completed_job(self, client: TestClient) -> None:
        """SSE stream returns 200 with correct content-type for a completed job."""
        job_id = self._make_terminal_job(client, "COMPLETED")
        with client.stream("GET", f"/jobs/{job_id}/events") as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers.get("content-type", "")

    def test_events_unknown_job_emits_error_event(self, client: TestClient) -> None:
        """Stream for an unknown job emits an error event and closes."""
        import json as _json

        events: list[dict] = []
        with client.stream("GET", "/jobs/00000000-0000-0000-0000-000000000000/events") as resp:
            assert resp.status_code == 200  # SSE always returns 200; error is in the event
            for raw_line in resp.iter_lines():
                if raw_line.startswith("data: "):
                    try:
                        events.append(_json.loads(raw_line[6:]))
                    except _json.JSONDecodeError:
                        pass
                    break  # only need first event

        assert events, "Expected at least one event"
        # The error event contains an 'error' key
        assert "error" in events[0], f"Expected error event, got: {events[0]}"

    def test_events_emits_completed_event(self, client: TestClient) -> None:
        """A COMPLETED job emits a COMPLETED status event."""
        job_id = self._make_terminal_job(client, "COMPLETED")
        _, events = self._collect_events(client, job_id)
        assert events, "No events received"
        assert any(e.get("status") == "COMPLETED" for e in events), f"events: {events}"

    def test_events_emits_failed_event(self, client: TestClient) -> None:
        """A FAILED job emits a FAILED status event."""
        from assgen.db import update_job_status

        r = client.post("/jobs", json={"job_type": "audio.sfx.generate"})
        job_id = r.json()["id"]
        conn = client.app.state.conn
        update_job_status(conn, job_id, "FAILED", error="intentional test failure")

        _, events = self._collect_events(client, job_id)
        assert any(e.get("status") == "FAILED" for e in events), f"events: {events}"

    def test_events_payload_has_required_keys(self, client: TestClient) -> None:
        """Every SSE event payload has progress, message, and status keys."""
        job_id = self._make_terminal_job(client, "COMPLETED")
        _, events = self._collect_events(client, job_id)

        assert events, "Expected at least one event"
        for event in events:
            assert "progress" in event, f"Missing 'progress' in {event}"
            assert "message" in event, f"Missing 'message' in {event}"
            assert "status" in event, f"Missing 'status' in {event}"

    def test_events_progress_values_are_valid_floats(self, client: TestClient) -> None:
        """Progress values must be in the range [0.0, 1.0]."""
        job_id = self._make_terminal_job(client, "COMPLETED")
        _, events = self._collect_events(client, job_id)

        for event in events:
            p = event.get("progress", 0)
            assert 0.0 <= p <= 1.0, f"Invalid progress value {p!r} in event: {event}"

