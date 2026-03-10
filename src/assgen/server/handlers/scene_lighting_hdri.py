"""scene.lighting.hdri — HDRI panorama generation via LDM3D-pano.

Generates an equirectangular HDRI-style panorama (RGB + depth) from a text
prompt using Intel's LDM3D-pano model.

  pip install diffusers transformers accelerate torch Pillow

Params:
    prompt          (str):  scene description
    negative_prompt (str):  negative prompt (optional)
    steps           (int):  inference steps (default: 50)
    guidance_scale  (float):CFG scale (default: 5.0)
    width           (int):  output width, must be multiple of 8 (default: 1024)
    height          (int):  output height, must be multiple of 8 (default: 512)
    output          (str):  output prefix (default: hdri_<stem>)
"""
from __future__ import annotations

try:
    from diffusers import StableDiffusionLDM3DPipeline  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Generate an equirectangular HDRI panorama from a text prompt."""
    if not _AVAILABLE:
        raise RuntimeError(
            "diffusers is required. Run: pip install diffusers transformers accelerate torch"
        )

    import torch
    from pathlib import Path
    from PIL import Image
    from diffusers import StableDiffusionLDM3DPipeline

    prompt = params.get("prompt", "")
    if not prompt:
        raise ValueError("'prompt' is required for HDRI generation")

    negative_prompt = params.get("negative_prompt", "")
    steps = int(params.get("steps", 50))
    guidance = float(params.get("guidance_scale", 5.0))
    width = int(params.get("width", 1024))
    height = int(params.get("height", 512))
    # Round to multiples of 8
    width = max(8, width - (width % 8))
    height = max(8, height - (height % 8))

    out_prefix = params.get("output") or "hdri_scene"
    rgb_name = f"{out_prefix}_rgb.png"
    depth_name = f"{out_prefix}_depth.png"
    out_dir = Path(output_dir)

    progress_cb(0.05, "Loading LDM3D-pano pipeline…")
    hf_id = model_path or model_id or "Intel/ldm3d-pano"
    dtype = torch.float16 if device != "cpu" else torch.float32
    pipe = StableDiffusionLDM3DPipeline.from_pretrained(
        hf_id,
        torch_dtype=dtype,
    ).to(device)

    progress_cb(0.3, f"Generating panorama ({width}×{height})…")
    result = pipe(
        prompt=prompt,
        negative_prompt=negative_prompt or None,
        num_inference_steps=steps,
        guidance_scale=guidance,
        width=width,
        height=height,
    )

    out_files = []
    progress_cb(0.9, "Saving outputs…")

    rgb_img: Image.Image = result.rgb[0]
    rgb_img.save(str(out_dir / rgb_name))
    out_files.append(rgb_name)

    if hasattr(result, "depth") and result.depth:
        depth_img: Image.Image = result.depth[0]
        depth_img.save(str(out_dir / depth_name))
        out_files.append(depth_name)

    progress_cb(1.0, "Done")
    return {
        "files": out_files,
        "metadata": {"width": width, "height": height, "steps": steps},
    }
