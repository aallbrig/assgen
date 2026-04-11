"""Handler for visual.texture.seamless — fix tile seams via offset-blend.

Shifts the image by half its dimensions and blends the resulting seam
using a feathered mask to produce a tileable texture.

Params:
    input       (str):   source image path
    blend_width (float): blend zone as fraction of image size (default 0.1 = 10%)
"""
from __future__ import annotations

try:
    from PIL import Image  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Make a texture seamless by offset-blending the seam region."""
    if not _AVAILABLE:
        raise RuntimeError("Pillow is not installed. Run: pip install Pillow")

    from pathlib import Path

    import numpy as np
    from PIL import Image

    input_path = params.get("input", "")
    if not Path(input_path).exists():
        raise ValueError(f"Input file not found: {input_path}")

    blend_width: float = float(params.get("blend_width", 0.1))
    blend_width = max(0.01, min(0.49, blend_width))

    progress_cb(0.0, "Loading image")
    img = Image.open(input_path).convert("RGBA")
    w, h = img.size
    arr = np.array(img, dtype=np.float32)

    progress_cb(0.2, "Creating offset copy")
    # Roll by half the image dimensions to centre the seam
    rolled = np.roll(np.roll(arr, h // 2, axis=0), w // 2, axis=1)

    # Build a blend mask: fade from 0→1 near horizontal and vertical seams
    bw_px_x = max(1, int(w * blend_width))
    bw_px_y = max(1, int(h * blend_width))

    mask_x = np.ones(w, dtype=np.float32)
    mask_x[:bw_px_x] = np.linspace(0, 1, bw_px_x)
    mask_x[-bw_px_x:] = np.linspace(1, 0, bw_px_x)

    mask_y = np.ones(h, dtype=np.float32)
    mask_y[:bw_px_y] = np.linspace(0, 1, bw_px_y)
    mask_y[-bw_px_y:] = np.linspace(1, 0, bw_px_y)

    # Outer product: blend only near both seam edges simultaneously
    mask_2d = np.minimum(
        mask_x[np.newaxis, :, np.newaxis],
        mask_y[:, np.newaxis, np.newaxis],
    )

    progress_cb(0.6, "Blending seams")
    blended = arr * mask_2d + rolled * (1.0 - mask_2d)
    result = np.clip(blended, 0, 255).astype(np.uint8)

    progress_cb(0.9, "Saving")
    stem = Path(input_path).stem
    out_path = Path(output_dir) / f"{stem}_seamless.png"
    Image.fromarray(result, "RGBA").save(str(out_path))

    progress_cb(1.0, "Done")
    return {
        "files": [str(out_path)],
        "metadata": {
            "width": w,
            "height": h,
            "blend_width": blend_width,
        },
    }
