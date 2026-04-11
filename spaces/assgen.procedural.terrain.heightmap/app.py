"""assgen.procedural.terrain.heightmap — HuggingFace Space
Procedural terrain heightmap generation — CPU only, instant.
CLI equivalent: assgen gen procedural terrain heightmap
"""
from __future__ import annotations

import gradio as gr
from assgen.sdk import run   # no @spaces.GPU — CPU-only Space


def generate_heightmap(width: int, height: int, scale: float,
                       octaves: int, seed: int, colormap: str) -> tuple[str, str]:
    result = run(
        "procedural.terrain.heightmap",
        {"width": width, "height": height, "scale": scale,
         "octaves": octaves, "seed": seed, "colormap": colormap.lower()},
        device="cpu",
    )
    out_path = result["files"][0]
    info = (f"Size: {width}×{height} | Scale: {scale} | "
            f"Octaves: {octaves} | Seed: {seed}")
    return out_path, info


with gr.Blocks(title="assgen · Terrain Heightmap Generator") as demo:
    gr.Markdown(
        "# 🏔️ assgen · Terrain Heightmap Generator\n"
        "Procedural terrain heightmaps using fractal Perlin noise. "
        "CPU only — results are instant. "
        "Export the PNG as a heightmap in Unity/Godot/Unreal.\n"
        "Part of the [assgen](https://github.com/aallbrig/assgen) pipeline."
    )
    with gr.Row():
        with gr.Column():
            with gr.Row():
                w = gr.Slider(label="Width", minimum=64, maximum=1024, value=512, step=64)
                h = gr.Slider(label="Height", minimum=64, maximum=1024, value=512, step=64)
            scale = gr.Slider(label="Scale (zoom — larger = broader features)",
                              minimum=50.0, maximum=500.0, value=200.0, step=10.0)
            octaves = gr.Slider(label="Octaves (detail layers)",
                                minimum=1, maximum=8, value=6, step=1)
            seed = gr.Number(label="Seed", value=42, precision=0)
            colormap = gr.Radio(label="Colormap",
                                choices=["Grayscale", "Terrain", "Earth", "Brown"],
                                value="Terrain")
            btn = gr.Button("Generate Heightmap", variant="primary")
        with gr.Column():
            img_out = gr.Image(label="Heightmap", type="filepath")
            info = gr.Textbox(label="Info", interactive=False)
    gr.Examples(
        [[512, 512, 200.0, 6, 42, "Terrain"],
         [512, 512, 100.0, 8, 1337, "Earth"],
         [1024, 512, 250.0, 5, 777, "Brown"]],
        inputs=[w, h, scale, octaves, seed, colormap], cache_examples=False,
    )
    btn.click(fn=generate_heightmap, inputs=[w, h, scale, octaves, seed, colormap],
              outputs=[img_out, info])

demo.launch()
