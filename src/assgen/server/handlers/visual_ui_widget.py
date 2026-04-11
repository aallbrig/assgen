"""visual.ui.widget — individual UI control generation via SDXL.

Generates standalone game UI controls: sliders, toggles, checkboxes,
progress bars, spinners, radio buttons, and similar interactive elements.

  pip install diffusers transformers accelerate torch Pillow

Params:
    prompt          (str):  control description, e.g. "fantasy scroll health bar"
    widget_type     (str):  slider|toggle|checkbox|progressbar|spinner|radio|knob (default: slider)
    style           (str):  visual style
    width           (int):  output width in px (default: 320)
    height          (int):  output height in px (default: 64)
    steps           (int):  inference steps (default: 25)
    output          (str):  output filename (default: widget.png)
"""
from __future__ import annotations

try:
    from diffusers import StableDiffusionXLPipeline  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False

_WIDGET_HINTS = {
    "slider":      "horizontal slider control, track and thumb, game UI widget",
    "toggle":      "toggle switch, on/off button, game UI widget",
    "checkbox":    "checkbox control, tick mark, game UI widget",
    "progressbar": "progress bar, filled bar, game UI widget",
    "spinner":     "loading spinner, circular progress, game UI widget",
    "radio":       "radio button, selection circle, game UI widget",
    "knob":        "rotary knob, dial control, game UI widget",
}


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Generate a styled game UI control widget."""
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

    widget_type = (params.get("widget_type") or "slider").lower()
    style = params.get("style", "")
    width = int(params.get("width", 320))
    height = int(params.get("height", 64))
    width = max(8, width - (width % 8))
    height = max(8, height - (height % 8))
    steps = int(params.get("steps", 25))
    out_name = params.get("output") or "widget.png"
    out_path = Path(output_dir) / out_name

    progress_cb(0.05, "Loading SDXL pipeline…")
    hf_id = model_path or model_id or "stabilityai/stable-diffusion-xl-base-1.0"
    dtype = torch.float16 if device != "cpu" else torch.float32
    pipe = StableDiffusionXLPipeline.from_pretrained(hf_id, torch_dtype=dtype).to(device)

    type_hint = _WIDGET_HINTS.get(widget_type, _WIDGET_HINTS["slider"])
    style_tag = f", {style} style" if style else ""
    full_prompt = (
        f"{prompt}{style_tag}, {type_hint}, "
        "isolated on transparent background, clean edges, no background, PNG asset"
    )
    negative = "background, text, watermark, clutter"

    progress_cb(0.3, f"Generating {widget_type} widget…")
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
        "metadata": {"widget_type": widget_type, "width": width, "height": height},
    }
