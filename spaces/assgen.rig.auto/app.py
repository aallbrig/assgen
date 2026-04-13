"""assgen.rig.auto — HuggingFace Space
Automatically rig a 3D mesh using UniRig.
CLI equivalent: assgen gen visual rig auto
"""
from __future__ import annotations

try:
    import spaces; spaces.GPU  # AttributeError if wrong package
except (ImportError, AttributeError):
    import types
    spaces = types.SimpleNamespace(GPU=lambda fn: fn)

import gradio as gr
from assgen.sdk import run

SKELETON_TYPES = ["biped", "quadruped", "hand", "wing", "spine"]


@spaces.GPU
def rig_mesh(mesh_file: str, skeleton: str) -> str:
    result = run(
        "visual.rig.auto",
        {"input": mesh_file, "skeleton": skeleton},
        device="cuda",
    )
    glb_files = [f for f in result["files"] if f.endswith(".glb")]
    return glb_files[0] if glb_files else result["files"][0]


with gr.Blocks(title="assgen · Auto Rigger") as demo:
    gr.Markdown(
        "# assgen · Auto Rigger\n"
        "Automatically rig a 3D mesh for animation using UniRig. "
        "Powered by [VAST-AI/UniRig](https://huggingface.co/VAST-AI/UniRig). "
        "Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.\n\n"
        "_ZeroGPU — input a GLB or OBJ mesh. Rigged GLB is returned for download. "
        "Note: UniRig is a research model; complex meshes may produce imperfect results._"
    )
    with gr.Row():
        with gr.Column():
            mesh_file = gr.File(label="Upload Mesh (GLB or OBJ)",
                                file_types=[".glb", ".obj"])
            skeleton = gr.Dropdown(label="Skeleton Type", choices=SKELETON_TYPES,
                                   value="biped")
            btn = gr.Button("Auto Rig", variant="primary")
        with gr.Column():
            model3d = gr.Model3D(label="Rigged Mesh Preview (GLB)")
    btn.click(fn=rig_mesh, inputs=[mesh_file, skeleton], outputs=model3d)

demo.launch()
