"""assgen.animate.mocap — HuggingFace Space
Estimate human pose keypoints from images using Sapiens.
CLI equivalent: assgen gen visual animate mocap
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
def estimate_pose(image: Image.Image) -> tuple[str, str]:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        image.save(tmp.name)
        result = run(
            "visual.animate.mocap",
            {"input": tmp.name},
            device="cuda",
        )
    # Return annotated image and BVH/JSON output
    files = result["files"]
    img_files = [f for f in files if f.lower().endswith((".png", ".jpg"))]
    data_files = [f for f in files if not f.lower().endswith((".png", ".jpg"))]
    img_out = img_files[0] if img_files else files[0]
    data_out = data_files[0] if data_files else files[-1]
    return img_out, data_out


with gr.Blocks(title="assgen · Pose Estimation (MoCap)") as demo:
    gr.Markdown(
        "# assgen · Pose Estimation (MoCap)\n"
        "Estimate human pose keypoints from images for motion capture data. "
        "Powered by [facebook/sapiens-pose-0.3b](https://huggingface.co/facebook/sapiens-pose-0.3b). "
        "Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.\n\n"
        "_ZeroGPU — upload an image containing a person/character._"
    )
    with gr.Row():
        with gr.Column():
            image = gr.Image(label="Input Image (person or character)", type="pil")
            btn = gr.Button("Estimate Pose", variant="primary")
        with gr.Column():
            out_image = gr.Image(label="Pose Overlay", type="filepath")
            out_file = gr.File(label="Pose Data (BVH/JSON)")
    btn.click(fn=estimate_pose, inputs=image, outputs=[out_image, out_file])

demo.launch()
