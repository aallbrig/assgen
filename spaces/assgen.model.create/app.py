"""assgen.model.create — HuggingFace Space
Generate 3D game asset meshes from reference images using Hunyuan3D-2.
CLI equivalent: assgen gen visual model create
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
def generate_model(image: Image.Image, prompt: str) -> tuple[str, str]:
    if image is None and not (prompt or "").strip():
        raise gr.Error("Provide a reference image or a text prompt.")

    params: dict = {}
    if image is not None:
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        image.convert("RGBA").resize((512, 512)).save(tmp.name)
        # Key is "image" (not "image_path") — see handler contract
        params["image"] = tmp.name
    if prompt and prompt.strip():
        params["prompt"] = prompt.strip()

    result = run("visual.model.create", params, device="cuda")

    glb_path = result["files"][0]
    meta = result.get("metadata", {})
    info = (f"Vertices: {meta.get('vertices', '?'):,}  "
            f"Faces: {meta.get('faces', '?'):,}")
    return glb_path, info


with gr.Blocks(title="assgen · 3D Model Generator") as demo:
    gr.Markdown(
        "# 🗿 assgen · 3D Model Generator\n"
        "Generate 3D game asset `.glb` meshes from a reference image using Hunyuan3D-2.\n"
        "Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.\n\n"
        "⚠️ _Cold start: first request takes 2–3 min while the model loads (~14 GB)._\n"
        "_ZeroGPU — may queue briefly during high traffic._"
    )
    with gr.Row():
        with gr.Column():
            img = gr.Image(label="Reference Image (optional)", type="pil")
            prompt = gr.Textbox(label="Text Prompt (optional)",
                                placeholder="low-poly medieval sword", lines=2)
            btn = gr.Button("Generate 3D Model", variant="primary")
        with gr.Column():
            model_out = gr.Model3D(label="Generated 3D Model (.glb)",
                                   clear_color=[0.1, 0.1, 0.1, 1.0])
            info = gr.Textbox(label="Mesh Info", interactive=False)
    btn.click(fn=generate_model, inputs=[img, prompt], outputs=[model_out, info])

demo.launch()
