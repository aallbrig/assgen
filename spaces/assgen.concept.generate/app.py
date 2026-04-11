"""assgen.concept.generate — HuggingFace Space
Generate game concept art from text using SDXL.
CLI equivalent: assgen gen visual concept generate
"""
from __future__ import annotations

import random

try:
    import spaces
except (ImportError, AttributeError):
    import types
    spaces = types.SimpleNamespace(GPU=lambda fn: fn)

import gradio as gr
from assgen.sdk import run


@spaces.GPU
def generate_concept(prompt: str, negative: str, steps: int,
                     guidance: float, seed: int) -> str:
    actual_seed = seed if seed >= 0 else random.randint(0, 2**32 - 1)
    result = run(
        "visual.concept.generate",
        # Key is "steps" (not "num_inference_steps") — see handler contract
        {"prompt": prompt, "negative_prompt": negative,
         "steps": steps, "guidance_scale": guidance,
         "seed": actual_seed},
        device="cuda",
    )
    return result["files"][0]


EXAMPLES = [
    ["dark fantasy warrior in ornate plate armor, dramatic rim lighting, concept art",
     "blurry, low quality, watermark", 30, 7.5, 42],
    ["magical glowing forest environment, game concept art", "", 30, 7.5, 123],
    ["sci-fi plasma rifle, sleek hard surface design, concept art", "blurry, watermark", 30, 7.5, 456],
    ["fierce dragon perched on a mountain, fantasy boss design", "", 30, 7.5, 789],
]

with gr.Blocks(title="assgen · Concept Art Generator") as demo:
    gr.Markdown(
        "# 🎨 assgen · Concept Art Generator\n"
        "Generate game concept art from text using SDXL. "
        "Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.\n\n"
        "_ZeroGPU — may queue briefly during high traffic._"
    )
    with gr.Row():
        with gr.Column():
            prompt = gr.Textbox(label="Concept Description", lines=3,
                                placeholder="dark fantasy warrior in ornate plate armor")
            negative = gr.Textbox(label="Negative Prompt", lines=2,
                                  placeholder="blurry, low quality, watermark")
            with gr.Row():
                steps = gr.Slider(label="Steps", minimum=20, maximum=50, value=30, step=1)
                guidance = gr.Slider(label="Guidance", minimum=4.0, maximum=15.0,
                                     value=7.5, step=0.5)
            seed = gr.Number(label="Seed (-1 = random)", value=-1, precision=0)
            btn = gr.Button("Generate Concept Art", variant="primary")
        with gr.Column():
            image = gr.Image(label="Concept Art (1024×1024)", type="filepath")
    gr.Examples(EXAMPLES, inputs=[prompt, negative, steps, guidance, seed],
                cache_examples=False)
    btn.click(fn=generate_concept, inputs=[prompt, negative, steps, guidance, seed],
              outputs=image)

demo.launch()
