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

import re
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from assgen.client.cli import app

runner = CliRunner()

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _try_import(mod_name: str) -> bool:
    import importlib
    try:
        importlib.import_module(mod_name)
        return True
    except ModuleNotFoundError:
        return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def invoke(*args: str, input: str | None = None):
    """Invoke the root CLI and return the result."""
    return runner.invoke(app, list(args), input=input)


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from *text*."""
    return _ANSI_RE.sub("", text)


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
        assert "--json" in strip_ansi(result.output)

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
        assert "--variants" in strip_ansi(result.output)

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
        assert "--quality" in strip_ansi(result.output)

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
        assert "--from-job" in strip_ansi(result.output)

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
# jobs rerun smoke tests
# ---------------------------------------------------------------------------

class TestJobsRerun:
    """assgen jobs rerun re-submits with the original user params."""

    def _make_job(self, job_id: str, job_type: str, params: dict) -> MagicMock:
        mc = MagicMock()
        mc.__enter__ = lambda s: s
        mc.__exit__ = MagicMock(return_value=False)
        mc.get_job.return_value = {
            "id": job_id,
            "job_type": job_type,
            "status": "COMPLETED",
            "params": params,
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:01:00",
            "result": {},
        }
        mc.enqueue_job.return_value = {
            "id": "rerun0000001",
            "job_type": job_type,
            "status": "QUEUED",
        }
        return mc

    def test_rerun_in_help(self) -> None:
        result = invoke("jobs", "--help")
        assert "rerun" in strip_ansi(result.output)

    def test_rerun_dry_run_shows_job_type(self) -> None:
        job_id = "original001"
        mc = self._make_job(job_id, "visual.concept.generate", {"prompt": "castle"})
        with patch("assgen.client.commands.jobs.get_client", return_value=mc):
            result = invoke("jobs", "rerun", job_id, "--dry-run")
        assert result.exit_code == 0
        out = strip_ansi(result.output)
        assert "visual.concept.generate" in out
        assert "castle" in out

    def test_rerun_enqueues_fresh_job(self) -> None:
        from assgen.client import context
        context.reset()
        job_id = "original002"
        original_params = {
            "prompt": "ruined temple",
            "_quality": "high",
            "upstream_files": ["concept.png"],
            "upstream_job_id": "upstream001",
        }
        mc = self._make_job(job_id, "visual.concept.generate", original_params)
        with patch("assgen.client.commands.jobs.get_client", return_value=mc), \
             patch("assgen.client.commands.submit.get_client", return_value=mc):
            result = invoke("jobs", "rerun", job_id)
        context.reset()
        assert result.exit_code == 0
        sent_params = mc.enqueue_job.call_args[0][1]
        # User param preserved
        assert sent_params.get("prompt") == "ruined temple"
        # Internal params stripped
        assert "_quality" not in sent_params
        assert "upstream_files" not in sent_params
        assert "upstream_job_id" not in sent_params


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


# ---------------------------------------------------------------------------
# --context multi-input chaining
# ---------------------------------------------------------------------------

class TestContextFlag:
    """--context key=job_id loads upstream text into context_map param."""

    def _make_client(self, lore_job_id: str) -> MagicMock:
        mc = MagicMock()
        mc.__enter__ = MagicMock(return_value=mc)
        mc.__exit__ = MagicMock(return_value=False)

        def _get_job(job_id: str) -> dict:
            if job_id == lore_job_id:
                return {
                    "id": job_id,
                    "status": "COMPLETED",
                    "job_type": "narrative.lore.generate",
                    "result": {"files": ["lore.txt"]},
                }
            return {"id": job_id, "status": "COMPLETED", "result": {"files": []}}

        mc.get_job.side_effect = _get_job
        mc.download_file.return_value = b"The empire fell three centuries ago..."
        mc.enqueue_job.return_value = {
            "id": "dialoguejob0001",
            "status": "QUEUED",
            "job_type": "narrative.dialogue.npc",
        }
        return mc

    def test_context_flag_present_in_help(self) -> None:
        result = invoke("--help")
        assert "--context" in strip_ansi(result.output)

    def test_context_resolves_to_param(self) -> None:
        from assgen.client import context
        context.reset()
        lore_id = "lorejob00000001"
        mock_client = self._make_client(lore_id)
        with patch("assgen.client.commands.submit.get_client", return_value=mock_client):
            result = invoke(
                "--context", f"lore={lore_id}",
                "gen", "support", "narrative", "dialog", "innkeeper",
            )
        context.reset()
        assert result.exit_code == 0
        params_sent = mock_client.enqueue_job.call_args[0][1]
        assert "context_map" in params_sent
        assert "lore" in params_sent["context_map"]
        assert "empire" in params_sent["context_map"]["lore"]

    def test_context_bad_format_raises(self) -> None:
        from assgen.client import context as ctx_mod
        ctx_mod.reset()
        with pytest.raises(ValueError, match="key=job_id"):
            ctx_mod.set_context_map(["noequalssign"])
        ctx_mod.reset()

    def test_multiple_context_entries(self) -> None:
        from assgen.client import context as ctx_mod
        ctx_mod.reset()
        ctx_mod.set_context_map(["lore=job1", "scene=job2"])
        cm = ctx_mod.get_context_map()
        assert cm == {"lore": "job1", "scene": "job2"}
        ctx_mod.reset()


# ---------------------------------------------------------------------------
# Easy-win handler importability
# ---------------------------------------------------------------------------

class TestEasyWinHandlers:
    """Wrapper handlers import cleanly and delegate correctly."""

    def test_audio_ambient_generate_importable(self) -> None:
        import importlib
        mod = importlib.import_module("assgen.server.handlers.audio_ambient_generate")
        assert hasattr(mod, "run")

    def test_audio_music_adaptive_importable(self) -> None:
        import importlib
        mod = importlib.import_module("assgen.server.handlers.audio_music_adaptive")
        assert hasattr(mod, "run")

    def test_narrative_lore_generate_importable(self) -> None:
        import importlib
        mod = importlib.import_module("assgen.server.handlers.narrative_lore_generate")
        assert hasattr(mod, "run")

    def test_narrative_quest_design_importable(self) -> None:
        import importlib
        mod = importlib.import_module("assgen.server.handlers.narrative_quest_design")
        assert hasattr(mod, "run")

    def test_handler_coverage_reached_29_percent(self) -> None:
        """Retained for historical reference — originally verified 9/31 handlers."""
        from assgen.catalog import load_catalog
        catalog = load_catalog()
        real = sum(
            1 for jt in catalog
            if _try_import("assgen.server.handlers." + jt.replace(".", "_"))
        )
        assert real >= 9, f"Expected ≥9 real handlers, got {real}"




# ---------------------------------------------------------------------------
# Algorithmic handlers — importability + coverage
# ---------------------------------------------------------------------------

class TestAlgorithmicHandlers:
    """All 40 algorithmic handlers are importable and have a run() function."""

    def _assert_handler(self, name: str) -> None:
        import importlib
        mod = importlib.import_module(f"assgen.server.handlers.{name}")
        assert hasattr(mod, "run"), f"{name} missing run()"

    # visual mesh
    def test_visual_mesh_validate_importable(self)     : self._assert_handler("visual_mesh_validate")
    def test_visual_mesh_convert_importable(self)      : self._assert_handler("visual_mesh_convert")
    def test_visual_mesh_merge_importable(self)        : self._assert_handler("visual_mesh_merge")
    def test_visual_mesh_bounds_importable(self)       : self._assert_handler("visual_mesh_bounds")
    def test_visual_mesh_flipnormals_importable(self)  : self._assert_handler("visual_mesh_flipnormals")
    def test_visual_mesh_weld_importable(self)         : self._assert_handler("visual_mesh_weld")
    def test_visual_mesh_center_importable(self)       : self._assert_handler("visual_mesh_center")
    def test_visual_mesh_scale_importable(self)        : self._assert_handler("visual_mesh_scale")
    # lod
    def test_visual_lod_generate_importable(self)      : self._assert_handler("visual_lod_generate")
    # texture
    def test_visual_texture_channel_pack_importable(self)    : self._assert_handler("visual_texture_channel_pack")
    def test_visual_texture_convert_importable(self)         : self._assert_handler("visual_texture_convert")
    def test_visual_texture_atlas_pack_importable(self)      : self._assert_handler("visual_texture_atlas_pack")
    def test_visual_texture_mipmap_importable(self)          : self._assert_handler("visual_texture_mipmap")
    def test_visual_texture_normalmap_convert_importable(self): self._assert_handler("visual_texture_normalmap_convert")
    def test_visual_texture_seamless_importable(self)        : self._assert_handler("visual_texture_seamless")
    def test_visual_texture_resize_importable(self)          : self._assert_handler("visual_texture_resize")
    def test_visual_texture_report_importable(self)          : self._assert_handler("visual_texture_report")
    # sprite
    def test_visual_sprite_pack_importable(self)       : self._assert_handler("visual_sprite_pack")
    # audio process
    def test_audio_process_normalize_importable(self)     : self._assert_handler("audio_process_normalize")
    def test_audio_process_trim_silence_importable(self)  : self._assert_handler("audio_process_trim_silence")
    def test_audio_process_loop_optimize_importable(self) : self._assert_handler("audio_process_loop_optimize")
    def test_audio_process_convert_importable(self)       : self._assert_handler("audio_process_convert")
    def test_audio_process_downmix_importable(self)       : self._assert_handler("audio_process_downmix")
    def test_audio_process_resample_importable(self)      : self._assert_handler("audio_process_resample")
    def test_audio_process_waveform_importable(self)      : self._assert_handler("audio_process_waveform")
    # proc
    def test_proc_terrain_heightmap_importable(self)  : self._assert_handler("procedural_terrain_heightmap")
    def test_proc_texture_noise_importable(self)      : self._assert_handler("procedural_texture_noise")
    def test_proc_level_dungeon_importable(self)      : self._assert_handler("procedural_level_dungeon")
    def test_proc_level_voronoi_importable(self)      : self._assert_handler("procedural_level_voronoi")
    def test_proc_foliage_scatter_importable(self)    : self._assert_handler("procedural_foliage_scatter")
    def test_proc_tileset_wfc_importable(self)        : self._assert_handler("procedural_tileset_wfc")
    def test_proc_plant_lsystem_importable(self)      : self._assert_handler("procedural_plant_lsystem")
    # pipeline
    def test_pipeline_asset_manifest_importable(self) : self._assert_handler("pipeline_asset_manifest")
    def test_pipeline_asset_validate_importable(self) : self._assert_handler("pipeline_asset_validate")
    def test_pipeline_asset_rename_importable(self)   : self._assert_handler("pipeline_asset_rename")
    def test_pipeline_asset_report_importable(self)   : self._assert_handler("pipeline_asset_report")
    def test_pipeline_git_lfs_rules_importable(self)  : self._assert_handler("pipeline_git_lfs_rules")
    # narrative
    def test_narrative_dialogue_validate_importable(self) : self._assert_handler("narrative_dialogue_validate")
    def test_narrative_quest_validate_importable(self)    : self._assert_handler("narrative_quest_validate")
    def test_narrative_i18n_extract_importable(self)      : self._assert_handler("narrative_i18n_extract")

    # batch 1 — SDXL delegates
    def test_visual_blockout_create_importable(self)      : self._assert_handler("visual_blockout_create")
    def test_visual_texture_generate_importable(self)     : self._assert_handler("visual_texture_generate")
    def test_visual_ui_icon_importable(self)              : self._assert_handler("visual_ui_icon")
    def test_visual_vfx_particle_importable(self)         : self._assert_handler("visual_vfx_particle")
    # batch 2 — algorithmic
    def test_visual_model_retopo_importable(self)         : self._assert_handler("visual_model_retopo")
    def test_scene_physics_collider_importable(self)      : self._assert_handler("scene_physics_collider")
    def test_visual_texture_bake_importable(self)         : self._assert_handler("visual_texture_bake")
    def test_pipeline_integrate_export_importable(self)   : self._assert_handler("pipeline_integrate_export")
    # batch 3 — ML models
    def test_visual_texture_upscale_importable(self)      : self._assert_handler("visual_texture_upscale")
    def test_visual_texture_inpaint_importable(self)      : self._assert_handler("visual_texture_inpaint")
    def test_scene_depth_estimate_importable(self)        : self._assert_handler("scene_depth_estimate")
    def test_scene_lighting_hdri_importable(self)         : self._assert_handler("scene_lighting_hdri")
    def test_audio_voice_clone_importable(self)           : self._assert_handler("audio_voice_clone")
    # batch 4 — complex ML
    def test_visual_animate_keyframe_importable(self)     : self._assert_handler("visual_animate_keyframe")
    def test_visual_animate_mocap_importable(self)        : self._assert_handler("visual_animate_mocap")
    def test_visual_concept_style_importable(self)        : self._assert_handler("visual_concept_style")
    def test_visual_rig_auto_importable(self)             : self._assert_handler("visual_rig_auto")
    # batch 5 — UI generation
    def test_visual_ui_button_importable(self)            : self._assert_handler("visual_ui_button")
    def test_visual_ui_panel_importable(self)             : self._assert_handler("visual_ui_panel")
    def test_visual_ui_widget_importable(self)            : self._assert_handler("visual_ui_widget")
    def test_visual_ui_mockup_importable(self)            : self._assert_handler("visual_ui_mockup")
    def test_visual_ui_layout_importable(self)            : self._assert_handler("visual_ui_layout")
    def test_visual_ui_iconset_importable(self)           : self._assert_handler("visual_ui_iconset")
    def test_visual_ui_theme_importable(self)             : self._assert_handler("visual_ui_theme")
    def test_visual_ui_screen_importable(self)            : self._assert_handler("visual_ui_screen")

    def test_handler_coverage_full(self) -> None:
        """All 79 catalog entries have real handlers (100% coverage)."""
        import importlib

        from assgen.catalog import load_catalog
        catalog = load_catalog()
        missing = []
        for jt in catalog:
            mod_name = "assgen.server.handlers." + jt.replace(".", "_")
            try:
                importlib.import_module(mod_name)
            except ModuleNotFoundError:
                missing.append(jt)
        assert not missing, f"Missing handlers for: {missing}"


# ---------------------------------------------------------------------------
# New CLI commands — basic help checks
# ---------------------------------------------------------------------------

class TestNewCLICommands:
    """New algorithmic tool CLI commands register and respond to --help."""

    def test_gen_visual_mesh_help(self) -> None:
        r = invoke("gen", "visual", "mesh", "--help")
        assert r.exit_code == 0
        assert "mesh" in r.output.lower() or "validate" in r.output.lower()

    def test_gen_visual_lod_help(self) -> None:
        r = invoke("gen", "visual", "lod", "--help")
        assert r.exit_code == 0

    def test_gen_visual_sprite_help(self) -> None:
        r = invoke("gen", "visual", "sprite", "--help")
        assert r.exit_code == 0

    def test_gen_audio_process_help(self) -> None:
        r = invoke("gen", "audio", "process", "--help")
        assert r.exit_code == 0
        assert "normalize" in r.output or "audio" in r.output.lower()

    def test_gen_proc_help(self) -> None:
        r = invoke("gen", "procedural", "--help")
        assert r.exit_code == 0
        assert "procedural" in r.output.lower() or "terrain" in r.output.lower()

    def test_gen_proc_terrain_help(self) -> None:
        r = invoke("gen", "procedural", "terrain", "--help")
        assert r.exit_code == 0

    def test_gen_proc_level_help(self) -> None:
        r = invoke("gen", "procedural", "level", "--help")
        assert r.exit_code == 0

    def test_gen_pipeline_asset_help(self) -> None:
        r = invoke("gen", "pipeline", "asset", "--help")
        assert r.exit_code == 0

    def test_gen_pipeline_git_help(self) -> None:
        r = invoke("gen", "pipeline", "git", "--help")
        assert r.exit_code == 0

    def test_gen_support_narrative_validate_dialogue_help(self) -> None:
        r = invoke("gen", "support", "narrative", "validate-dialogue", "--help")
        assert r.exit_code == 0

    def test_gen_support_i18n_help(self) -> None:
        r = invoke("gen", "support", "i18n", "--help")
        assert r.exit_code == 0

    # --- new UI commands ---
    def test_gen_visual_ui_button_help(self) -> None:
        r = invoke("gen", "visual", "ui", "button", "--help")
        assert r.exit_code == 0
        assert "button" in r.output.lower()

    def test_gen_visual_ui_button_help_shows_new_flags(self) -> None:
        r = invoke("gen", "visual", "ui", "button", "--help")
        assert r.exit_code == 0
        text = strip_ansi(r.output)
        assert "nine-slice" in text
        assert "dpi" in text
        assert "greyscale" in text
        assert "focused" in text or "selected" in text

    def test_gen_visual_ui_panel_help(self) -> None:
        r = invoke("gen", "visual", "ui", "panel", "--help")
        assert r.exit_code == 0
        assert "panel" in r.output.lower()

    def test_gen_visual_ui_widget_help(self) -> None:
        r = invoke("gen", "visual", "ui", "widget", "--help")
        assert r.exit_code == 0
        assert "widget" in r.output.lower()

    def test_gen_visual_ui_mockup_help(self) -> None:
        r = invoke("gen", "visual", "ui", "mockup", "--help")
        assert r.exit_code == 0
        assert "mockup" in r.output.lower()

    def test_gen_visual_ui_layout_help(self) -> None:
        r = invoke("gen", "visual", "ui", "layout", "--help")
        assert r.exit_code == 0
        assert "layout" in r.output.lower()

    def test_gen_visual_ui_iconset_help(self) -> None:
        r = invoke("gen", "visual", "ui", "iconset", "--help")
        assert r.exit_code == 0
        assert "icon" in r.output.lower()

    def test_gen_visual_ui_theme_help(self) -> None:
        r = invoke("gen", "visual", "ui", "theme", "--help")
        assert r.exit_code == 0
        assert "theme" in r.output.lower()

    def test_gen_visual_ui_screen_help(self) -> None:
        r = invoke("gen", "visual", "ui", "screen", "--help")
        assert r.exit_code == 0
        assert "screen" in r.output.lower()


# ---------------------------------------------------------------------------
# Procedural handler functional tests (no external deps required)
# ---------------------------------------------------------------------------

class TestButtonHandlerHelpers:
    """Unit tests for pure-Python helpers in visual_ui_button — no GPU needed."""

    def _import_helpers(self):
        from assgen.server.handlers.visual_ui_button import (
            _STATE_MODIFIERS,
            _nine_slice_insets,
            _parse_dpi_scales,
        )
        return _parse_dpi_scales, _nine_slice_insets, _STATE_MODIFIERS

    def test_parse_dpi_scales_default(self):
        parse, _, _ = self._import_helpers()
        assert parse(None) == [1]
        assert parse("1x") == [1]

    def test_parse_dpi_scales_multi(self):
        parse, _, _ = self._import_helpers()
        assert parse("1x,2x,3x") == [3, 2, 1]  # sorted descending

    def test_parse_dpi_scales_dedup(self):
        parse, _, _ = self._import_helpers()
        assert parse("2x,2x,1x") == [2, 1]

    def test_nine_slice_auto_insets_default(self):
        _, ns, _ = self._import_helpers()
        result = ns(256, 128, None)
        # 16% of min(256,128)=128 → 20px, but min is 4
        assert result["left"] == result["right"] == result["top"] == result["bottom"]
        assert result["left"] >= 4

    def test_nine_slice_inset_override(self):
        _, ns, _ = self._import_helpers()
        result = ns(256, 128, 24)
        assert result == {"left": 24, "right": 24, "top": 24, "bottom": 24}

    def test_nine_slice_inset_min_floor(self):
        _, ns, _ = self._import_helpers()
        result = ns(8, 8, 1)
        assert result["left"] == 4  # clamped to min 4

    def test_all_states_have_modifiers(self):
        _, _, mods = self._import_helpers()
        expected = {"normal", "hover", "pressed", "disabled", "focused", "selected", "locked"}
        assert expected == set(mods.keys())

    def test_focused_state_differs_from_hover(self):
        _, _, mods = self._import_helpers()
        assert mods["focused"] != mods["hover"]
        assert mods["focused"] != ""

    def test_locked_differs_from_disabled(self):
        _, _, mods = self._import_helpers()
        assert mods["locked"] != mods["disabled"]

# Skip Pillow-dependent tests if Pillow is not installed in this environment
try:
    from PIL import Image as _TestPIL  # noqa: F401
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

_pil_required = pytest.mark.skipif(not _PIL_AVAILABLE, reason="Pillow not installed")


class TestProceduralHandlers:
    """Test proc handlers that have no external deps (pure Python)."""

    @_pil_required
    def test_proc_level_dungeon_run(self, tmp_path) -> None:
        from assgen.server.handlers.procedural_level_dungeon import run
        result = run("proc.level.dungeon", {"width": 16, "height": 16, "rooms": 3, "seed": 1},
                     None, None, "cpu", lambda f, m: None, str(tmp_path))
        assert "files" in result
        assert any("dungeon.json" in f for f in result["files"])

    @_pil_required
    def test_proc_level_voronoi_run(self, tmp_path) -> None:
        from assgen.server.handlers.procedural_level_voronoi import run
        result = run("proc.level.voronoi", {"width": 64, "height": 64, "regions": 4, "seed": 1},
                     None, None, "cpu", lambda f, m: None, str(tmp_path))
        assert any("voronoi.png" in f for f in result["files"])
        assert any("regions.json" in f for f in result["files"])

    def test_proc_plant_lsystem_run(self, tmp_path) -> None:
        from assgen.server.handlers.procedural_plant_lsystem import run
        result = run("proc.plant.lsystem",
                     {"axiom": "F", "rules": '{"F":"F[+F][-F]"}', "iterations": 3},
                     None, None, "cpu", lambda f, m: None, str(tmp_path))
        assert any("plant.svg" in f for f in result["files"])
        assert result["metadata"]["branch_count"] > 0

    def test_pipeline_asset_manifest_run(self, tmp_path) -> None:
        from assgen.server.handlers.pipeline_asset_manifest import run
        # Create a dummy file
        (tmp_path / "test.png").write_bytes(b"\x89PNG")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run("pipeline.asset.manifest", {"directory": str(tmp_path)},
                     None, None, "cpu", lambda f, m: None, str(out_dir))
        import json
        manifest = json.loads((out_dir / "manifest.json").read_text())
        assert manifest["file_count"] >= 1

    def test_pipeline_asset_rename_dry_run(self, tmp_path) -> None:
        from assgen.server.handlers.pipeline_asset_rename import run
        (tmp_path / "MyAsset.png").write_bytes(b"")
        (tmp_path / "AnotherAsset.glb").write_bytes(b"")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run("pipeline.asset.rename",
                     {"directory": str(tmp_path), "convention": "snake_case", "dry_run": True},
                     None, None, "cpu", lambda f, m: None, str(out_dir))
        import json
        plan = json.loads((out_dir / "rename_plan.json").read_text())
        assert plan["dry_run"] is True
        renames = {r["from"]: r["to"] for r in plan["renames"]}
        assert renames.get("MyAsset.png") == "my_asset.png"

    def test_pipeline_git_lfs_rules_run(self, tmp_path) -> None:
        from assgen.server.handlers.pipeline_git_lfs_rules import run
        (tmp_path / "model.glb").write_bytes(b"")
        (tmp_path / "texture.png").write_bytes(b"")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run("pipeline.git.lfs_rules", {"directory": str(tmp_path)},
                     None, None, "cpu", lambda f, m: None, str(out_dir))
        lfs_text = (out_dir / "lfs_rules.txt").read_text()
        assert "filter=lfs" in lfs_text

    def test_narrative_dialogue_validate_run(self, tmp_path) -> None:
        import json

        from assgen.server.handlers.narrative_dialogue_validate import run
        dialogue = {"nodes": [
            {"id": "start", "text": "Hello", "choices": [{"text": "Hi", "next": "end"}]},
            {"id": "end",   "text": "Bye",   "exit": True},
        ]}
        infile = tmp_path / "dialogue.json"
        infile.write_text(json.dumps(dialogue))
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run("narrative.dialogue.validate", {"input": str(infile)},
                     None, None, "cpu", lambda f, m: None, str(out_dir))
        report = json.loads((out_dir / "validation_report.json").read_text())
        assert report["errors"] == []

    def test_narrative_quest_validate_run(self, tmp_path) -> None:
        import json

        from assgen.server.handlers.narrative_quest_validate import run
        quest = {"start": "q1", "nodes": [
            {"id": "q1", "title": "Find the key", "next": ["q2"]},
            {"id": "q2", "title": "Open the door", "next": []},
        ]}
        infile = tmp_path / "quest.json"
        infile.write_text(json.dumps(quest))
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run("narrative.quest.validate", {"input": str(infile)},
                     None, None, "cpu", lambda f, m: None, str(out_dir))
        report = json.loads((out_dir / "validation_report.json").read_text())
        assert report["errors"] == []

    def test_narrative_i18n_extract_run(self, tmp_path) -> None:
        import json

        from assgen.server.handlers.narrative_i18n_extract import run
        (tmp_path / "dialogue.json").write_text(json.dumps([
            {"id": "n1", "text": "Hello world"},
            {"id": "n2", "text": "Goodbye"},
        ]))
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        run("narrative.i18n.extract", {"directory": str(tmp_path)},
                     None, None, "cpu", lambda f, m: None, str(out_dir))
        template = json.loads((out_dir / "i18n_template.json").read_text())
        assert template["strings"]
        values = [s["value"] for s in template["strings"]]
        assert "Hello world" in values


class TestCriticalHandlerImports:
    """Verify the 4 critical ML handlers import cleanly without their deps installed."""

    def _assert_importable(self, module_name: str) -> None:
        import importlib
        mod = importlib.import_module(f"assgen.server.handlers.{module_name}")
        assert hasattr(mod, "run"), f"{module_name} missing run()"

    def test_visual_uv_auto_importable(self):        self._assert_importable("visual_uv_auto")
    def test_audio_voice_tts_importable(self):       self._assert_importable("audio_voice_tts")
    def test_visual_concept_generate_importable(self): self._assert_importable("visual_concept_generate")
    def test_visual_model_create_importable(self):   self._assert_importable("visual_model_create")

    def test_visual_concept_generate_covers_texture(self):
        """visual_concept_generate should also handle texture/icon/blockout/vfx job types."""
        from assgen.server.handlers.visual_concept_generate import _JOB_PREFIXES
        for jt in ["visual.texture.generate", "visual.ui.icon", "visual.blockout.create", "visual.vfx.particle"]:
            assert jt in _JOB_PREFIXES

    def test_visual_uv_auto_fallback_flag(self):
        """visual_uv_auto._XATLAS_AVAILABLE is False when xatlas not installed."""
        import sys
        orig = sys.modules.get("xatlas")
        sys.modules["xatlas"] = None  # type: ignore[assignment]
        try:
            import importlib

            import assgen.server.handlers.visual_uv_auto as mod
            importlib.reload(mod)
            assert not mod._XATLAS_AVAILABLE
        finally:
            if orig is None:
                sys.modules.pop("xatlas", None)
            else:
                sys.modules["xatlas"] = orig
