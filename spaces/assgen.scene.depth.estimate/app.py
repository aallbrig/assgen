"""assgen.scene.depth.estimate — HuggingFace Space
Monocular depth estimation using Intel DPT-Large.
CLI equivalent: assgen gen scene depth estimate
"""
from __future__ import annotations

import os
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
def estimate_depth(image: Image.Image) -> tuple[str, str]:
    if image is None:
        raise gr.Error("Please upload an image.")
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    image.save(tmp.name)
    result = run(
        "scene.depth.estimate",
        # "input" key (not "input_path"); "colormap" is a boolean string flag,
        # not a colormap name — "true" requests the false-colour overlay.
        {"input": tmp.name, "colormap": "true"},
        device="cuda",
    )
    os.unlink(tmp.name)
    out_path = result["files"][0]
    meta = result.get("metadata", {})
    depth_min = meta.get("depth_min", "?")
    depth_max = meta.get("depth_max", "?")
    if isinstance(depth_min, float):
        info = f"Input: {image.width}×{image.height} | Depth range: {depth_min:.3f} – {depth_max:.3f}"
    else:
        info = f"Input: {image.width}×{image.height}"
    return out_path, info


with gr.Blocks(title="assgen · Depth Estimator") as demo:
    gr.Markdown(
        "# 📐 assgen · Depth Estimator\n"
        "Depth maps from game scene images using Intel DPT-Large. "
        "Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.\n\n"
        "_ZeroGPU — may queue briefly during high traffic._"
    )
    with gr.Row():
        with gr.Column():
            img = gr.Image(label="Input Image", type="pil")
            # No colormap dropdown — the handler uses a fixed internal colormap.
            btn = gr.Button("Estimate Depth", variant="primary")
        with gr.Column():
            depth = gr.Image(label="Depth Map", type="filepath")
            info = gr.Textbox(label="Info", interactive=False)
    btn.click(fn=estimate_depth, inputs=[img], outputs=[depth, info])

demo.launch()
