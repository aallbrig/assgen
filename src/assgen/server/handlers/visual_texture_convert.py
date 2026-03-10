"""Handler for visual.texture.convert — image format conversion.

Converts PNG/TGA/JPG/EXR to WebP/PNG/TGA/JPG.

Params:
    input  (str): input image path
    format (str): target format — png, jpg, tga, webp, exr (default "png")
"""
from __future__ import annotations

try:
    from PIL import Image  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Convert an image to the target format."""
    if not _AVAILABLE:
        raise RuntimeError("Pillow is not installed. Run: pip install Pillow")

    from pathlib import Path
    from PIL import Image

    input_path = params.get("input", "")
    fmt = params.get("format", "png").lower().lstrip(".")
    if not Path(input_path).exists():
        raise ValueError(f"Input file not found: {input_path}")

    _FORMAT_MAP = {
        "jpg": "JPEG",
        "jpeg": "JPEG",
        "png": "PNG",
        "tga": "TGA",
        "webp": "WEBP",
        "exr": "EXR",
        "tiff": "TIFF",
        "bmp": "BMP",
    }
    pil_format = _FORMAT_MAP.get(fmt, fmt.upper())

    progress_cb(0.0, "Loading image")
    img = Image.open(input_path)

    # JPEG does not support alpha — flatten to RGB
    if pil_format == "JPEG" and img.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        bg.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
        img = bg

    progress_cb(0.7, f"Saving as {fmt}")
    stem = Path(input_path).stem
    ext = "jpg" if fmt in ("jpg", "jpeg") else fmt
    out_path = Path(output_dir) / f"{stem}.{ext}"
    img.save(str(out_path), format=pil_format)

    progress_cb(1.0, "Done")
    return {
        "files": [str(out_path)],
        "metadata": {
            "input": input_path,
            "format": fmt,
            "width": img.width,
            "height": img.height,
            "mode": img.mode,
        },
    }
