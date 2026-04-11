"""visual.texture.inpaint — texture inpainting via SDXL Inpainting.

  pip install diffusers transformers accelerate torch Pillow

Params:
    input       (str):  path to source texture
    mask        (str):  path to mask image (white = inpaint region)
    prompt      (str):  text prompt for inpainting
    negative_prompt (str): negative prompt (optional)
    strength    (float): inpainting strength 0.0-1.0 (default: 0.99)
    steps       (int):  inference steps (default: 30)
    output      (str):  output filename (default: <stem>_inpainted.png)
"""
from __future__ import annotations

try:
    from diffusers import StableDiffusionXLInpaintPipeline  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Inpaint a masked region with SDXL Inpainting."""
    if not _AVAILABLE:
        raise RuntimeError(
            "diffusers is required. Run: pip install diffusers transformers accelerate torch"
        )

    from pathlib import Path

    import torch
    from diffusers import StableDiffusionXLInpaintPipeline
    from PIL import Image

    input_path = Path(params.get("input", ""))
    mask_path = Path(params.get("mask", ""))
    if not input_path.exists():
        raise ValueError(f"Input image not found: {input_path!r}")
    if not mask_path.exists():
        raise ValueError(f"Mask image not found: {mask_path!r}")

    prompt = params.get("prompt", "seamless game texture, high quality, 4k")
    negative_prompt = params.get(
        "negative_prompt",
        "blurry, low quality, seams, artifacts"
    )
    strength = float(params.get("strength", 0.99))
    steps = int(params.get("steps", 30))
    out_name = params.get("output") or f"{input_path.stem}_inpainted.png"
    out_path = Path(output_dir) / out_name

    progress_cb(0.05, "Loading SDXL inpainting pipeline…")
    hf_id = model_path or model_id or "diffusers/stable-diffusion-xl-1.0-inpainting-0.1"
    dtype = torch.float16 if device != "cpu" else torch.float32
    pipe = StableDiffusionXLInpaintPipeline.from_pretrained(
        hf_id,
        torch_dtype=dtype,
    ).to(device)

    progress_cb(0.3, "Loading images…")
    image = Image.open(str(input_path)).convert("RGB")
    mask = Image.open(str(mask_path)).convert("RGB")

    # Resize mask to match source
    if mask.size != image.size:
        mask = mask.resize(image.size, Image.NEAREST)

    progress_cb(0.4, "Running inpainting…")
    result = pipe(
        prompt=prompt,
        negative_prompt=negative_prompt,
        image=image,
        mask_image=mask,
        strength=strength,
        num_inference_steps=steps,
    ).images[0]

    progress_cb(0.95, "Saving…")
    result.save(str(out_path))
    progress_cb(1.0, "Done")

    w, h = result.size
    return {
        "files": [out_name],
        "metadata": {"width": w, "height": h, "steps": steps},
    }
