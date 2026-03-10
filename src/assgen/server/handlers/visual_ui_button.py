"""visual.ui.button — styled game button / control generation via SDXL.

Generates isolated PNG button/control assets with transparent backgrounds,
optionally in multiple states (normal, hover, pressed, disabled).

  pip install diffusers transformers accelerate torch Pillow

Params:
    prompt          (str):  button description, e.g. "medieval stone button START"
    style           (str):  visual style hint, e.g. "flat", "pixel-art", "3d-embossed"
    width           (int):  output width in px (default: 256)
    height          (int):  output height in px (default: 128)
    states          (list): which states to generate: normal|hover|pressed|disabled (default: [normal])
    steps           (int):  inference steps (default: 25)
    output          (str):  output filename stem (default: button)
"""
from __future__ import annotations

try:
    from diffusers import StableDiffusionXLPipeline  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False

_STATE_MODIFIERS = {
    "normal":   "",
    "hover":    ", glowing highlight, lighter tone",
    "pressed":  ", darker, depressed inset, shadow inward",
    "disabled": ", greyscale, desaturated, low contrast",
}


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Generate styled game button assets with optional state variants."""
    if not _AVAILABLE:
        raise RuntimeError(
            "diffusers is required. Run: pip install diffusers transformers accelerate torch"
        )

    import torch
    from pathlib import Path
    from diffusers import StableDiffusionXLPipeline

    prompt = params.get("prompt", "")
    if not prompt:
        raise ValueError("'prompt' is required")

    style = params.get("style", "")
    width = int(params.get("width", 256))
    height = int(params.get("height", 128))
    # Round to multiples of 8
    width = max(8, width - (width % 8))
    height = max(8, height - (height % 8))
    raw_states = params.get("states") or ["normal"]
    if isinstance(raw_states, str):
        raw_states = [s.strip() for s in raw_states.split(",")]
    steps = int(params.get("steps", 25))
    out_stem = params.get("output") or "button"
    out_dir = Path(output_dir)

    progress_cb(0.05, "Loading SDXL pipeline…")
    hf_id = model_path or model_id or "stabilityai/stable-diffusion-xl-base-1.0"
    dtype = torch.float16 if device != "cpu" else torch.float32
    pipe = StableDiffusionXLPipeline.from_pretrained(hf_id, torch_dtype=dtype).to(device)

    style_tag = f", {style} style" if style else ""
    base_prompt = (
        f"{prompt}{style_tag}, game UI button, isolated on transparent background, "
        "clean edges, no background, PNG asset"
    )
    negative = "background, clutter, text, watermark, frame"

    out_files: list[str] = []
    n = len(raw_states)
    for i, state in enumerate(raw_states):
        modifier = _STATE_MODIFIERS.get(state, "")
        full_prompt = base_prompt + modifier
        progress_cb(0.1 + 0.8 * (i / n), f"Generating {state} state…")
        image = pipe(
            prompt=full_prompt,
            negative_prompt=negative,
            num_inference_steps=steps,
            width=width,
            height=height,
        ).images[0]
        out_name = f"{out_stem}_{state}.png" if len(raw_states) > 1 else f"{out_stem}.png"
        image.save(str(out_dir / out_name))
        out_files.append(out_name)

    progress_cb(1.0, "Done")
    return {
        "files": out_files,
        "metadata": {"width": width, "height": height, "states": raw_states},
    }
