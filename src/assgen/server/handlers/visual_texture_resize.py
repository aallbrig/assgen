"""Handler for visual.texture.resize — resize a texture image.

Params:
    input  (str): source image path
    width  (int): target width in pixels
    height (int): target height in pixels
    pow2   (bool): snap width/height to next power-of-2 (default false)
"""
from __future__ import annotations

try:
    from PIL import Image  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def _next_pow2(n: int) -> int:
    p = 1
    while p < n:
        p <<= 1
    return p


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Resize a texture to the specified dimensions."""
    if not _AVAILABLE:
        raise RuntimeError("Pillow is not installed. Run: pip install Pillow")

    from pathlib import Path
    from PIL import Image

    input_path = params.get("input", "")
    if not Path(input_path).exists():
        raise ValueError(f"Input file not found: {input_path}")

    progress_cb(0.0, "Loading image")
    img = Image.open(input_path)
    orig_w, orig_h = img.size

    target_w = int(params.get("width", orig_w))
    target_h = int(params.get("height", orig_h))
    pow2 = str(params.get("pow2", "false")).lower() in ("true", "1", "yes")

    if pow2:
        target_w = _next_pow2(target_w)
        target_h = _next_pow2(target_h)

    progress_cb(0.5, f"Resizing to {target_w}×{target_h}")
    resized = img.resize((target_w, target_h), Image.LANCZOS)

    stem = Path(input_path).stem
    suffix = Path(input_path).suffix or ".png"
    out_path = Path(output_dir) / f"{stem}_resized{suffix}"
    resized.save(str(out_path))

    progress_cb(1.0, "Done")
    return {
        "files": [str(out_path)],
        "metadata": {
            "original_size": [orig_w, orig_h],
            "output_size": [target_w, target_h],
            "pow2_snapped": pow2,
        },
    }
