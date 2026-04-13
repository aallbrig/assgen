"""assgen.scene.lighting.hdri — HuggingFace Space
Generate 360° panoramic HDRI-reference images from text using LDM3D-pano.
CLI equivalent: assgen gen scene lighting hdri
"""
from __future__ import annotations

try:
    import spaces; spaces.GPU  # AttributeError if wrong package
except (ImportError, AttributeError):
    import types
    spaces = types.SimpleNamespace(GPU=lambda fn: fn)

import gradio as gr
from assgen.sdk import run


@spaces.GPU
def generate_hdri(prompt: str, steps: int) -> str:
    result = run(
        "scene.lighting.hdri",
        {"prompt": prompt, "steps": steps, "width": 1024, "height": 512},
        device="cuda",
    )
    # Return first PNG (RGB panorama)
    img_files = [f for f in result["files"] if f.lower().endswith((".png", ".jpg"))]
    return img_files[0] if img_files else result["files"][0]


EXAMPLES = [
    ["sunset over desert dunes, warm golden light, clear sky", 50],
    ["overcast forest clearing, soft diffuse light, morning mist", 50],
    ["dramatic thunderstorm, dark clouds, lightning on horizon", 50],
    ["bright sunny beach, tropical, blue sky, ocean horizon", 50],
    ["volcanic landscape, molten lava glow, smoke and ash", 50],
]

with gr.Blocks(title="assgen · HDRI Panorama Generator") as demo:
    gr.Markdown(
        "# assgen · HDRI Panorama Generator\n"
        "Generate 360° equirectangular panoramas for game scene lighting reference. "
        "Powered by [Intel/ldm3d-pano](https://huggingface.co/Intel/ldm3d-pano). "
        "Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.\n\n"
        "_ZeroGPU — outputs 1024×512 equirectangular PNG (LDR reference for HDRI setup)._"
    )
    with gr.Row():
        with gr.Column():
            prompt = gr.Textbox(label="Scene Description", lines=3,
                                placeholder="sunset over desert dunes, warm golden light")
            steps = gr.Slider(label="Steps", minimum=20, maximum=80, value=50, step=10)
            btn = gr.Button("Generate Panorama", variant="primary")
        with gr.Column():
            output = gr.Image(label="360° Panorama (1024×512 equirectangular)", type="filepath")
    gr.Examples(EXAMPLES, inputs=[prompt, steps], cache_examples=False)
    btn.click(fn=generate_hdri, inputs=[prompt, steps], outputs=output)

demo.launch()
