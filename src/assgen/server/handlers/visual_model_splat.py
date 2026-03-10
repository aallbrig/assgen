"""Handler for ``visual.model.splat`` — TripoSR image-to-3D mesh generation.

TripoSR (stabilityai/TripoSR) reconstructs a 3D mesh from one or more
multi-view input images in a single forward pass.

Dependencies
------------
Install the ``inference`` extras plus the TripoSR library::

    pip install "assgen[inference]"
    pip install tsr          # Stability AI TripoSR package

The module-level ``import tsr`` intentionally raises ``ImportError`` when the
package is absent so the worker falls back to the generic stub handler.

Params (from ``assgen gen visual model splat``)
-----------------------------------------------
images         list[str]  Multi-view input image paths (1–6 recommended)
target_faces   int        Max triangle count after decimation (default 10 000)
convert_mesh   bool       Also export a .ply alongside the .glb
output         str|None   Unused server-side (client controls save path)
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable

# Module-level imports: guard so worker falls back to stub if deps absent
try:
    from PIL import Image
    import tsr                                           # noqa: F401
    from tsr.system import TSR                           # noqa: F401
    from tsr.utils import remove_background, resize_foreground  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[float, str], None]

# TripoSR outputs ~100k-300k raw triangles at resolution=256.
# We always post-process before returning.
_INFERENCE_RESOLUTION = 256
_CHUNK_SIZE = 131_072


def run(
    job_type: str,
    params: dict[str, Any],
    model_id: str | None,
    model_path: str | None,
    device: str,
    progress_cb: ProgressCallback,
    output_dir: Path,
) -> dict[str, Any]:
    """Run TripoSR inference and return post-processed mesh paths.

    Returns:
        ``{"files": ["output.glb"], "metadata": {...}}``
    """
    if not _AVAILABLE:
        raise RuntimeError(
            "TripoSR is not installed. Run: pip install tsr  "
            "(see https://github.com/VAST-AI-Research/TripoSR)"
        )

    import torch
    from assgen.server.handlers.mesh_utils import (
        DEFAULT_TARGET_FACES,
        clean_mesh,
        mesh_stats,
    )

    images_param: list[str] = params.get("images") or []
    target_faces: int = int(params.get("target_faces") or DEFAULT_TARGET_FACES)
    convert_mesh: bool = bool(params.get("convert_mesh", False))

    if not images_param:
        raise ValueError("visual.model.splat requires at least one input image via 'images'")

    if not model_path:
        raise ValueError("model_path is required — model not downloaded yet")

    # ------------------------------------------------------------------ #
    # 1. Load model
    # ------------------------------------------------------------------ #
    progress_cb(0.20, "Loading TripoSR model…")
    model = TSR.from_pretrained(
        model_path,
        config_name="config.yaml",
        weight_name="model.ckpt",
    )
    model.renderer.set_chunk_size(_CHUNK_SIZE)
    model.to(device)
    logger.info("TripoSR loaded", extra={"device": device})

    # ------------------------------------------------------------------ #
    # 2. Pre-process input images
    # ------------------------------------------------------------------ #
    progress_cb(0.25, "Pre-processing input images…")
    pil_images: list[Image.Image] = []
    for img_path in images_param[:6]:  # TripoSR handles up to 6 views well
        img = Image.open(img_path).convert("RGBA")
        img = remove_background(img)
        img = resize_foreground(img, ratio=0.85)
        pil_images.append(img)

    # ------------------------------------------------------------------ #
    # 3. Inference
    # ------------------------------------------------------------------ #
    progress_cb(0.30, "Running TripoSR inference…")
    with torch.no_grad():
        scene_codes = model(pil_images, device=device)

    # ------------------------------------------------------------------ #
    # 4. Mesh extraction
    # ------------------------------------------------------------------ #
    progress_cb(0.65, "Extracting mesh…")
    meshes = model.extract_mesh(scene_codes, resolution=_INFERENCE_RESOLUTION)
    raw_mesh = meshes[0]

    glb_path = output_dir / "output.glb"
    raw_mesh.export(str(glb_path))
    logger.info("Raw mesh exported", extra={"path": str(glb_path), "faces": len(raw_mesh.faces)})

    # ------------------------------------------------------------------ #
    # 5. Trimesh post-processing (fill holes, fix normals, decimate)
    # ------------------------------------------------------------------ #
    progress_cb(0.80, f"Post-processing mesh → {target_faces:,} faces…")
    clean_mesh(glb_path, target_faces=target_faces)
    stats = mesh_stats(glb_path)
    logger.info("Mesh post-processing complete", extra=stats)

    output_files = ["output.glb"]

    if convert_mesh:
        ply_path = output_dir / "output.ply"
        glb_path_obj = __import__("trimesh").load(str(glb_path))
        glb_path_obj.export(str(ply_path))
        output_files.append("output.ply")

    progress_cb(0.99, "Done")
    return {
        "files": output_files,
        "metadata": {
            "model": "TripoSR",
            "input_images": len(pil_images),
            "target_faces": target_faces,
            **stats,
        },
    }
