"""visual.texture.upscale — AI texture upscaling via Stable Diffusion x4 Upscaler.

Uses diffusers StableDiffusionUpscalePipeline with stabilityai/stable-diffusion-x4-upscaler.
basicsr/realesrgan are NOT used — they are broken with torchvision >= 0.16.

Params:
    input       (str):  path to input texture (PNG/JPG/WEBP)
    prompt      (str):  optional style hint (default: "high resolution, seamless game texture")
    output      (str):  output filename (default: <stem>_upscaled.png)
    steps       (int):  diffusion steps (default: 20; increase for higher quality)
"""
from __future__ import annotations

from pathlib import Path

import torch
from PIL import Image

MODEL_ID = "stabilityai/stable-diffusion-x4-upscaler"
# SD x4 upscaler works on small input patches; 128×128 → 512×512 at 12 GB VRAM budget.
# Larger inputs are tiled automatically by the pipeline but may OOM on small GPUs.
MAX_INPUT_PX = 128
DEFAULT_PROMPT = "high resolution, seamless game texture, 4K, detailed"

_pipe = None


def _load(model_id: str, device: str):
    global _pipe
    if _pipe is None:
        from diffusers import StableDiffusionUpscalePipeline

        _pipe = StableDiffusionUpscalePipeline.from_pretrained(
            model_id, torch_dtype=torch.float16 if device != "cpu" else torch.float32
        )
        _pipe.to(device)
    return _pipe


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Upscale a texture 4× using Stable Diffusion x4 Upscaler."""
    used_model = model_id or MODEL_ID

    raw_input = params.get("input") or ""
    input_path = Path(raw_input) if raw_input else Path("")
    if not raw_input or not input_path.is_file():
        raise ValueError(f"Input file not found: {input_path!r}")

    prompt = params.get("prompt") or DEFAULT_PROMPT
    steps = int(params.get("steps", 20))
    out_name = params.get("output") or f"{input_path.stem}_upscaled.png"
    out_path = Path(output_dir) / out_name

    progress_cb(0.1, "Loading SD x4 Upscaler…")
    pipe = _load(used_model, device)

    progress_cb(0.2, "Reading image…")
    image = Image.open(input_path).convert("RGB")

    # Cap input so the pipeline fits in a typical 12 GB GPU budget
    w, h = image.size
    if w > MAX_INPUT_PX or h > MAX_INPUT_PX:
        ratio = min(MAX_INPUT_PX / w, MAX_INPUT_PX / h)
        image = image.resize(
            (int(w * ratio), int(h * ratio)), Image.Resampling.LANCZOS
        )

    progress_cb(0.4, f"Upscaling {image.width}×{image.height} → {image.width * 4}×{image.height * 4}…")
    result = pipe(prompt=prompt, image=image, num_inference_steps=steps)
    out_img = result.images[0]

    progress_cb(0.9, "Saving…")
    out_img.save(str(out_path))
    progress_cb(1.0, "Done")

    return {
        "files": [out_name],
        "metadata": {
            "scale": 4,
            "input_width": image.width,
            "input_height": image.height,
            "output_width": out_img.width,
            "output_height": out_img.height,
            "model": used_model,
        },
    }
