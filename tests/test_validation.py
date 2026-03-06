"""Tests for assgen.server.validation — allow-list and model/task compatibility."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from assgen.server.validation import (
    TASK_COMPATIBLE_TAGS,
    check_allow_list,
    validate_model_task_compatibility,
    validate_job_model,
)


# ---------------------------------------------------------------------------
# Allow-list enforcement
# ---------------------------------------------------------------------------

class TestCheckAllowList:
    def test_empty_allow_list_permits_everything(self) -> None:
        cfg: dict = {"allow_list": []}
        check_allow_list("org/any-model", cfg)  # should not raise

    def test_absent_allow_list_permits_everything(self) -> None:
        cfg: dict = {}
        check_allow_list("org/any-model", cfg)  # should not raise

    def test_model_on_list_is_permitted(self) -> None:
        cfg = {"allow_list": ["stabilityai/TripoSR", "facebook/audiogen-medium"]}
        check_allow_list("stabilityai/TripoSR", cfg)  # should not raise

    def test_model_not_on_list_raises(self) -> None:
        cfg = {"allow_list": ["stabilityai/TripoSR"]}
        with pytest.raises(ValueError, match="not on the server allow_list"):
            check_allow_list("facebook/audiogen-medium", cfg)

    def test_error_message_contains_model_id(self) -> None:
        cfg = {"allow_list": ["other/model"]}
        with pytest.raises(ValueError, match="facebook/audiogen-medium"):
            check_allow_list("facebook/audiogen-medium", cfg)


# ---------------------------------------------------------------------------
# Task compatibility
# ---------------------------------------------------------------------------

class TestValidateModelTaskCompatibility:
    def _cfg(self, skip: bool = False) -> dict:
        return {"skip_model_validation": skip}

    def test_skips_when_config_says_so(self) -> None:
        ok, reason = validate_model_task_compatibility(
            "org/model", "text-to-image", self._cfg(skip=True)
        )
        assert ok
        assert "skipped" in reason

    def test_skips_when_no_catalog_task(self) -> None:
        ok, _ = validate_model_task_compatibility("org/model", None, self._cfg())
        assert ok

    def test_skips_when_task_not_in_rules(self) -> None:
        ok, reason = validate_model_task_compatibility(
            "org/model", "totally-unknown-task", self._cfg()
        )
        assert ok
        assert "no compatibility rules" in reason

    def test_allows_when_hf_api_unreachable(self) -> None:
        with patch(
            "assgen.server.validation.fetch_hf_pipeline_tag", return_value=None
        ):
            ok, reason = validate_model_task_compatibility(
                "org/model", "text-to-image", self._cfg()
            )
        assert ok
        assert "allowed by default" in reason

    def test_accepts_compatible_model(self) -> None:
        with patch(
            "assgen.server.validation.fetch_hf_pipeline_tag",
            return_value="text-to-image",
        ):
            ok, _ = validate_model_task_compatibility(
                "stabilityai/sdxl", "text-to-image", self._cfg()
            )
        assert ok

    def test_rejects_incompatible_model(self) -> None:
        with patch(
            "assgen.server.validation.fetch_hf_pipeline_tag",
            return_value="text-to-speech",  # wrong for image-to-3d
        ):
            ok, reason = validate_model_task_compatibility(
                "some/tts-model", "image-to-3d", self._cfg()
            )
        assert not ok
        assert "text-to-speech" in reason
        assert "image-to-3d" in reason

    def test_rejects_text_to_speech_for_image_task(self) -> None:
        with patch(
            "assgen.server.validation.fetch_hf_pipeline_tag",
            return_value="text-to-speech",
        ):
            ok, reason = validate_model_task_compatibility(
                "tts/model", "text-to-image", self._cfg()
            )
        assert not ok

    def test_accepts_audio_model_for_audio_task(self) -> None:
        with patch(
            "assgen.server.validation.fetch_hf_pipeline_tag",
            return_value="text-to-audio",
        ):
            ok, _ = validate_model_task_compatibility(
                "facebook/audiogen-medium", "text-to-audio", self._cfg()
            )
        assert ok


# ---------------------------------------------------------------------------
# Combined validate_job_model
# ---------------------------------------------------------------------------

class TestValidateJobModel:
    def test_passes_open_server(self) -> None:
        cfg: dict = {}
        with patch(
            "assgen.server.validation.fetch_hf_pipeline_tag",
            return_value="text-to-image",
        ):
            validate_job_model("stabilityai/sdxl", "text-to-image", cfg)

    def test_raises_on_deny_listed_model(self) -> None:
        cfg = {"allow_list": ["other/model"]}
        with pytest.raises(ValueError, match="not on the server allow_list"):
            validate_job_model("stabilityai/sdxl", "text-to-image", cfg)

    def test_raises_on_incompatible_model(self) -> None:
        cfg: dict = {}
        with patch(
            "assgen.server.validation.fetch_hf_pipeline_tag",
            return_value="text-to-speech",
        ):
            with pytest.raises(ValueError, match="pipeline_tag"):
                validate_job_model("tts/model", "text-to-image", cfg)

    def test_skip_validation_bypasses_incompatibility(self) -> None:
        cfg = {"skip_model_validation": True}
        # Would fail compatibility, but skip_model_validation=True overrides
        validate_job_model("tts/model", "text-to-image", cfg)

    def test_skip_validation_does_not_bypass_allow_list(self) -> None:
        """allow_list is enforced even when skip_model_validation is True."""
        cfg = {"allow_list": ["other/model"], "skip_model_validation": True}
        with pytest.raises(ValueError, match="not on the server allow_list"):
            validate_job_model("tts/model", "text-to-image", cfg)


# ---------------------------------------------------------------------------
# TASK_COMPATIBLE_TAGS structure sanity
# ---------------------------------------------------------------------------

class TestTaskCompatibleTagsStructure:
    def test_all_values_are_frozensets(self) -> None:
        for task, tags in TASK_COMPATIBLE_TAGS.items():
            assert isinstance(tags, frozenset), f"{task}: expected frozenset, got {type(tags)}"

    def test_all_tags_are_strings(self) -> None:
        for task, tags in TASK_COMPATIBLE_TAGS.items():
            for tag in tags:
                assert isinstance(tag, str), f"{task}: tag {tag!r} is not a string"

    def test_common_tasks_present(self) -> None:
        expected = {
            "text-to-image", "image-to-3d", "text-to-audio",
            "music-generation", "text-to-video",
        }
        for task in expected:
            assert task in TASK_COMPATIBLE_TAGS, f"Missing task: {task}"

    def test_audio_tasks_do_not_accept_image_tags(self) -> None:
        """Audio tasks must not allow image-generation pipeline tags."""
        image_tags = {"text-to-image", "image-to-image"}
        audio_tasks = {"text-to-audio", "audio-generation", "music-generation"}
        for task in audio_tasks:
            overlap = TASK_COMPATIBLE_TAGS.get(task, frozenset()) & image_tags
            assert not overlap, (
                f"Audio task '{task}' incorrectly accepts image tags: {overlap}"
            )

    def test_3d_tasks_do_not_accept_pure_audio_tags(self) -> None:
        audio_tags = {"text-to-audio", "text-to-speech", "audio-generation"}
        _3d_tasks = {"image-to-3d", "text-to-3d", "mesh-retopology"}
        for task in _3d_tasks:
            overlap = TASK_COMPATIBLE_TAGS.get(task, frozenset()) & audio_tags
            assert not overlap, (
                f"3D task '{task}' incorrectly accepts audio tags: {overlap}"
            )
