"""Handler for visual.texture.normalmap_convert — flip G channel DX↔GL.

DirectX normal maps use +Y = down (G channel inverted relative to OpenGL).
This handler flips the G channel to convert between conventions.

Params:
    input       (str): path to normal map image
    from_format (str): source convention "dx" or "gl" (default "dx")
                       The handler flips G to produce the opposite convention.
"""
from __future__ import annotations

try:
    from PIL import Image  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Flip the G channel of a normal map to convert DX↔GL conventions."""
    if not _AVAILABLE:
        raise RuntimeError("Pillow is not installed. Run: pip install Pillow")

    import numpy as np
    from pathlib import Path
    from PIL import Image

    input_path = params.get("input", "")
    if not Path(input_path).exists():
        raise ValueError(f"Input file not found: {input_path}")

    from_fmt = params.get("from_format", "dx").lower()
    to_fmt = "gl" if from_fmt == "dx" else "dx"

    progress_cb(0.0, "Loading normal map")
    img = Image.open(input_path).convert("RGB")
    arr = np.array(img).astype(np.uint16)

    progress_cb(0.4, f"Flipping G channel ({from_fmt}→{to_fmt})")
    arr[:, :, 1] = 255 - arr[:, :, 1]

    progress_cb(0.8, "Saving")
    stem = Path(input_path).stem
    out_path = Path(output_dir) / f"{stem}_{to_fmt}.png"
    Image.fromarray(arr.astype(np.uint8), "RGB").save(str(out_path))

    progress_cb(1.0, "Done")
    return {
        "files": [str(out_path)],
        "metadata": {
            "from_format": from_fmt,
            "to_format": to_fmt,
            "width": img.width,
            "height": img.height,
        },
    }
