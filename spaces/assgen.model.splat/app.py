"""assgen.model.splat — HuggingFace Space
Convert a set of multi-view images to a 3D mesh using TripoSR.
CLI equivalent: assgen gen visual model splat
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
def generate_splat(image: Image.Image, target_faces: int) -> str:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        image.save(tmp.name)
        result = run(
            "visual.model.splat",
            {"images": [tmp.name], "target_faces": target_faces},
            device="cuda",
        )
    # Return the first GLB file
    glb_files = [f for f in result["files"] if f.endswith(".glb")]
    return glb_files[0] if glb_files else result["files"][0]


with gr.Blocks(title="assgen · Image-to-3D (TripoSR)") as demo:
    gr.Markdown(
        "# assgen · Image-to-3D (TripoSR)\n"
        "Convert a single foreground image to a 3D mesh using TripoSR. "
        "Powered by [stabilityai/TripoSR](https://huggingface.co/stabilityai/TripoSR). "
        "Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.\n\n"
        "_ZeroGPU — use an image with a clear foreground object for best results._"
    )
    with gr.Row():
        with gr.Column():
            image = gr.Image(label="Input Image (foreground object, white bg preferred)",
                             type="pil")
            target_faces = gr.Slider(label="Target Face Count",
                                     minimum=1000, maximum=50000, value=10000, step=1000)
            btn = gr.Button("Generate 3D Mesh", variant="primary")
        with gr.Column():
            model3d = gr.Model3D(label="Generated 3D Mesh (GLB)")
    btn.click(fn=generate_splat, inputs=[image, target_faces], outputs=model3d)

demo.launch()
