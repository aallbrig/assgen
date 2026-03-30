"""Tests for the compose pipeline engine (assgen.client.compose).

Uses mock API client + mock wait to test:
  - Sequential step execution with file chaining
  - Error propagation (enqueue failure, job failure, timeout)
  - from_step dependency resolution
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from assgen.client.compose import run_pipeline


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_job(job_id: str, job_type: str, status: str = "COMPLETED", files: list[str] | None = None) -> dict[str, Any]:
    return {
        "id": job_id,
        "job_type": job_type,
        "status": status,
        "output": {"files": files or [f"/outputs/{job_id}/result.glb"]},
        "params": {},
    }


def _make_mock_client(jobs: dict[str, dict]) -> MagicMock:
    """Return a mock APIClient that returns pre-defined jobs."""
    client = MagicMock()
    call_count = {"n": 0}

    def enqueue_side_effect(job_type: str, params: dict, **kwargs: Any) -> dict:
        call_count["n"] += 1
        jid = f"job-{call_count['n']:03d}"
        jobs[jid] = _mock_job(jid, job_type)
        return {"id": jid, "status": "QUEUED", "job_type": job_type}

    client.enqueue_job.side_effect = enqueue_side_effect
    return client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPipelineExecution:
    """Test basic pipeline step sequencing."""

    def test_single_step(self) -> None:
        jobs: dict[str, dict] = {}
        mock_client = _make_mock_client(jobs)

        def fake_wait(client: Any, job_id: str, timeout: float | None = None) -> dict:
            return jobs[job_id]

        with patch("assgen.client.compose.get_client") as gc, \
             patch("assgen.client.compose.wait_for_job", side_effect=fake_wait):
            gc.return_value.__enter__ = lambda s: mock_client
            gc.return_value.__exit__ = lambda s, *a: None

            result = run_pipeline([
                {"id": "step1", "job_type": "visual.concept.generate", "params": {"prompt": "test"}},
            ])

        assert "step1" in result
        assert result["step1"]["status"] == "COMPLETED"
        mock_client.enqueue_job.assert_called_once()

    def test_multi_step_chaining(self) -> None:
        jobs: dict[str, dict] = {}
        mock_client = _make_mock_client(jobs)

        def fake_wait(client: Any, job_id: str, timeout: float | None = None) -> dict:
            return jobs[job_id]

        with patch("assgen.client.compose.get_client") as gc, \
             patch("assgen.client.compose.wait_for_job", side_effect=fake_wait):
            gc.return_value.__enter__ = lambda s: mock_client
            gc.return_value.__exit__ = lambda s, *a: None

            result = run_pipeline([
                {"id": "concept", "job_type": "visual.concept.generate", "params": {"prompt": "sword"}},
                {"id": "mesh", "job_type": "visual.model.splat", "from_step": "concept"},
                {"id": "rig", "job_type": "visual.rig.auto", "from_step": "mesh"},
            ])

        assert len(result) == 3
        assert all(r["status"] == "COMPLETED" for r in result.values())

        # Verify the second call received upstream_files from the first step
        calls = mock_client.enqueue_job.call_args_list
        assert len(calls) == 3
        mesh_params = calls[1][0][1]  # second call, second positional arg (params)
        assert "upstream_files" in mesh_params

    def test_multi_source_from_step(self) -> None:
        jobs: dict[str, dict] = {}
        mock_client = _make_mock_client(jobs)

        def fake_wait(client: Any, job_id: str, timeout: float | None = None) -> dict:
            return jobs[job_id]

        with patch("assgen.client.compose.get_client") as gc, \
             patch("assgen.client.compose.wait_for_job", side_effect=fake_wait):
            gc.return_value.__enter__ = lambda s: mock_client
            gc.return_value.__exit__ = lambda s, *a: None

            run_pipeline([
                {"id": "a", "job_type": "visual.concept.generate", "params": {"prompt": "a"}},
                {"id": "b", "job_type": "visual.concept.generate", "params": {"prompt": "b"}},
                {"id": "merge", "job_type": "visual.mesh.merge", "from_step": ["a", "b"]},
            ])

        merge_params = mock_client.enqueue_job.call_args_list[2][0][1]
        # Should have files from both step a and step b
        assert len(merge_params["upstream_files"]) == 2

    def test_global_params_merged(self) -> None:
        jobs: dict[str, dict] = {}
        mock_client = _make_mock_client(jobs)

        def fake_wait(client: Any, job_id: str, timeout: float | None = None) -> dict:
            return jobs[job_id]

        with patch("assgen.client.compose.get_client") as gc, \
             patch("assgen.client.compose.wait_for_job", side_effect=fake_wait):
            gc.return_value.__enter__ = lambda s: mock_client
            gc.return_value.__exit__ = lambda s, *a: None

            run_pipeline(
                [{"id": "s", "job_type": "visual.concept.generate", "params": {"prompt": "x"}}],
                global_params={"_quality": "draft"},
            )

        params = mock_client.enqueue_job.call_args_list[0][0][1]
        assert params["_quality"] == "draft"
        assert params["prompt"] == "x"

    def test_step_callback_called(self) -> None:
        jobs: dict[str, dict] = {}
        mock_client = _make_mock_client(jobs)
        callback_calls: list[tuple] = []

        def fake_wait(client: Any, job_id: str, timeout: float | None = None) -> dict:
            return jobs[job_id]

        def on_step(step_id: str, status: str, msg: str) -> None:
            callback_calls.append((step_id, status))

        with patch("assgen.client.compose.get_client") as gc, \
             patch("assgen.client.compose.wait_for_job", side_effect=fake_wait):
            gc.return_value.__enter__ = lambda s: mock_client
            gc.return_value.__exit__ = lambda s, *a: None

            run_pipeline(
                [{"id": "s1", "job_type": "visual.concept.generate", "params": {"prompt": "x"}}],
                on_step=on_step,
            )

        statuses = [s for _, s in callback_calls]
        assert "SUBMITTING" in statuses
        assert "RUNNING" in statuses
        assert "DONE" in statuses


class TestPipelineErrors:
    """Test error propagation and edge cases."""

    def test_missing_from_step_raises(self) -> None:
        jobs: dict[str, dict] = {}
        mock_client = _make_mock_client(jobs)

        with patch("assgen.client.compose.get_client") as gc:
            gc.return_value.__enter__ = lambda s: mock_client
            gc.return_value.__exit__ = lambda s, *a: None

            with pytest.raises(RuntimeError, match="has not completed"):
                run_pipeline([
                    {"id": "mesh", "job_type": "visual.model.splat", "from_step": "nonexistent"},
                ])

    def test_failed_job_halts_pipeline(self) -> None:
        jobs: dict[str, dict] = {}
        mock_client = _make_mock_client(jobs)

        def fake_wait(client: Any, job_id: str, timeout: float | None = None) -> dict:
            job = jobs[job_id]
            job["status"] = "FAILED"
            return job

        with patch("assgen.client.compose.get_client") as gc, \
             patch("assgen.client.compose.wait_for_job", side_effect=fake_wait):
            gc.return_value.__enter__ = lambda s: mock_client
            gc.return_value.__exit__ = lambda s, *a: None

            with pytest.raises(RuntimeError, match="FAILED"):
                run_pipeline([
                    {"id": "s1", "job_type": "visual.concept.generate", "params": {"prompt": "x"}},
                    {"id": "s2", "job_type": "visual.model.splat", "from_step": "s1"},
                ])

        # Only one job should have been enqueued (pipeline halted after step 1)
        assert mock_client.enqueue_job.call_count == 1

    def test_enqueue_failure_raises(self) -> None:
        from assgen.client.api import APIError

        mock_client = MagicMock()
        mock_client.enqueue_job.side_effect = APIError(422, "Unknown job_type")

        with patch("assgen.client.compose.get_client") as gc:
            gc.return_value.__enter__ = lambda s: mock_client
            gc.return_value.__exit__ = lambda s, *a: None

            with pytest.raises(RuntimeError, match="failed to enqueue"):
                run_pipeline([
                    {"id": "s1", "job_type": "bad.type", "params": {}},
                ])

    def test_timeout_raises(self) -> None:
        jobs: dict[str, dict] = {}
        mock_client = _make_mock_client(jobs)

        def fake_wait(client: Any, job_id: str, timeout: float | None = None) -> dict:
            raise TimeoutError("timed out")

        with patch("assgen.client.compose.get_client") as gc, \
             patch("assgen.client.compose.wait_for_job", side_effect=fake_wait):
            gc.return_value.__enter__ = lambda s: mock_client
            gc.return_value.__exit__ = lambda s, *a: None

            with pytest.raises(RuntimeError, match="failed"):
                run_pipeline(
                    [{"id": "s1", "job_type": "visual.concept.generate", "params": {"prompt": "x"}}],
                    timeout_per_step=0.1,
                )
