"""visual.ui.mockup — full-screen UI mockup generation via ControlNet Canny + SDXL.

Generates complete game screen mockups (main menu, pause, inventory layout) guided
by a canny-edge reference sketch.  Falls back to plain SDXL text-to-image when no
reference is provided.

  pip install diffusers transformers accelerate torch Pillow controlnet-aux

Params:
    prompt          (str):  screen description, e.g. "fantasy RPG main menu, dark castle background"
    reference       (str):  optional path to a sketch/wireframe reference image
    negative_prompt (str):  negative prompt (optional)
    width           (int):  output width (default: 1280)
    height          (int):  output height (default: 720)
    steps           (int):  inference steps (default: 30)
    controlnet_scale (float): ControlNet conditioning strength (default: 0.8)
    output          (str):  output filename (default: mockup.png)
"""
from __future__ import annotations

try:
    from diffusers import StableDiffusionXLPipeline  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False

try:
    from diffusers import StableDiffusionXLControlNetPipeline, ControlNetModel  # noqa: F401
    _CONTROLNET_AVAILABLE = True
except ImportError:
    _CONTROLNET_AVAILABLE = False


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Generate a full-screen UI mockup, optionally guided by a sketch reference."""
    if not _AVAILABLE:
        raise RuntimeError(
            "diffusers is required. Run: pip install diffusers transformers accelerate torch"
        )

    from pathlib import Path

    prompt = params.get("prompt", "")
    if not prompt:
        raise ValueError("'prompt' is required")

    reference_path = params.get("reference", "")
    negative_prompt = params.get("negative_prompt", "blurry, low quality, artifacts")
    width = int(params.get("width", 1280))
    height = int(params.get("height", 720))
    width = max(8, width - (width % 8))
    height = max(8, height - (height % 8))
    steps = int(params.get("steps", 30))
    cn_scale = float(params.get("controlnet_scale", 0.8))
    out_name = params.get("output") or "mockup.png"
    out_path = Path(output_dir) / out_name

    has_reference = bool(reference_path) and Path(reference_path).exists()

    if has_reference and _CONTROLNET_AVAILABLE:
        image = _generate_with_controlnet(
            prompt, reference_path, negative_prompt,
            width, height, steps, cn_scale, device, model_path, model_id, progress_cb
        )
    else:
        if has_reference and not _CONTROLNET_AVAILABLE:
            progress_cb(0.1, "controlnet-aux not available, falling back to SDXL text-to-image…")
        image = _generate_sdxl(
            prompt, negative_prompt, width, height, steps, device, model_path, model_id, progress_cb
        )

    progress_cb(0.95, "Saving mockup…")
    image.save(str(out_path))
    progress_cb(1.0, "Done")

    w, h = image.size
    return {
        "files": [out_name],
        "metadata": {
            "width": w, "height": h,
            "method": "controlnet" if (has_reference and _CONTROLNET_AVAILABLE) else "sdxl",
        },
    }


def _generate_sdxl(prompt, negative_prompt, width, height, steps, device, model_path, model_id, progress_cb):
    import torch
    from diffusers import StableDiffusionXLPipeline
    hf_id = model_path or model_id or "stabilityai/stable-diffusion-xl-base-1.0"
    dtype = torch.float16 if device != "cpu" else torch.float32
    progress_cb(0.1, "Loading SDXL pipeline…")
    pipe = StableDiffusionXLPipeline.from_pretrained(hf_id, torch_dtype=dtype).to(device)
    full_prompt = f"{prompt}, game UI screen mockup, digital art, clean UI design"
    progress_cb(0.3, "Generating mockup…")
    return pipe(
        prompt=full_prompt,
        negative_prompt=negative_prompt,
        num_inference_steps=steps,
        width=width,
        height=height,
    ).images[0]


def _generate_with_controlnet(prompt, reference_path, negative_prompt, width, height, steps, cn_scale, device, model_path, model_id, progress_cb):
    import torch
    from PIL import Image
    from diffusers import StableDiffusionXLControlNetPipeline, ControlNetModel
    try:
        from controlnet_aux import CannyDetector
        canny = CannyDetector()
    except ImportError:
        import numpy as np
        import cv2

        class _SimpleCanny:
            def __call__(self, img):
                arr = np.array(img.convert("RGB"))
                edges = cv2.Canny(arr, 100, 200)
                return Image.fromarray(edges)
        canny = _SimpleCanny()

    progress_cb(0.05, "Loading ControlNet Canny…")
    cn_id = "diffusers/controlnet-canny-sdxl-1.0"
    dtype = torch.float16 if device != "cpu" else torch.float32
    controlnet = ControlNetModel.from_pretrained(cn_id, torch_dtype=dtype)
    base_id = model_path or model_id or "stabilityai/stable-diffusion-xl-base-1.0"
    progress_cb(0.15, "Loading SDXL + ControlNet pipeline…")
    pipe = StableDiffusionXLControlNetPipeline.from_pretrained(
        base_id, controlnet=controlnet, torch_dtype=dtype
    ).to(device)

    progress_cb(0.25, "Extracting canny edges from reference…")
    ref_img = Image.open(reference_path).convert("RGB").resize((width, height))
    control_image = canny(ref_img)

    full_prompt = f"{prompt}, game UI screen mockup, digital art, clean UI design"
    progress_cb(0.35, "Generating mockup with ControlNet guidance…")
    return pipe(
        prompt=full_prompt,
        negative_prompt=negative_prompt,
        image=control_image,
        num_inference_steps=steps,
        controlnet_conditioning_scale=cn_scale,
        width=width,
        height=height,
    ).images[0]
