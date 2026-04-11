"""visual.ui.panel — dialog boxes, frames, and panel chrome via SDXL.

Generates game UI panel assets: dialog boxes, inventory frames, tooltip
backgrounds, and decorative chrome elements.

  pip install diffusers transformers accelerate torch Pillow

Params:
    prompt          (str):  panel description, e.g. "gothic stone dialog box frame"
    style           (str):  visual style hint
    width           (int):  output width in px (default: 512)
    height          (int):  output height in px (default: 256)
    panel_type      (str):  dialog|inventory|tooltip|frame|border (default: dialog)
    transparent     (bool): attempt transparent background (default: true)
    steps           (int):  inference steps (default: 25)
    output          (str):  output filename (default: panel.png)
"""
from __future__ import annotations

try:
    from diffusers import StableDiffusionXLPipeline  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False

_PANEL_PROMPTS = {
    "dialog":    "dialog box panel, speech bubble frame, game UI",
    "inventory": "inventory grid panel, item container frame, game UI",
    "tooltip":   "tooltip popup, info panel, small rectangular frame, game UI",
    "frame":     "decorative border frame, ornate UI frame, game UI",
    "border":    "panel border, edge trim, UI chrome element, game UI",
}


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Generate a game UI panel / dialog box asset."""
    if not _AVAILABLE:
        raise RuntimeError(
            "diffusers is required. Run: pip install diffusers transformers accelerate torch"
        )

    from pathlib import Path

    import torch
    from diffusers import StableDiffusionXLPipeline

    prompt = params.get("prompt", "")
    if not prompt:
        raise ValueError("'prompt' is required")

    style = params.get("style", "")
    width = int(params.get("width", 512))
    height = int(params.get("height", 256))
    width = max(8, width - (width % 8))
    height = max(8, height - (height % 8))
    panel_type = (params.get("panel_type") or "dialog").lower()
    steps = int(params.get("steps", 25))
    out_name = params.get("output") or "panel.png"
    out_path = Path(output_dir) / out_name

    progress_cb(0.05, "Loading SDXL pipeline…")
    hf_id = model_path or model_id or "stabilityai/stable-diffusion-xl-base-1.0"
    dtype = torch.float16 if device != "cpu" else torch.float32
    pipe = StableDiffusionXLPipeline.from_pretrained(hf_id, torch_dtype=dtype).to(device)

    type_hint = _PANEL_PROMPTS.get(panel_type, _PANEL_PROMPTS["dialog"])
    style_tag = f", {style} style" if style else ""
    full_prompt = (
        f"{prompt}{style_tag}, {type_hint}, "
        "isolated on transparent background, clean edges, no background, PNG asset"
    )
    negative = "background scenery, characters, text, watermark"

    progress_cb(0.3, f"Generating {panel_type} panel…")
    image = pipe(
        prompt=full_prompt,
        negative_prompt=negative,
        num_inference_steps=steps,
        width=width,
        height=height,
    ).images[0]

    progress_cb(0.95, "Saving…")
    image.save(str(out_path))
    progress_cb(1.0, "Done")

    return {
        "files": [out_name],
        "metadata": {"panel_type": panel_type, "width": width, "height": height},
    }
