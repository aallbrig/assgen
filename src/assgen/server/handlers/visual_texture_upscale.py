"""visual.texture.upscale — AI-based texture upscaling via Real-ESRGAN.

  pip install realesrgan basicsr torch Pillow

Params:
    input       (str):  path to input texture (PNG/JPG/WEBP)
    scale       (int):  upscale factor 2 or 4 (default: 4)
    tile        (int):  tile size for VRAM-limited GPUs (default: 0 = auto)
    output      (str):  output filename (default: <stem>_x<scale>.png)
"""
from __future__ import annotations

try:
    from realesrgan import RealESRGANer  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Upscale a texture using Real-ESRGAN."""
    if not _AVAILABLE:
        raise RuntimeError(
            "realesrgan is required. Run: pip install realesrgan basicsr torch"
        )

    import cv2
    from pathlib import Path
    from basicsr.archs.rrdbnet_arch import RRDBNet
    from realesrgan import RealESRGANer

    raw_input = params.get("input") or ""
    input_path = Path(raw_input) if raw_input else Path("")
    if not raw_input or not input_path.is_file():
        raise ValueError(f"Input file not found: {input_path!r}")

    scale = int(params.get("scale", 4))
    tile = int(params.get("tile", 0))
    out_name = params.get("output") or f"{input_path.stem}_x{scale}.png"
    out_path = Path(output_dir) / out_name

    if scale == 2:
        arch = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=2)
        dn_model = "RealESRGAN_x2plus.pth"
    else:
        arch = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
        dn_model = "RealESRGAN_x4plus.pth"

    model_weights = model_path or dn_model

    progress_cb(0.1, f"Loading Real-ESRGAN ({dn_model})…")
    use_half = (device != "cpu")
    upsampler = RealESRGANer(
        scale=scale,
        model_path=model_weights,
        model=arch,
        tile=tile,
        tile_pad=10,
        pre_pad=0,
        half=use_half,
        device=device,
    )

    progress_cb(0.3, "Reading image…")
    img = cv2.imread(str(input_path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError(f"Could not read image: {input_path}")

    progress_cb(0.5, "Upscaling…")
    out_img, _ = upsampler.enhance(img, outscale=scale)

    progress_cb(0.9, "Saving…")
    cv2.imwrite(str(out_path), out_img)
    progress_cb(1.0, "Done")

    h, w = out_img.shape[:2]
    return {
        "files": [out_name],
        "metadata": {"scale": scale, "width": w, "height": h},
    }
