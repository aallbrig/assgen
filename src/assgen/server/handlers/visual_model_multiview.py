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

try:
    from diffusers import DiffusionPipeline  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Generate 6 surrounding views from a single concept image via Zero123++."""
    if not _AVAILABLE:
        raise RuntimeError(
            "diffusers is required. Run: pip install diffusers transformers accelerate torch"
        )

    import torch
    from pathlib import Path
    from PIL import Image
    from diffusers import DiffusionPipeline

    out_dir = Path(output_dir)

    # Resolve input image — prefer upstream_files, fall back to explicit param
    input_image_path: str | None = params.get("image")
    if not input_image_path:
        upstream = params.get("upstream_files", [])
        image_exts = {".png", ".jpg", ".jpeg", ".webp"}
        input_image_path = next(
            (f for f in upstream if Path(f).suffix.lower() in image_exts), None
        )
    if not input_image_path:
        raise ValueError(
            "'image' param or upstream_files with an image are required for visual.model.multiview"
        )

    progress_cb(0.05, "Loading input image…")
    input_image = Image.open(input_image_path).convert("RGB")

    progress_cb(0.10, "Loading Zero123++ pipeline…")
    hf_id = model_path or model_id or "sudo-ai/zero123plus"
    dtype = torch.float16 if device != "cpu" else torch.float32

    pipe = DiffusionPipeline.from_pretrained(
        hf_id,
        custom_pipeline="sudo-ai/zero123plus",
        torch_dtype=dtype,
    ).to(device)
    pipe.set_progress_bar_config(disable=True)

    progress_cb(0.15, "Generating 6-view turnaround…")
    result = pipe(input_image, num_inference_steps=36).images[0]

    # Zero123++ returns a 2×3 grid image (6 views tiled)
    # Split the grid into 6 individual view images
    grid_w, grid_h = result.size
    tile_w = grid_w // 3
    tile_h = grid_h // 2

    _VIEW_LABELS = [
        "front_right", "right", "back_right",
        "front_left",  "left",  "back_left",
    ]
    out_stem = params.get("output") or "multiview"
    out_files: list[str] = []

    # Save full grid for reference
    grid_name = f"{out_stem}_grid.png"
    result.save(str(out_dir / grid_name))
    out_files.append(grid_name)

    for idx, label in enumerate(_VIEW_LABELS):
        col = idx % 3
        row = idx // 3
        box = (col * tile_w, row * tile_h, (col + 1) * tile_w, (row + 1) * tile_h)
        view = result.crop(box)
        fname = f"{out_stem}_{label}.png"
        view.save(str(out_dir / fname))
        out_files.append(fname)
        progress_cb(0.20 + 0.70 * ((idx + 1) / 6), f"Saved view: {label}")

    progress_cb(1.0, "Done")
    return {
        "files": out_files,
        "metadata": {
            "source_image": str(input_image_path),
            "views": _VIEW_LABELS,
            "grid_file": grid_name,
        },
    }
