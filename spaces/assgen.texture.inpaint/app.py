"""assgen.texture.inpaint — HuggingFace Space
Fill masked regions of a texture using SDXL Inpainting.
CLI equivalent: assgen gen visual texture inpaint
"""
from __future__ import annotations

import tempfile

try:
    import spaces
except (ImportError, AttributeError):
    import types
    spaces = types.SimpleNamespace(GPU=lambda fn: fn)

import gradio as gr
from PIL import Image

from assgen.sdk import run


@spaces.GPU
def inpaint_texture(texture: Image.Image, mask: Image.Image,
                    prompt: str, steps: int) -> str:
    with (tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tex_tmp,
          tempfile.NamedTemporaryFile(suffix=".png", delete=False) as mask_tmp):
        texture.save(tex_tmp.name)
        mask.save(mask_tmp.name)
        result = run(
            "visual.texture.inpaint",
            {"input": tex_tmp.name, "mask": mask_tmp.name,
             "prompt": prompt, "steps": steps},
            device="cuda",
        )
    return result["files"][0]


with gr.Blocks(title="assgen · Texture Inpainting") as demo:
    gr.Markdown(
        "# assgen · Texture Inpainting\n"
        "Fill masked regions of a texture with AI-generated content using SDXL Inpainting. "
        "Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.\n\n"
        "_ZeroGPU — upload the texture and a white-on-black mask (white = inpaint region)._"
    )
    with gr.Row():
        with gr.Column():
            texture = gr.Image(label="Original Texture", type="pil")
            mask = gr.Image(label="Mask (white = fill area, black = keep)",
                            type="pil")
            prompt = gr.Textbox(label="Fill Description",
                                placeholder="seamless stone texture, uniform lighting",
                                lines=2)
            steps = gr.Slider(label="Steps", minimum=20, maximum=40, value=30, step=5)
            btn = gr.Button("Inpaint Texture", variant="primary")
        with gr.Column():
            output = gr.Image(label="Inpainted Texture", type="filepath")
    btn.click(fn=inpaint_texture, inputs=[texture, mask, prompt, steps], outputs=output)

demo.launch()
