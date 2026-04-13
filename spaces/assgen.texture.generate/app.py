"""assgen.texture.generate — HuggingFace Space
Generate seamless tileable game textures from text using SDXL.
The handler applies texture-specific prompt guidance automatically.
CLI equivalent: assgen gen visual texture generate
"""
from __future__ import annotations

import random

try:
    import spaces; spaces.GPU  # AttributeError if wrong package
except (ImportError, AttributeError):
    import types
    spaces = types.SimpleNamespace(GPU=lambda fn: fn)

import gradio as gr
from assgen.sdk import run


@spaces.GPU
def generate_texture(description: str, steps: int, guidance: float, seed: int) -> str:
    actual_seed = seed if seed >= 0 else random.randint(0, 2**32 - 1)
    result = run(
        "visual.texture.generate",
        # Key is "steps" (not "num_inference_steps") — same pattern as concept.generate
        {"prompt": description, "steps": steps,
         "guidance_scale": guidance, "seed": actual_seed},
        device="cuda",
    )
    return result["files"][0]


EXAMPLES = [
    ["rough cracked stone wall", 30, 7.5, 42],
    ["worn oak wooden plank floor", 30, 7.5, 100],
    ["rusty corrugated metal sheet", 30, 7.5, 200],
    ["mossy cobblestone path", 30, 7.5, 300],
    ["smooth polished white marble with grey veins", 30, 7.5, 400],
    ["dark fantasy dungeon floor, wet stone", 30, 7.5, 500],
]

with gr.Blocks(title="assgen · Texture Generator") as demo:
    gr.Markdown(
        "# 🧱 assgen · Texture Generator\n"
        "Generate seamless tileable PBR albedo textures. "
        "Prompt is enhanced with texture guidance automatically. "
        "Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.\n\n"
        "_ZeroGPU — may queue briefly during high traffic._"
    )
    with gr.Row():
        with gr.Column():
            desc = gr.Textbox(label="Surface / Material Description",
                              placeholder="rough cracked stone wall", lines=2)
            with gr.Row():
                steps = gr.Slider(label="Steps", minimum=20, maximum=50, value=30, step=1)
                guidance = gr.Slider(label="Guidance", minimum=4.0, maximum=12.0,
                                     value=7.5, step=0.5)
            seed = gr.Number(label="Seed (-1 = random)", value=-1, precision=0)
            btn = gr.Button("Generate Texture", variant="primary")
        with gr.Column():
            image = gr.Image(label="Generated Texture (1024×1024)", type="filepath")
            gr.Markdown("_Tip: pipe output into assgen.texture.upscale for 4× resolution._")
    gr.Examples(EXAMPLES, inputs=[desc, steps, guidance, seed], cache_examples=False)
    btn.click(fn=generate_texture, inputs=[desc, steps, guidance, seed], outputs=image)

demo.launch()
