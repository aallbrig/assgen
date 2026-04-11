"""Handler for visual.texture.mipmap — generate mipmap chain from an image.

Outputs each mip level as a separate PNG file.

Params:
    input    (str): source image path
    min_size (int): stop generating mips when either dimension hits this size (default 1)
"""
from __future__ import annotations

try:
    from PIL import Image  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Generate a mipmap chain and save each level as a PNG."""
    if not _AVAILABLE:
        raise RuntimeError("Pillow is not installed. Run: pip install Pillow")

    from pathlib import Path

    from PIL import Image

    input_path = params.get("input", "")
    if not Path(input_path).exists():
        raise ValueError(f"Input file not found: {input_path}")

    min_size: int = int(params.get("min_size", 1))

    progress_cb(0.0, "Loading image")
    img = Image.open(input_path).convert("RGBA")
    stem = Path(input_path).stem

    out_files: list[str] = []
    levels: list[dict] = []
    level = 0
    current = img

    while True:
        w, h = current.size
        out_path = Path(output_dir) / f"{stem}_mip{level}.png"
        current.save(str(out_path))
        out_files.append(str(out_path))
        levels.append({"level": level, "width": w, "height": h, "file": out_path.name})

        if w <= min_size and h <= min_size:
            break
        next_w = max(min_size, w // 2)
        next_h = max(min_size, h // 2)
        current = current.resize((next_w, next_h), Image.LANCZOS)
        level += 1
        progress_cb(min(0.9, level / 15), f"Level {level}: {next_w}×{next_h}")

    progress_cb(1.0, "Done")
    return {
        "files": out_files,
        "metadata": {
            "levels": levels,
            "level_count": len(levels),
            "original_size": [img.width, img.height],
        },
    }
