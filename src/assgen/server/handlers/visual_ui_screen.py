"""visual.ui.screen — complete game screen composition via SDXL.

Generates high-resolution complete game screen images (HUD + gameplay +
UI chrome) from a text description.  Useful for visual prototyping and
concept art for game screens before implementation.

  pip install diffusers transformers accelerate torch Pillow

Params:
    prompt          (str):  screen description, e.g. "fantasy RPG combat HUD with health bars, minimap, and skill hotbar"
    screen_type     (str):  gameplay|mainmenu|pause|inventory|loading|cutscene (default: gameplay)
    negative_prompt (str):  negative prompt (optional)
    width           (int):  output width (default: 1920)
    height          (int):  output height (default: 1080)
    steps           (int):  inference steps (default: 35)
    guidance_scale  (float):CFG scale (default: 7.5)
    output          (str):  output filename (default: screen.png)
"""
from __future__ import annotations

try:
    from diffusers import StableDiffusionXLPipeline  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False

_SCREEN_HINTS = {
    "gameplay":  "game screen with HUD overlay, health bar, minimap, in-game UI",
    "mainmenu":  "main menu screen, title card, menu buttons, background art",
    "pause":     "pause screen, semi-transparent overlay, resume/quit options",
    "inventory": "inventory screen, item grid, equipment slots, stats panel",
    "loading":   "loading screen, progress bar, atmospheric background art",
    "cutscene":  "cutscene frame, cinematic letterbox, subtitle bar",
}


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Generate a complete game screen composition."""
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

    screen_type = (params.get("screen_type") or "gameplay").lower()
    negative_prompt = params.get("negative_prompt", "blurry, low quality, text artifacts, watermark")
    width = int(params.get("width", 1920))
    height = int(params.get("height", 1080))
    width = max(8, width - (width % 8))
    height = max(8, height - (height % 8))
    steps = int(params.get("steps", 35))
    guidance = float(params.get("guidance_scale", 7.5))
    out_name = params.get("output") or "screen.png"
    out_path = Path(output_dir) / out_name

    progress_cb(0.05, "Loading SDXL pipeline…")
    hf_id = model_path or model_id or "stabilityai/stable-diffusion-xl-base-1.0"
    dtype = torch.float16 if device != "cpu" else torch.float32
    pipe = StableDiffusionXLPipeline.from_pretrained(hf_id, torch_dtype=dtype).to(device)

    screen_hint = _SCREEN_HINTS.get(screen_type, _SCREEN_HINTS["gameplay"])
    full_prompt = (
        f"{prompt}, {screen_hint}, "
        "game UI design, digital art, high resolution, detailed"
    )

    progress_cb(0.2, f"Generating {screen_type} screen ({width}×{height})…")
    image = pipe(
        prompt=full_prompt,
        negative_prompt=negative_prompt,
        num_inference_steps=steps,
        guidance_scale=guidance,
        width=width,
        height=height,
    ).images[0]

    progress_cb(0.95, "Saving…")
    image.save(str(out_path))
    progress_cb(1.0, "Done")

    w, h = image.size
    return {
        "files": [out_name],
        "metadata": {"screen_type": screen_type, "width": w, "height": h},
    }
