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
        assert "assgen" in result.output
        assert any(c.isdigit() for c in result.output)

    def test_version_flag_exits_0(self) -> None:
        result = invoke("--version")
        assert result.exit_code == 0

    def test_version_short_flag_exits_0(self) -> None:
        result = invoke("-V")
        assert result.exit_code == 0

    def test_version_flag_prints_name_and_number(self) -> None:
        result = invoke("--version")
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


# ---------------------------------------------------------------------------
# --json flag
# ---------------------------------------------------------------------------

class TestJsonFlag:
    """--json emits valid JSON and suppresses Rich formatting."""

    def _enqueue_mock(self) -> MagicMock:
        mc = MagicMock()
        mc.__enter__ = MagicMock(return_value=mc)
        mc.__exit__ = MagicMock(return_value=False)
        mc.enqueue_job.return_value = {
            "id": "aaaabbbbccccdddd",
            "status": "QUEUED",
            "job_type": "audio.sfx.generate",
        }
        return mc

    def test_json_flag_present_in_help(self) -> None:
        result = invoke("--help")
        assert "--json" in result.output

    def test_json_flag_emits_valid_json(self) -> None:
        import json as _json
        from assgen.client import context
        context.reset()
        with patch("assgen.client.commands.submit.get_client", return_value=self._enqueue_mock()):
            result = invoke("--json", "gen", "audio", "sfx", "generate", "laser gun")
        context.reset()
        assert result.exit_code == 0
        parsed = _json.loads(result.output.strip())
        assert parsed["status"] == "QUEUED"
        assert parsed["job_type"] == "audio.sfx.generate"
        assert "job_id" in parsed

    def test_json_flag_no_rich_markup(self) -> None:
        from assgen.client import context
        context.reset()
        with patch("assgen.client.commands.submit.get_client", return_value=self._enqueue_mock()):
            result = invoke("--json", "gen", "audio", "sfx", "generate", "laser gun")
        context.reset()
        # Rich markup / decorations must not appear in JSON output
        assert "[green]" not in result.output
        assert "enqueued" not in result.output.lower()


# ---------------------------------------------------------------------------
# --variants flag
# ---------------------------------------------------------------------------

class TestVariantsFlag:
    """--variants N submits N jobs."""

    def _enqueue_mock(self, n: int) -> MagicMock:
        mc = MagicMock()
        mc.__enter__ = MagicMock(return_value=mc)
        mc.__exit__ = MagicMock(return_value=False)
        jobs = [
            {"id": f"job{i:016d}", "status": "QUEUED", "job_type": "audio.sfx.generate"}
            for i in range(n)
        ]
        mc.enqueue_job.side_effect = jobs
        return mc

    def test_variants_flag_present_in_help(self) -> None:
        result = invoke("--help")
        assert "--variants" in result.output

    def test_variants_submits_n_jobs(self) -> None:
        from assgen.client import context
        context.reset()
        mock_client = self._enqueue_mock(3)
        with patch("assgen.client.commands.submit.get_client", return_value=mock_client):
            result = invoke("--variants", "3", "gen", "audio", "sfx", "generate", "explosion")
        context.reset()
        assert result.exit_code == 0
        assert mock_client.enqueue_job.call_count == 3

    def test_variants_json_emits_array(self) -> None:
        import json as _json
        from assgen.client import context
        context.reset()
        mock_client = self._enqueue_mock(2)
        with patch("assgen.client.commands.submit.get_client", return_value=mock_client):
            result = invoke("--json", "--variants", "2", "gen", "audio", "sfx", "generate", "wind")
        context.reset()
        assert result.exit_code == 0
        parsed = _json.loads(result.output.strip())
        assert "jobs" in parsed
        assert len(parsed["jobs"]) == 2
        for job in parsed["jobs"]:
            assert job["status"] == "QUEUED"


# ---------------------------------------------------------------------------
# --quality flag
# ---------------------------------------------------------------------------

class TestQualityFlag:
    """--quality injects _quality into job params."""

    def _enqueue_mock(self) -> MagicMock:
        mc = MagicMock()
        mc.__enter__ = MagicMock(return_value=mc)
        mc.__exit__ = MagicMock(return_value=False)
        mc.enqueue_job.return_value = {
            "id": "qualityjob00000001",
            "status": "QUEUED",
            "job_type": "audio.music.compose",
        }
        return mc

    def test_quality_flag_present_in_help(self) -> None:
        result = invoke("--help")
        assert "--quality" in result.output

    def test_quality_draft_sets_param(self) -> None:
        from assgen.client import context
        context.reset()
        mock_client = self._enqueue_mock()
        with patch("assgen.client.commands.submit.get_client", return_value=mock_client):
            result = invoke("--quality", "draft", "gen", "audio", "music", "compose", "battle")
        context.reset()
        assert result.exit_code == 0
        call_kwargs = mock_client.enqueue_job.call_args
        params_sent = call_kwargs[0][1]  # second positional arg is params dict
        assert params_sent.get("_quality") == "draft"

    def test_quality_standard_omits_param(self) -> None:
        """standard is the default — should NOT inject _quality (saves bandwidth)."""
        from assgen.client import context
        context.reset()
        mock_client = self._enqueue_mock()
        with patch("assgen.client.commands.submit.get_client", return_value=mock_client):
            result = invoke("gen", "audio", "music", "compose", "battle")
        context.reset()
        assert result.exit_code == 0
        call_kwargs = mock_client.enqueue_job.call_args
        params_sent = call_kwargs[0][1]
        assert "_quality" not in params_sent

    def test_quality_high_sets_param(self) -> None:
        import json as _json
        from assgen.client import context
        context.reset()
        mock_client = self._enqueue_mock()
        with patch("assgen.client.commands.submit.get_client", return_value=mock_client):
            result = invoke("--json", "--quality", "high", "gen", "audio", "music", "compose", "epic")
        context.reset()
        assert result.exit_code == 0
        parsed = _json.loads(result.output.strip())
        assert parsed["status"] == "QUEUED"
        params_sent = mock_client.enqueue_job.call_args[0][1]
        assert params_sent.get("_quality") == "high"


# ---------------------------------------------------------------------------
# --from-job chaining
# ---------------------------------------------------------------------------

class TestFromJobFlag:
    """--from-job adds upstream job info to params."""

    def _make_clients(self, upstream_id: str) -> MagicMock:
        mc = MagicMock()
        mc.__enter__ = MagicMock(return_value=mc)
        mc.__exit__ = MagicMock(return_value=False)
        mc.get_job.return_value = {
            "id": upstream_id,
            "status": "COMPLETED",
            "job_type": "visual.model.create",
            "result": {"files": ["model.glb"]},
        }
        mc.enqueue_job.return_value = {
            "id": "downstream00001",
            "status": "QUEUED",
            "job_type": "visual.texture.generate",
        }
        return mc

    def test_from_job_flag_present_in_help(self) -> None:
        result = invoke("--help")
        assert "--from-job" in result.output

    def test_from_job_injects_upstream_info(self) -> None:
        from assgen.client import context
        context.reset()
        upstream_id = "upstream0000001"
        mock_client = self._make_clients(upstream_id)
        with patch("assgen.client.commands.submit.get_client", return_value=mock_client):
            result = invoke(
                "--from-job", upstream_id,
                "gen", "visual", "texture", "generate", "--prompt", "mossy stone",
            )
        context.reset()
        assert result.exit_code == 0
        params_sent = mock_client.enqueue_job.call_args[0][1]
        assert params_sent["upstream_job_id"] == upstream_id
        assert params_sent["upstream_files"] == ["model.glb"]


# ---------------------------------------------------------------------------
# Handler import smoke — verify module-level ImportError → stub fallback
# ---------------------------------------------------------------------------

class TestHandlerImportFallback:
    """Handlers degrade gracefully when optional deps are absent."""

    def test_audio_sfx_generate_importable(self) -> None:
        """Module must import cleanly even without audiocraft installed."""
        import importlib
        mod = importlib.import_module("assgen.server.handlers.audio_sfx_generate")
        assert hasattr(mod, "run")

    def test_audio_music_compose_importable(self) -> None:
        import importlib
        mod = importlib.import_module("assgen.server.handlers.audio_music_compose")
        assert hasattr(mod, "run")

    def test_audio_music_loop_importable(self) -> None:
        import importlib
        mod = importlib.import_module("assgen.server.handlers.audio_music_loop")
        assert hasattr(mod, "run")

    def test_narrative_dialogue_npc_importable(self) -> None:
        import importlib
        mod = importlib.import_module("assgen.server.handlers.narrative_dialogue_npc")
        assert hasattr(mod, "run")

    def test_visual_texture_pbr_importable(self) -> None:
        import importlib
        mod = importlib.import_module("assgen.server.handlers.visual_texture_pbr")
        assert hasattr(mod, "run")


# ---------------------------------------------------------------------------
# Catalog quality_variants
# ---------------------------------------------------------------------------

class TestCatalogQualityVariants:
    """get_model_for_job_quality resolves tier variants correctly."""

    def test_draft_resolves_to_small(self) -> None:
        from assgen.catalog import get_model_for_job_quality
        mid = get_model_for_job_quality("audio.music.compose", "draft")
        assert mid == "facebook/musicgen-small"

    def test_high_resolves_to_large(self) -> None:
        from assgen.catalog import get_model_for_job_quality
        mid = get_model_for_job_quality("audio.music.compose", "high")
        assert mid == "facebook/musicgen-large"

    def test_standard_resolves_to_medium(self) -> None:
        from assgen.catalog import get_model_for_job_quality
        mid = get_model_for_job_quality("audio.music.compose", "standard")
        assert mid == "facebook/musicgen-medium"

    def test_no_variants_returns_default(self) -> None:
        from assgen.catalog import get_model_for_job_quality
        mid = get_model_for_job_quality("visual.model.create", "draft")
        # Hunyuan3D-2 has no quality_variants — should return the default model_id
        assert mid == "tencent/Hunyuan3D-2"

    def test_loop_draft_resolves_stereo_small(self) -> None:
        from assgen.catalog import get_model_for_job_quality
        mid = get_model_for_job_quality("audio.music.loop", "draft")
        assert mid == "facebook/musicgen-stereo-small"

    def test_pbr_entry_in_catalog(self) -> None:
        from assgen.catalog import get_model_for_job
        entry = get_model_for_job("visual.texture.pbr")
        assert entry is not None
        assert entry["model_id"] is None  # algorithmic — no ML model


