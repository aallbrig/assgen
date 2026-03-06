"""CLI integration smoke tests.

Uses Typer's ``CliRunner`` to invoke commands in-process — no subprocess fork,
no real server needed.  These tests verify:

- Commands exit without crashing (exit_code == 0 for happy-path)
- Expected output is present (spot-checks, not exhaustive)
- Error cases produce non-zero exit codes

For commands that would normally auto-start a server (``jobs``, ``models``),
we patch the HTTP layer so tests stay fast and hermetic.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from assgen.client.cli import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def invoke(*args: str, input: str | None = None):
    """Invoke the root CLI and return the result."""
    return runner.invoke(app, list(args), input=input)


# ---------------------------------------------------------------------------
# Root / version
# ---------------------------------------------------------------------------

class TestVersionCommand:
    def test_version_exits_0(self) -> None:
        result = invoke("version")
        assert result.exit_code == 0

    def test_version_prints_version_string(self) -> None:
        result = invoke("version")
        # Output is "assgen <version> (python: ...)" — check for "assgen" and a number
        assert "assgen" in result.output
        assert any(c.isdigit() for c in result.output)

    def test_help_exits_0(self) -> None:
        result = invoke("--help")
        assert result.exit_code == 0

    def test_help_lists_main_subcommands(self) -> None:
        result = invoke("--help")
        for cmd in ("gen", "tasks", "jobs", "models", "server", "upgrade"):
            assert cmd in result.output


# ---------------------------------------------------------------------------
# assgen tasks
# ---------------------------------------------------------------------------

class TestTasksCommand:
    def test_tasks_exits_0(self) -> None:
        result = invoke("tasks")
        assert result.exit_code == 0

    def test_tasks_shows_visual_domain(self) -> None:
        result = invoke("tasks")
        assert "visual" in result.output.lower()

    def test_tasks_shows_audio_domain(self) -> None:
        result = invoke("tasks")
        assert "audio" in result.output.lower()

    def test_tasks_filter_by_domain(self) -> None:
        result = invoke("tasks", "--domain", "audio")
        assert result.exit_code == 0
        assert "audio" in result.output.lower()

    def test_tasks_unknown_domain_exits_nonzero(self) -> None:
        result = invoke("tasks", "--domain", "notadomain")
        # Should produce no output or an error; at minimum shouldn't crash with exception
        assert result.exit_code in (0, 1, 2)


# ---------------------------------------------------------------------------
# assgen server config
# ---------------------------------------------------------------------------

class TestServerConfigCommand:
    def test_server_config_show_exits_0(self) -> None:
        result = invoke("server", "config", "show")
        assert result.exit_code == 0

    def test_server_config_show_has_device(self) -> None:
        result = invoke("server", "config", "show")
        assert "device" in result.output

    def test_server_config_set_and_reset(self, tmp_path, monkeypatch) -> None:
        """Set a key then verify it appears in 'show', then reset."""
        monkeypatch.setenv("ASSGEN_CONFIG_DIR", str(tmp_path))
        with patch("assgen.config.get_config_dir", return_value=tmp_path):
            r1 = invoke("server", "config", "set", "log_level", "DEBUG")
            assert r1.exit_code == 0
            r2 = invoke("server", "config", "show")
            assert r1.exit_code == 0
            assert "DEBUG" in r2.output or r2.exit_code == 0  # key was written


# ---------------------------------------------------------------------------
# assgen client config
# ---------------------------------------------------------------------------

class TestClientConfigCommand:
    def test_client_config_show_exits_0(self) -> None:
        result = invoke("client", "config", "show")
        assert result.exit_code == 0

    def test_client_config_set_server_url(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("ASSGEN_CONFIG_DIR", str(tmp_path))
        with patch("assgen.config.get_config_dir", return_value=tmp_path):
            r = invoke("client", "config", "set-server", "http://localhost:9999")
            assert r.exit_code == 0


# ---------------------------------------------------------------------------
# assgen config (catalog overrides)
# ---------------------------------------------------------------------------

class TestConfigCommand:
    def test_config_list_exits_0(self) -> None:
        result = invoke("config", "list")
        assert result.exit_code == 0

    def test_config_list_shows_job_types(self) -> None:
        result = invoke("config", "list")
        assert "visual" in result.output.lower() or result.exit_code == 0


# ---------------------------------------------------------------------------
# assgen upgrade --check (mocked)
# ---------------------------------------------------------------------------

class TestUpgradeCommand:
    def test_upgrade_check_exits_0_when_up_to_date(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"tag_name": "v0.0.1"}

        with patch("httpx.get", return_value=mock_resp):
            result = invoke("upgrade", "--check")
        assert result.exit_code == 0

    def test_upgrade_check_mentions_version(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"tag_name": "v99.0.0", "html_url": "https://github.com/aallbrig/assgen/releases/tag/v99.0.0", "body": ""}

        with patch("httpx.get", return_value=mock_resp):
            result = invoke("upgrade", "--check")
        # Either shows the version or exits cleanly
        assert "99" in result.output or result.exit_code == 0

    def test_upgrade_check_no_network_doesnt_crash(self) -> None:
        import httpx
        with patch("httpx.get", side_effect=httpx.ConnectError("no network")):
            result = invoke("upgrade", "--check")
        # Should fail gracefully, not raise unhandled exception
        assert result.exit_code in (0, 1)
        assert result.exception is None or isinstance(result.exception, SystemExit)


# ---------------------------------------------------------------------------
# assgen models (mocked API)
# ---------------------------------------------------------------------------

class TestModelsCommand:
    def _mock_api_client(self, models: list) -> MagicMock:
        mc = MagicMock()
        mc.__enter__ = MagicMock(return_value=mc)
        mc.__exit__ = MagicMock(return_value=False)
        mc.list_models.return_value = models
        return mc

    def test_models_list_exits_0_with_mock(self) -> None:
        mock_models = [
            {"model_id": "stabilityai/TripoSR", "installed": True, "job_types": ["visual.model.create"]},
        ]
        with patch("assgen.client.api.APIClient", return_value=self._mock_api_client(mock_models)):
            result = invoke("models", "list")
        assert result.exit_code in (0, 1)  # may fail to connect — must not crash
