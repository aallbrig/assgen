"""visual.concept.style — image style transfer via IP-Adapter.

Applies the visual style of a reference image to a new prompt using IP-Adapter
with SDXL as the base model.

  pip install diffusers transformers accelerate torch Pillow

Params:
    prompt          (str):  content description for the output
    style_image     (str):  path to the style reference image
    negative_prompt (str):  negative prompt (optional)
    scale           (float):IP-Adapter style influence 0.0–1.0 (default: 0.6)
    steps           (int):  inference steps (default: 30)
    width           (int):  output width (default: 1024)
    height          (int):  output height (default: 1024)
    output          (str):  output filename (default: styled.png)
"""
from __future__ import annotations

try:
    from diffusers import StableDiffusionXLPipeline  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Generate a styled image using IP-Adapter with SDXL."""
    if not _AVAILABLE:
        raise RuntimeError(
            "diffusers is required. Run: pip install diffusers transformers accelerate torch"
        )

    import torch
    from pathlib import Path
    from PIL import Image
    from diffusers import StableDiffusionXLPipeline

    prompt = params.get("prompt", "")
    if not prompt:
        raise ValueError("'prompt' is required")

    style_image_path = params.get("style_image", "")
    if not style_image_path or not Path(style_image_path).exists():
        raise ValueError(f"'style_image' not found: {style_image_path!r}")

    negative_prompt = params.get("negative_prompt", "")
    scale = float(params.get("scale", 0.6))
    steps = int(params.get("steps", 30))
    width = int(params.get("width", 1024))
    height = int(params.get("height", 1024))
    out_name = params.get("output") or "styled.png"
    out_path = Path(output_dir) / out_name

    progress_cb(0.05, "Loading SDXL pipeline…")
    base_id = model_path or model_id or "stabilityai/stable-diffusion-xl-base-1.0"
    dtype = torch.float16 if device != "cpu" else torch.float32
    pipe = StableDiffusionXLPipeline.from_pretrained(
        base_id,
        torch_dtype=dtype,
    ).to(device)

    progress_cb(0.2, "Loading IP-Adapter…")
    pipe.load_ip_adapter(
        "h94/IP-Adapter",
        subfolder="sdxl_models",
        weight_name="ip-adapter_sdxl.bin",
    )
    pipe.set_ip_adapter_scale(scale)

    progress_cb(0.3, "Loading style image…")
    style_img = Image.open(style_image_path).convert("RGB")

    progress_cb(0.4, "Running styled generation…")
    result = pipe(
        prompt=prompt,
        negative_prompt=negative_prompt or None,
        ip_adapter_image=style_img,
        num_inference_steps=steps,
        width=width,
        height=height,
    ).images[0]

    progress_cb(0.95, "Saving…")
    result.save(str(out_path))
    progress_cb(1.0, "Done")

    w, h = result.size
    return {
        "files": [out_name],
        "metadata": {"width": w, "height": h, "ip_adapter_scale": scale},
    }
