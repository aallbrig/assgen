"""Handler for visual.texture.channel_pack — pack R/G/B/A channels into RGBA.

Packs separate grayscale (or full-colour) images into a single RGBA texture.
Params:
    r            (str): path to image used as Red channel (required)
    g            (str): path to image used as Green channel (required)
    b            (str): path to image used as Blue channel (required)
    a            (str): path to image used as Alpha channel (optional)
    output_name  (str): output filename (default "packed.png")
"""
from __future__ import annotations

try:
    from PIL import Image  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Pack separate channel images into a single RGBA texture."""
    if not _AVAILABLE:
        raise RuntimeError("Pillow is not installed. Run: pip install Pillow")

    import numpy as np
    from pathlib import Path
    from PIL import Image

    def _load_gray(path: str, size: tuple[int, int]) -> "np.ndarray":
        img = Image.open(path).convert("L").resize(size, Image.LANCZOS)
        return np.array(img)

    r_path = params.get("r")
    g_path = params.get("g")
    b_path = params.get("b")
    a_path = params.get("a")
    output_name: str = params.get("output_name", "packed.png")

    if not r_path:
        raise ValueError("param 'r' (red channel image path) is required")
    if not g_path:
        raise ValueError("param 'g' (green channel image path) is required")
    if not b_path:
        raise ValueError("param 'b' (blue channel image path) is required")

    for label, p in [("r", r_path), ("g", g_path), ("b", b_path)]:
        if not Path(p).exists():
            raise ValueError(f"Channel image not found: {label}={p}")
    if a_path and not Path(a_path).exists():
        raise ValueError(f"Alpha channel image not found: a={a_path}")

    progress_cb(0.0, "Loading red channel")
    ref_img = Image.open(r_path).convert("L")
    size = ref_img.size

    progress_cb(0.2, "Loading channels")
    r_arr = np.array(ref_img)
    g_arr = _load_gray(g_path, size)
    b_arr = _load_gray(b_path, size)

    if a_path:
        a_arr = _load_gray(a_path, size)
        rgba = np.stack([r_arr, g_arr, b_arr, a_arr], axis=-1).astype(np.uint8)
        mode = "RGBA"
    else:
        rgba = np.stack([r_arr, g_arr, b_arr], axis=-1).astype(np.uint8)
        mode = "RGB"

    progress_cb(0.8, "Saving packed texture")
    out_path = Path(output_dir) / output_name
    Image.fromarray(rgba, mode).save(str(out_path))

    progress_cb(1.0, "Done")
    return {
        "files": [str(out_path)],
        "metadata": {
            "width": size[0],
            "height": size[1],
            "mode": mode,
            "channels_packed": ["r", "g", "b"] + (["a"] if a_path else []),
        },
    }
