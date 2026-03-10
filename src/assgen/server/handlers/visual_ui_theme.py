"""visual.ui.theme — coordinated UI theme kit via IP-Adapter + SDXL.

Generates a matched set of UI elements (icons, button, panel) derived from a
style reference image using IP-Adapter, ensuring visual cohesion across all
generated assets.

  pip install diffusers transformers accelerate torch Pillow

Params:
    prompt          (str):  theme description, e.g. "dark souls gothic stone medieval"
    style_image     (str):  path to reference image that defines the visual style
    elements        (list|str): which elements to generate:
                              icon|button|panel|widget (default: all four)
    ip_adapter_scale (float): style influence 0.0–1.0 (default: 0.65)
    steps           (int):  inference steps (default: 30)
    output          (str):  output filename stem (default: theme)
"""
from __future__ import annotations

try:
    from diffusers import StableDiffusionXLPipeline  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False

_ELEMENT_PROMPTS = {
    "icon":   ("game UI icon, isolated, flat icon, no background", 128, 128),
    "button": ("game button control, isolated, no background", 256, 96),
    "panel":  ("game UI panel frame dialog box, isolated, no background", 512, 256),
    "widget": ("game UI slider widget control, isolated, no background", 320, 80),
}


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Generate a coordinated UI theme kit using IP-Adapter style transfer."""
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
        raise ValueError("'style_image' reference is required for visual.ui.theme")

    raw_elements = params.get("elements") or list(_ELEMENT_PROMPTS.keys())
    if isinstance(raw_elements, str):
        raw_elements = [e.strip() for e in raw_elements.split(",") if e.strip()]
    elements = [e for e in raw_elements if e in _ELEMENT_PROMPTS]
    if not elements:
        elements = list(_ELEMENT_PROMPTS.keys())

    ip_scale = float(params.get("ip_adapter_scale", 0.65))
    steps = int(params.get("steps", 30))
    out_stem = params.get("output") or "theme"
    out_dir = Path(output_dir)

    progress_cb(0.05, "Loading SDXL pipeline…")
    hf_id = model_path or model_id or "stabilityai/stable-diffusion-xl-base-1.0"
    dtype = torch.float16 if device != "cpu" else torch.float32
    pipe = StableDiffusionXLPipeline.from_pretrained(hf_id, torch_dtype=dtype).to(device)

    progress_cb(0.1, "Loading IP-Adapter…")
    pipe.load_ip_adapter("h94/IP-Adapter", subfolder="sdxl_models", weight_name="ip-adapter_sdxl.bin")
    pipe.set_ip_adapter_scale(ip_scale)

    style_img = Image.open(style_image_path).convert("RGB")
    negative = "background scenery, text, watermark, clutter"
    out_files: list[str] = []

    for i, element in enumerate(elements):
        type_hint, w, h = _ELEMENT_PROMPTS[element]
        full_prompt = f"{prompt}, {type_hint}, PNG asset"
        progress_cb(0.15 + 0.75 * (i / len(elements)), f"Generating {element}…")
        image = pipe(
            prompt=full_prompt,
            negative_prompt=negative,
            ip_adapter_image=style_img,
            num_inference_steps=steps,
            width=w,
            height=h,
        ).images[0]
        out_name = f"{out_stem}_{element}.png"
        image.save(str(out_dir / out_name))
        out_files.append(out_name)

    progress_cb(1.0, "Done")
    return {
        "files": out_files,
        "metadata": {"elements": elements, "style_locked": True, "ip_adapter_scale": ip_scale},
    }
