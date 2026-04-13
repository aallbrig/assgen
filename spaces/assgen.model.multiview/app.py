"""assgen.model.multiview — HuggingFace Space
Generate 6 surrounding views of a 3D object from a single image using Zero123++.
CLI equivalent: assgen gen visual model multiview
"""
from __future__ import annotations

import tempfile

try:
    import spaces; spaces.GPU  # AttributeError if wrong package
except (ImportError, AttributeError):
    import types
    spaces = types.SimpleNamespace(GPU=lambda fn: fn)

import gradio as gr
from PIL import Image

from assgen.sdk import run


@spaces.GPU
def generate_multiview(image: Image.Image) -> list:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        image.save(tmp.name)
        result = run(
            "visual.model.multiview",
            {"image": tmp.name},
            device="cuda",
        )
    return result["files"]


with gr.Blocks(title="assgen · Multi-View Generator") as demo:
    gr.Markdown(
        "# assgen · Multi-View Generator\n"
        "Generate 6 surrounding views of a 3D object from a single image. "
        "Powered by [Zero123++](https://huggingface.co/sudo-ai/zero123plus). "
        "Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.\n\n"
        "_ZeroGPU — best results with objects on a white/transparent background._"
    )
    with gr.Row():
        with gr.Column():
            image = gr.Image(label="Input Object Image (square, white bg preferred)",
                             type="pil")
            btn = gr.Button("Generate Views", variant="primary")
        with gr.Column():
            gallery = gr.Gallery(label="6 Surrounding Views", columns=3, rows=2)
    btn.click(fn=generate_multiview, inputs=image, outputs=gallery)

demo.launch()
