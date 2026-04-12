"""visual.model.multiview — single image → 6 surrounding views via Zero123++.

Generates six camera-orbit views of a subject from a single concept image.
These views substantially improve downstream mesh quality when fed into
visual.model.splat (TripoSR) compared to single-image reconstruction.

  pip install diffusers transformers accelerate torch Pillow

Params:
    upstream_files  (list): output files from a prior job; first image file is used
    image           (str):  explicit path to input image (alternative to upstream_files)
    prompt          (str):  optional text prompt to guide generation (usually blank for Zero123++)
    output          (str):  output filename stem (default: multiview)
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from diffusers import DiffusionPipeline  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False

_VIEW_LABELS = [
    "front_right", "right", "back_right",
    "front_left",  "left",  "back_left",
]


def _resolve_input_image(params: dict) -> str | None:
    image_exts = {".png", ".jpg", ".jpeg", ".webp"}
    p = params.get("image")
    if p:
        return p
    for f in params.get("upstream_files", []):
        if Path(f).suffix.lower() in image_exts:
            return f
    return None


def _stub_multiview(params: dict, output_dir: Path, progress_cb) -> dict:
    """Generate 6 copies of the input image as placeholder views."""
    from PIL import Image

    input_path = _resolve_input_image(params)
    out_stem = params.get("output") or "multiview"

    if input_path and Path(input_path).exists():
        src = Image.open(input_path).convert("RGB")
    else:
        src = Image.new("RGB", (512, 512), color=(128, 128, 128))

    out_files: list[str] = []
    grid_w, grid_h = src.size * 3, src.size[1] * 2  # type: ignore[operator]

    # Build simple 3×2 grid
    grid_w = src.width * 3
    grid_h = src.height * 2
    grid = Image.new("RGB", (grid_w, grid_h))
    for idx, label in enumerate(_VIEW_LABELS):
        col = idx % 3
        row = idx // 3
        grid.paste(src, (col * src.width, row * src.height))
        fname = f"{out_stem}_{label}.png"
        src.save(str(output_dir / fname))
        out_files.append(str(output_dir / fname))
        progress_cb(0.2 + 0.6 * ((idx + 1) / 6), f"Stub view: {label}")

    grid_name = f"{out_stem}_grid.png"
    grid.save(str(output_dir / grid_name))
    out_files.insert(0, str(output_dir / grid_name))

    progress_cb(1.0, "Stub multiview done")
    return {
        "files": out_files,
        "metadata": {
            "stub": True,
            "reason": "Zero123++ requires HF auth or is unavailable",
            "source_image": str(input_path),
            "views": _VIEW_LABELS,
            "grid_file": grid_name,
        },
    }


def _run_real_multiview(params: dict, model_path, device, progress_cb, output_dir: Path) -> dict:
    import torch
    from diffusers import DiffusionPipeline
    from PIL import Image

    input_path = _resolve_input_image(params)
    if not input_path:
        raise ValueError("'image' param or upstream_files with an image are required")

    progress_cb(0.05, "Loading input image…")
    input_image = Image.open(input_path).convert("RGB")

    progress_cb(0.10, "Loading Zero123++ pipeline…")
    hf_id = model_path or "sudo-ai/zero123plus"
    dtype = torch.float16 if device != "cpu" else torch.float32
    pipe = DiffusionPipeline.from_pretrained(
        hf_id,
        custom_pipeline="sudo-ai/zero123plus",
        torch_dtype=dtype,
    ).to(device)
    pipe.set_progress_bar_config(disable=True)

    progress_cb(0.15, "Generating 6-view turnaround…")
    result = pipe(input_image, num_inference_steps=36).images[0]

    grid_w, grid_h = result.size
    tile_w = grid_w // 3
    tile_h = grid_h // 2

    out_stem = params.get("output") or "multiview"
    out_files: list[str] = []

    grid_name = f"{out_stem}_grid.png"
    result.save(str(output_dir / grid_name))
    out_files.append(str(output_dir / grid_name))

    for idx, label in enumerate(_VIEW_LABELS):
        col = idx % 3
        row = idx // 3
        box = (col * tile_w, row * tile_h, (col + 1) * tile_w, (row + 1) * tile_h)
        view = result.crop(box)
        fname = f"{out_stem}_{label}.png"
        view.save(str(output_dir / fname))
        out_files.append(str(output_dir / fname))
        progress_cb(0.20 + 0.70 * ((idx + 1) / 6), f"Saved view: {label}")

    progress_cb(1.0, "Done")
    return {
        "files": out_files,
        "metadata": {
            "source_image": str(input_path),
            "views": _VIEW_LABELS,
            "grid_file": grid_name,
        },
    }


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Generate 6 surrounding views from a single concept image via Zero123++."""
    out_dir = Path(output_dir)
    if not _AVAILABLE:
        raise RuntimeError(
            "diffusers is required. Run: pip install diffusers transformers accelerate torch"
        )
    return _run_real_multiview(params, model_path or model_id, device, progress_cb, out_dir)
