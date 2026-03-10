"""scene.depth.estimate — monocular depth estimation via DPT-Large.

  pip install transformers torch Pillow

Params:
    input       (str):  path to input image (PNG/JPG)
    output      (str):  output filename (default: <stem>_depth.png)
    colormap    (bool): if true, also save a false-colour visualisation (default: true)
    normalise   (bool): normalise depth to full [0,255] range (default: true)
"""
from __future__ import annotations

try:
    from transformers import pipeline as hf_pipeline  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Estimate per-pixel depth from a single image with DPT-Large."""
    if not _AVAILABLE:
        raise RuntimeError(
            "transformers is required. Run: pip install transformers torch"
        )

    import numpy as np
    from pathlib import Path
    from PIL import Image
    from transformers import pipeline as hf_pipeline

    input_path = Path(params.get("input", ""))
    if not input_path.exists():
        raise ValueError(f"Input image not found: {input_path!r}")

    out_name = params.get("output") or f"{input_path.stem}_depth.png"
    out_path = Path(output_dir) / out_name
    do_colormap = str(params.get("colormap", "true")).lower() not in ("false", "0", "no")
    do_normalise = str(params.get("normalise", "true")).lower() not in ("false", "0", "no")

    progress_cb(0.05, "Loading DPT-Large depth estimation model…")
    hf_id = model_path or model_id or "Intel/dpt-large"
    estimator = hf_pipeline(
        task="depth-estimation",
        model=hf_id,
        device=0 if device == "cuda" else -1,
    )

    progress_cb(0.3, "Loading image…")
    image = Image.open(str(input_path)).convert("RGB")

    progress_cb(0.4, "Running depth estimation…")
    result = estimator(image)
    depth_pil: Image.Image = result["depth"]

    depth_arr = np.array(depth_pil, dtype=np.float32)
    if do_normalise:
        d_min, d_max = depth_arr.min(), depth_arr.max()
        if d_max > d_min:
            depth_arr = (depth_arr - d_min) / (d_max - d_min) * 255.0
        else:
            depth_arr[:] = 128

    out_files = [out_name]
    progress_cb(0.9, "Saving depth map…")
    Image.fromarray(depth_arr.astype(np.uint8), mode="L").save(str(out_path))

    if do_colormap:
        try:
            import cv2
            col_arr = cv2.applyColorMap(depth_arr.astype(np.uint8), cv2.COLORMAP_INFERNO)
            col_name = f"{input_path.stem}_depth_colour.png"
            cv2.imwrite(str(Path(output_dir) / col_name), col_arr)
            out_files.append(col_name)
        except ImportError:
            pass  # opencv optional for colourmap

    progress_cb(1.0, "Done")
    h, w = depth_arr.shape[:2]
    return {
        "files": out_files,
        "metadata": {"width": w, "height": h},
    }
