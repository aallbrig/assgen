"""assgen.concept.style — HuggingFace Space
Apply a style reference image to concept art generation using IP-Adapter + SDXL.
CLI equivalent: assgen gen visual concept style
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
def apply_style(style_image: Image.Image, prompt: str,
                style_strength: float, steps: int) -> str:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        style_image.save(tmp.name)
        result = run(
            "visual.concept.style",
            {
                "style_image": tmp.name,
                "prompt": prompt,
                "scale": style_strength,
                "steps": steps,
            },
            device="cuda",
        )
    return result["files"][0]


EXAMPLES = [
    [None, "forest environment with glowing mushrooms, game art", 0.6, 30],
    [None, "ancient stone temple, dramatic lighting, concept art", 0.7, 30],
]

with gr.Blocks(title="assgen · Style Transfer (Concept Art)") as demo:
    gr.Markdown(
        "# assgen · Style Transfer (Concept Art)\n"
        "Generate game concept art in the style of a reference image using IP-Adapter + SDXL. "
        "Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.\n\n"
        "_ZeroGPU — upload a style reference (painting, sketch, or photo) and describe your content._"
    )
    with gr.Row():
        with gr.Column():
            style_image = gr.Image(label="Style Reference Image", type="pil")
            prompt = gr.Textbox(label="Content Description", lines=3,
                                placeholder="forest environment with glowing mushrooms, game art")
            with gr.Row():
                style_strength = gr.Slider(label="Style Strength",
                                           minimum=0.0, maximum=1.0, value=0.6, step=0.05)
                steps = gr.Slider(label="Steps", minimum=20, maximum=40, value=30, step=5)
            btn = gr.Button("Generate Styled Art", variant="primary")
        with gr.Column():
            output = gr.Image(label="Styled Concept Art (1024×1024)", type="filepath")
    btn.click(fn=apply_style, inputs=[style_image, prompt, style_strength, steps], outputs=output)

demo.launch()
