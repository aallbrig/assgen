"""Integration tests for HuggingFace connectivity and model validation.

These tests make real HTTP requests to the HuggingFace Hub API.
They are skipped automatically in offline / CI environments unless
the ``--run-integration`` flag is passed to pytest.

Run manually:
    pytest -m integration -v
    pytest -m integration -v --tb=short tests/test_hf_integration.py
"""
from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.integration


def _has_network() -> bool:
    """Quick check — returns False if HF Hub API is unreachable."""
    try:
        import urllib.request
        urllib.request.urlopen(
            "https://huggingface.co/api/models/stabilityai/stable-diffusion-xl-base-1.0"
            "?fields=pipeline_tag",
            timeout=5,
        )
        return True
    except Exception:
        return False


_network_available = pytest.mark.skipif(
    not _has_network(),
    reason="HuggingFace Hub API not reachable — skipping integration tests",
)


# ---------------------------------------------------------------------------
# fetch_hf_pipeline_tag
# ---------------------------------------------------------------------------

class TestFetchHfPipelineTag:
    """Verify that fetch_hf_pipeline_tag() returns correct tags for known models."""

    @_network_available
    def test_sdxl_returns_text_to_image(self) -> None:
        from assgen.server.validation import fetch_hf_pipeline_tag
        tag = fetch_hf_pipeline_tag("stabilityai/stable-diffusion-xl-base-1.0")
        assert tag == "text-to-image"

    @_network_available
    def test_hunyuan3d2_returns_image_to_3d(self) -> None:
        from assgen.server.validation import fetch_hf_pipeline_tag
        tag = fetch_hf_pipeline_tag("tencent/Hunyuan3D-2")
        assert tag == "image-to-3d"

    @_network_available
    def test_triposr_returns_image_to_3d(self) -> None:
        from assgen.server.validation import fetch_hf_pipeline_tag
        tag = fetch_hf_pipeline_tag("stabilityai/TripoSR")
        assert tag == "image-to-3d"

    @_network_available
    def test_musicgen_large_returns_text_to_audio(self) -> None:
        from assgen.server.validation import fetch_hf_pipeline_tag
        tag = fetch_hf_pipeline_tag("facebook/musicgen-large")
        assert tag == "text-to-audio"

    @_network_available
    def test_audiogen_medium_has_no_pipeline_tag(self) -> None:
        """AudioGen Medium has no HF pipeline_tag — validation auto-skips for tagless models."""
        from assgen.server.validation import fetch_hf_pipeline_tag
        tag = fetch_hf_pipeline_tag("facebook/audiogen-medium")
        # AudioGen Medium deliberately has no pipeline_tag on HF Hub.
        # The validator returns True (pass) for models without a tag, so it is
        # safe to use in the catalog with task: null.
        assert tag is None

    @_network_available
    def test_bark_returns_text_to_speech(self) -> None:
        from assgen.server.validation import fetch_hf_pipeline_tag
        tag = fetch_hf_pipeline_tag("suno/bark")
        assert tag == "text-to-speech"

    @_network_available
    def test_openvoice_returns_text_to_speech(self) -> None:
        from assgen.server.validation import fetch_hf_pipeline_tag
        tag = fetch_hf_pipeline_tag("myshell-ai/OpenVoice")
        assert tag == "text-to-speech"

    @_network_available
    def test_ldm3d_pano_returns_text_to_3d(self) -> None:
        from assgen.server.validation import fetch_hf_pipeline_tag
        tag = fetch_hf_pipeline_tag("Intel/ldm3d-pano")
        assert tag == "text-to-3d"

    @_network_available
    def test_nonexistent_model_returns_none(self) -> None:
        from assgen.server.validation import fetch_hf_pipeline_tag
        tag = fetch_hf_pipeline_tag("assgen/this-model-does-not-exist-xyzzy")
        assert tag is None


# ---------------------------------------------------------------------------
# validate_model_task_compatibility (real HF calls)
# ---------------------------------------------------------------------------

class TestValidateModelTaskCompatibilityIntegration:
    """End-to-end validation using real pipeline_tags from HF Hub."""

    @_network_available
    def test_sdxl_compatible_with_text_to_image(self) -> None:
        from assgen.server.validation import validate_model_task_compatibility
        ok, reason = validate_model_task_compatibility(
            "stabilityai/stable-diffusion-xl-base-1.0", "text-to-image", {}
        )
        assert ok, reason

    @_network_available
    def test_hunyuan3d2_compatible_with_image_to_3d(self) -> None:
        from assgen.server.validation import validate_model_task_compatibility
        ok, reason = validate_model_task_compatibility(
            "tencent/Hunyuan3D-2", "image-to-3d", {}
        )
        assert ok, reason

    @_network_available
    def test_musicgen_compatible_with_text_to_audio(self) -> None:
        from assgen.server.validation import validate_model_task_compatibility
        ok, reason = validate_model_task_compatibility(
            "facebook/musicgen-large", "text-to-audio", {}
        )
        assert ok, reason

    @_network_available
    def test_audiogen_medium_passes_validation_with_null_task(self) -> None:
        """AudioGen Medium passes validation when task is null (no pipeline_tag check)."""
        from assgen.server.validation import validate_model_task_compatibility
        ok, reason = validate_model_task_compatibility(
            "facebook/audiogen-medium", None, {}
        )
        assert ok, reason

    @_network_available
    def test_bark_compatible_with_text_to_speech(self) -> None:
        from assgen.server.validation import validate_model_task_compatibility
        ok, reason = validate_model_task_compatibility(
            "suno/bark", "text-to-speech", {}
        )
        assert ok, reason

    @_network_available
    def test_sdxl_incompatible_with_image_to_3d(self) -> None:
        """An image model must not be accepted for a 3D task."""
        from assgen.server.validation import validate_model_task_compatibility
        ok, reason = validate_model_task_compatibility(
            "stabilityai/stable-diffusion-xl-base-1.0", "image-to-3d", {}
        )
        assert not ok
        assert "text-to-image" in reason

    @_network_available
    def test_bark_incompatible_with_image_to_3d(self) -> None:
        """A TTS model must not be accepted for a 3D task."""
        from assgen.server.validation import validate_model_task_compatibility
        ok, reason = validate_model_task_compatibility(
            "suno/bark", "image-to-3d", {}
        )
        assert not ok
        assert "text-to-speech" in reason


# ---------------------------------------------------------------------------
# Full catalog: every model_id that has a non-null entry validates OK
# ---------------------------------------------------------------------------

class TestCatalogModelsValidateAgainstHF:
    """Verify every catalog entry with a non-null model_id is compatible
    with its declared task when checked against the live HF Hub API.

    This is the ultimate regression guard: if someone updates the catalog
    with a broken/wrong model, this test will catch it.
    """

    @_network_available
    def test_all_catalog_models_pass_validation(self) -> None:
        from assgen.catalog import load_catalog
        from assgen.server.validation import validate_model_task_compatibility

        load_catalog.cache_clear()
        catalog = load_catalog()
        failures: list[str] = []

        for job_type, entry in sorted(catalog.items()):
            model_id = entry.get("model_id")
            task = entry.get("task")
            if not model_id:
                continue  # algorithmic task — no model to validate

            ok, reason = validate_model_task_compatibility(model_id, task, {})
            if not ok:
                failures.append(f"  {job_type}: {reason}")

        assert not failures, (
            f"{len(failures)} catalog model(s) failed validation:\n"
            + "\n".join(failures)
        )
