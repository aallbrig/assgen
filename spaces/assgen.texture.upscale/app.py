"""assgen.texture.upscale — HuggingFace Space
4× AI texture upscaling using Real-ESRGAN.
CLI equivalent: assgen gen visual texture upscale
"""
from __future__ import annotations

try:
    import spaces
except (ImportError, AttributeError):
    import types
    spaces = types.SimpleNamespace(GPU=lambda fn: fn)

import gradio as gr
from PIL import Image
from assgen.sdk import run


@spaces.GPU
def upscale(image: Image.Image, scale: str) -> tuple[str, str]:
    if image is None:
        raise gr.Error("Please upload an image to upscale.")

    # Cap to 512×512 to avoid ZeroGPU timeout
    w, h = image.size
    if w > 512 or h > 512:
        ratio = min(512 / w, 512 / h)
        image = image.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

    import tempfile
    import os
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    image.save(tmp.name)

    result = run(
        "visual.texture.upscale",
        # Key is "input" (not "input_path") — see handler contract
        {"input": tmp.name, "scale": int(scale.replace("×", ""))},
        device="cuda",
    )
    os.unlink(tmp.name)
    out_path = result["files"][0]
    out_img = Image.open(out_path)
    info = f"Input: {image.width}×{image.height} → Output: {out_img.width}×{out_img.height}"
    return out_path, info


with gr.Blocks(title="assgen · Texture Upscaler") as demo:
    gr.Markdown(
        "# 🔍 assgen · Texture Upscaler\n"
        "4× AI texture upscaling using Real-ESRGAN. "
        "Input capped at 512×512 for ZeroGPU. "
        "Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.\n\n"
        "_ZeroGPU — may queue briefly during high traffic._"
    )
    with gr.Row():
        with gr.Column():
            img_in = gr.Image(label="Input Texture", type="pil")
            scale = gr.Radio(label="Scale", choices=["2×", "4×"], value="4×")
            btn = gr.Button("Upscale", variant="primary")
        with gr.Column():
            img_out = gr.Image(label="Upscaled Texture", type="filepath")
            info = gr.Textbox(label="Dimensions", interactive=False)
    btn.click(fn=upscale, inputs=[img_in, scale], outputs=[img_out, info])

demo.launch()
