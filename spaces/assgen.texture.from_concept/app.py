"""assgen.texture.from_concept — HuggingFace Space
Generate tileable textures guided by concept art using IP-Adapter + SDXL.
CLI equivalent: assgen gen visual texture from-concept
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
def texture_from_concept(concept: Image.Image, description: str,
                          style_strength: float, steps: int) -> str:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        concept.save(tmp.name)
        result = run(
            "visual.texture.from_concept",
            {
                "concept_image": tmp.name,
                "prompt": description,
                "ip_adapter_scale": style_strength,
                "steps": steps,
            },
            device="cuda",
        )
    return result["files"][0]


EXAMPLES = [
    [None, "rough stone wall, seamless, uniform lighting", 0.6, 30],
    [None, "weathered wood planks, tileable texture", 0.6, 30],
    [None, "dark metal armor plating, game texture", 0.7, 30],
]

with gr.Blocks(title="assgen · Texture from Concept Art") as demo:
    gr.Markdown(
        "# assgen · Texture from Concept Art\n"
        "Generate tileable PBR-ready textures guided by a concept art style reference. "
        "Uses IP-Adapter + SDXL with automatic texture prompt engineering. "
        "Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.\n\n"
        "_ZeroGPU — upload concept art and describe the surface/material._"
    )
    with gr.Row():
        with gr.Column():
            concept = gr.Image(label="Concept Art Reference", type="pil")
            description = gr.Textbox(label="Surface Description",
                                     placeholder="rough stone wall, seamless, uniform lighting",
                                     lines=2)
            with gr.Row():
                style_strength = gr.Slider(label="Style Strength",
                                           minimum=0.0, maximum=1.0, value=0.6, step=0.05)
                steps = gr.Slider(label="Steps", minimum=20, maximum=40, value=30, step=5)
            btn = gr.Button("Generate Texture", variant="primary")
        with gr.Column():
            output = gr.Image(label="Generated Texture (1024×1024)", type="filepath")
    gr.Examples(EXAMPLES, inputs=[concept, description, style_strength, steps],
                cache_examples=False)
    btn.click(fn=texture_from_concept,
              inputs=[concept, description, style_strength, steps], outputs=output)

demo.launch()
