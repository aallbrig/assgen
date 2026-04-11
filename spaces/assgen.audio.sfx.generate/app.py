"""assgen.audio.sfx.generate — HuggingFace Space
Generate game sound effects from text descriptions (AudioGen Medium).
CLI equivalent: assgen gen audio sfx generate
"""
from __future__ import annotations

try:
    import spaces
except (ImportError, AttributeError):
    import types
    spaces = types.SimpleNamespace(GPU=lambda fn: fn)

import gradio as gr
from assgen.sdk import run


@spaces.GPU
def generate_sfx(description: str, duration: float) -> str:
    result = run(
        "audio.sfx.generate",
        {"prompt": description, "duration": duration},
        device="cuda",
    )
    return result["files"][0]


EXAMPLES = [
    ["sword clashing against armor", 2.0],
    ["footsteps on stone dungeon floor", 3.0],
    ["explosion with debris and dust", 2.5],
    ["wooden door creaking open slowly", 1.5],
    ["arrow whooshing through air", 1.0],
    ["fire crackling in a campfire", 4.0],
    ["coin pickup jingle", 0.8],
    ["magic spell casting with sparkles", 2.0],
]

with gr.Blocks(title="assgen · Audio SFX Generator") as demo:
    gr.Markdown(
        "# 🔊 assgen · Audio SFX Generator\n"
        "Generate game sound effects from text. "
        "Powered by [AudioGen Medium](https://huggingface.co/facebook/audiogen-medium). "
        "Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.\n\n"
        "_ZeroGPU — may queue briefly during high traffic._"
    )
    with gr.Row():
        with gr.Column():
            prompt = gr.Textbox(label="Sound Effect Description",
                                placeholder="sword clashing against armor", lines=2)
            duration = gr.Slider(label="Duration (seconds)",
                                 minimum=0.5, maximum=10.0, value=3.0, step=0.5)
            btn = gr.Button("Generate SFX", variant="primary")
        with gr.Column():
            audio = gr.Audio(label="Generated Sound Effect", type="filepath")
    gr.Examples(EXAMPLES, inputs=[prompt, duration], cache_examples=False)
    btn.click(fn=generate_sfx, inputs=[prompt, duration], outputs=audio)

demo.launch()
