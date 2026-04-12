"""assgen.texture.upscale — HuggingFace Space
4× AI texture upscaling using Stable Diffusion x4 Upscaler.
CLI equivalent: assgen gen visual texture upscale

Uses diffusers StableDiffusionUpscalePipeline — no basicsr/realesrgan required.
"""
from __future__ import annotations

try:
    import spaces
except (ImportError, AttributeError):
    import types
    spaces = types.SimpleNamespace(GPU=lambda fn: fn)

import gradio as gr
import torch
from diffusers import StableDiffusionUpscalePipeline
from PIL import Image

MODEL_ID = "stabilityai/stable-diffusion-x4-upscaler"
MAX_INPUT_PX = 128  # SD x4 upscaler works on small patches; 128×128 → 512×512

_pipe: StableDiffusionUpscalePipeline | None = None


def _load() -> StableDiffusionUpscalePipeline:
    global _pipe
    if _pipe is None:
        _pipe = StableDiffusionUpscalePipeline.from_pretrained(
            MODEL_ID, torch_dtype=torch.float16
        )
    return _pipe


@spaces.GPU
def upscale(image: Image.Image, prompt: str) -> tuple[Image.Image, str]:
    if image is None:
        raise gr.Error("Please upload a texture image to upscale.")

    pipe = _load()
    pipe.to("cuda" if torch.cuda.is_available() else "cpu")

    # Cap input to MAX_INPUT_PX × MAX_INPUT_PX; model always outputs 4× size
    w, h = image.size
    if w > MAX_INPUT_PX or h > MAX_INPUT_PX:
        ratio = min(MAX_INPUT_PX / w, MAX_INPUT_PX / h)
        image = image.resize((int(w * ratio), int(h * ratio)), Image.Resampling.LANCZOS)

    if prompt.strip() == "":
        prompt = "high resolution, seamless game texture, 4K, detailed"

    result = pipe(prompt=prompt, image=image, num_inference_steps=20)
    out_img = result.images[0]

    info = f"{image.width}×{image.height} → {out_img.width}×{out_img.height}"
    return out_img, info


with gr.Blocks(title="assgen · Texture Upscaler") as demo:
    gr.Markdown(
        "# 🔍 assgen · Texture Upscaler\n"
        "AI 4× texture upscaling using [Stable Diffusion x4 Upscaler]"
        "(https://huggingface.co/stabilityai/stable-diffusion-x4-upscaler). "
        "Input capped at 128×128 (output is 512×512). "
        "Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.\n\n"
        "_ZeroGPU — may queue briefly during high traffic._"
    )
    with gr.Row():
        with gr.Column():
            img_in = gr.Image(label="Input Texture (max 128×128)", type="pil")
            prompt_in = gr.Textbox(
                label="Style Hint (optional)",
                placeholder="seamless stone wall texture, rough, detailed",
                lines=2,
            )
            btn = gr.Button("Upscale 4×", variant="primary")
        with gr.Column():
            img_out = gr.Image(label="Upscaled Texture (512×512)")
            info = gr.Textbox(label="Dimensions", interactive=False)
    btn.click(fn=upscale, inputs=[img_in, prompt_in], outputs=[img_out, info])

demo.launch()
