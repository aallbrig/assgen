"""assgen.audio.music.loop — HuggingFace Space
Generate seamlessly looping background music for games using MusicGen.
CLI equivalent: assgen gen audio music loop
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
def generate_loop(description: str, duration: float) -> str:
    result = run(
        "audio.music.loop",
        {"prompt": description, "duration": duration},
        device="cuda",
    )
    return result["files"][0]


EXAMPLES = [
    ["upbeat tavern music, lute and drums, lively", 15.0],
    ["tense combat music, orchestral, driving percussion", 10.0],
    ["peaceful village theme, flute and strings, gentle", 15.0],
    ["mysterious dungeon ambient music, low strings, eerie", 15.0],
    ["epic boss battle, full orchestra, intense", 10.0],
]

with gr.Blocks(title="assgen · Music Loop Generator") as demo:
    gr.Markdown(
        "# assgen · Music Loop Generator\n"
        "Generate seamlessly looping background music for game scenes. "
        "Powered by [MusicGen Medium](https://huggingface.co/facebook/musicgen-medium). "
        "Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.\n\n"
        "_ZeroGPU — may queue briefly during high traffic._"
    )
    with gr.Row():
        with gr.Column():
            prompt = gr.Textbox(label="Music Description", lines=3,
                                placeholder="upbeat tavern music, lute and drums, lively")
            duration = gr.Slider(label="Duration (seconds)",
                                 minimum=5.0, maximum=30.0, value=15.0, step=5.0)
            btn = gr.Button("Generate Loop", variant="primary")
        with gr.Column():
            audio = gr.Audio(label="Generated Music Loop", type="filepath")
    gr.Examples(EXAMPLES, inputs=[prompt, duration], cache_examples=False)
    btn.click(fn=generate_loop, inputs=[prompt, duration], outputs=audio)

demo.launch()
