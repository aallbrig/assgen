"""Model↔task compatibility validation and server allow-list enforcement.

When a job is submitted the server:
1. Checks the model_id is on the allow_list (if one is configured).
2. Fetches the model's `pipeline_tag` from the HuggingFace Hub API.
3. Verifies that tag is compatible with the catalog task for this job type.

Both checks can be bypassed by setting ``skip_model_validation: true`` in
server.yaml (server admin opt-out).  The allow-list is *always* enforced
unless it is empty (empty = "allow everything").

HF Hub API is queried via a lightweight HTTP call so that the inference
extras (torch, transformers, …) are not required just for validation.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Task → acceptable HF pipeline_tag values
#
# Each catalog `task` string maps to a frozenset of HF pipeline_tag values
# that make sense for that task.  A model whose pipeline_tag is NOT in the
# set will be rejected unless the server is configured to skip validation.
# ---------------------------------------------------------------------------

TASK_COMPATIBLE_TAGS: dict[str, frozenset[str]] = {
    # 2-D image generation
    "text-to-image":      frozenset({"text-to-image"}),
    "image-to-image":     frozenset({"image-to-image", "text-to-image"}),
    "inpainting":         frozenset({"image-to-image", "text-to-image"}),

    # 3-D geometry
    "image-to-3d":        frozenset({"image-to-3d", "text-to-3d"}),
    "text-to-3d":         frozenset({"text-to-3d", "image-to-3d"}),
    "image-to-3dgs":      frozenset({"image-to-3d", "text-to-3d", "image-to-3dgs"}),
    "mesh-retopology":    frozenset({"image-to-3d", "text-to-3d", "mesh-retopology"}),
    "uv-unwrap":          frozenset({"image-to-3d", "text-to-3d", "uv-unwrap"}),

    # Texture / material
    "texture-generation": frozenset({"text-to-image", "image-to-image", "texture-generation"}),
    "texture-bake":       frozenset({"texture-bake", "text-to-image", "image-to-image"}),

    # Rigging / animation
    "auto-rig":           frozenset({"auto-rig", "image-to-3d", "object-detection", "image-classification"}),
    "skeleton-rig":       frozenset({"skeleton-rig", "image-to-3d"}),
    "motion-retarget":    frozenset({"motion-retarget", "skeleton-rig"}),
    "text-to-animation":  frozenset({"text-to-motion", "text-to-video", "text-to-animation", "animation-generate"}),
    "text-to-motion":     frozenset({"text-to-motion", "text-to-video"}),
    "video-to-motion":    frozenset({"video-to-motion", "video-classification"}),
    "video-to-pose":      frozenset({"video-classification", "image-classification", "video-to-pose", "pose-estimation"}),
    "animation-generate": frozenset({"text-to-motion", "animation-generate"}),

    # Audio — MusicGen and AudioGen both have pipeline_tag "text-to-audio" on HF
    "text-to-audio":      frozenset({"text-to-audio", "audio-to-audio", "text-to-speech"}),
    "text-to-music":      frozenset({"text-to-audio", "audio-generation", "music-generation"}),
    "audio-generation":   frozenset({"text-to-audio", "audio-generation"}),
    "music-generation":   frozenset({"text-to-audio", "audio-generation", "music-generation"}),
    "audio-to-audio":     frozenset({"audio-to-audio", "text-to-audio"}),
    "automatic-speech-recognition": frozenset({"automatic-speech-recognition"}),

    # Voice
    "text-to-speech":     frozenset({"text-to-speech", "text-to-audio"}),
    "voice-clone":        frozenset({"text-to-speech", "voice-conversion", "voice-clone", "text-to-audio"}),

    # Video
    "text-to-video":      frozenset({"text-to-video"}),
    "image-to-video":     frozenset({"image-to-video", "text-to-video"}),

    # Scene / environment
    "text-to-panorama":   frozenset({"text-to-image", "text-to-panorama", "text-to-3d", "image-to-image"}),
    "collision-mesh":     frozenset({"collision-mesh", "image-to-3d", "text-to-3d"}),
    "mesh-export":        frozenset({"mesh-export"}),

    # Pose / keypoints (facebook/sapiens-pose-0.3b has pipeline_tag "keypoint-detection")
    "keypoint-detection": frozenset({"keypoint-detection", "image-to-image", "image-classification"}),

    # NLP / support
    "text-generation":    frozenset({"text-generation", "text2text-generation"}),
    "translation":        frozenset({"translation", "text2text-generation"}),
    "question-answering": frozenset({"question-answering"}),
    "feature-extraction": frozenset({"feature-extraction"}),
    "depth-estimation":   frozenset({"depth-estimation"}),
    "object-detection":   frozenset({"object-detection"}),
    "image-segmentation": frozenset({"image-segmentation"}),
}

# ---------------------------------------------------------------------------
# Allow-list helpers
# ---------------------------------------------------------------------------


def check_allow_list(model_id: str, server_cfg: dict[str, Any]) -> None:
    """Raise ``ValueError`` if *model_id* is not on the configured allow list.

    An empty (or absent) allow_list means *all* models are permitted.
    """
    allow_list: list[str] = server_cfg.get("allow_list") or []
    if not allow_list:
        return  # open policy — everything is allowed
    if model_id not in allow_list:
        raise ValueError(
            f"Model '{model_id}' is not on the server allow_list. "
            "Ask the server administrator to add it, or set allow_list: [] to allow all models."
        )


# ---------------------------------------------------------------------------
# HuggingFace Hub tag fetching
# ---------------------------------------------------------------------------


def fetch_hf_pipeline_tag(model_id: str) -> str | None:
    """Return the HF ``pipeline_tag`` for *model_id*, or ``None`` on failure.

    Uses a lightweight HTTP call to the HF Hub REST API — no heavy
    ML dependencies required.
    """
    try:
        import httpx
        url = f"https://huggingface.co/api/models/{model_id}?fields=pipeline_tag"
        resp = httpx.get(url, timeout=10.0, follow_redirects=True)
        if resp.status_code == 200:
            tag = resp.json().get("pipeline_tag")
            logger.debug("HF pipeline_tag for %s: %s", model_id, tag)
            return tag
        logger.warning(
            "HF Hub API returned %d for model %s — skipping tag validation",
            resp.status_code, model_id,
        )
    except Exception as exc:
        logger.warning("Could not fetch HF pipeline_tag for %s: %s", model_id, exc)
    return None


# ---------------------------------------------------------------------------
# Compatibility validation
# ---------------------------------------------------------------------------


def validate_model_task_compatibility(
    model_id: str,
    catalog_task: str | None,
    server_cfg: dict[str, Any],
) -> tuple[bool, str]:
    """Check whether *model_id* is suitable for *catalog_task*.

    Returns ``(ok, reason)`` where *reason* is a human-readable explanation
    when ``ok`` is ``False``.

    Validation is skipped (returns ``(True, "skipped")`` ) when:
    - ``server_cfg["skip_model_validation"]`` is truthy
    - ``catalog_task`` is ``None`` (job type has no associated HF task)
    - The task is not in ``TASK_COMPATIBLE_TAGS`` (unknown/custom task)
    - The HF Hub API returns no pipeline_tag for the model
    """
    if server_cfg.get("skip_model_validation"):
        return True, "validation skipped (server config)"

    if not catalog_task:
        return True, "no task constraint for this job type"

    compatible = TASK_COMPATIBLE_TAGS.get(catalog_task)
    if compatible is None:
        logger.debug(
            "Task '%s' not in TASK_COMPATIBLE_TAGS — skipping validation", catalog_task
        )
        return True, f"task '{catalog_task}' has no compatibility rules defined"

    pipeline_tag = fetch_hf_pipeline_tag(model_id)
    if pipeline_tag is None:
        logger.warning(
            "Could not determine pipeline_tag for %s — allowing by default", model_id
        )
        return True, "could not fetch pipeline_tag from HF Hub — allowed by default"

    if pipeline_tag in compatible:
        return True, f"compatible ({pipeline_tag} ∈ {sorted(compatible)})"

    return False, (
        f"Model '{model_id}' has pipeline_tag='{pipeline_tag}' which is not "
        f"compatible with task '{catalog_task}'. "
        f"Expected one of: {sorted(compatible)}. "
        "Set skip_model_validation: true in server.yaml to override."
    )


# ---------------------------------------------------------------------------
# Combined validation entry point
# ---------------------------------------------------------------------------


def validate_job_model(
    model_id: str,
    catalog_task: str | None,
    server_cfg: dict[str, Any],
) -> None:
    """Run all validations for a given *model_id* + *catalog_task* pair.

    Raises ``ValueError`` with a descriptive message on failure.
    """
    check_allow_list(model_id, server_cfg)
    ok, reason = validate_model_task_compatibility(model_id, catalog_task, server_cfg)
    if not ok:
        raise ValueError(reason)
    logger.debug("Model validation passed for %s: %s", model_id, reason)
