"""assgen.audio.ambient.generate — HuggingFace Space
Generate looping ambient soundscapes using MusicGen Stereo Large.
CLI equivalent: assgen gen audio ambient generate
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
def generate_ambient(description: str, duration: float) -> str:
    result = run(
        "audio.ambient.generate",
        {"prompt": description, "duration": duration},
        device="cuda",
    )
    return result["files"][0]


EXAMPLES = [
    ["eerie cave drips echoing in the dark", 20.0],
    ["bustling market square ambience, crowd and merchants", 30.0],
    ["thunderstorm at sea, rain on wood, waves crashing", 20.0],
    ["dense jungle at night, insects and frogs", 30.0],
    ["ancient stone dungeon, distant torches flickering", 20.0],
    ["wind howling across a frozen tundra", 20.0],
]

with gr.Blocks(title="assgen · Ambient Soundscape Generator") as demo:
    gr.Markdown(
        "# assgen · Ambient Soundscape Generator\n"
        "Generate looping stereo ambient soundscapes for game environments. "
        "Powered by [MusicGen Stereo Large](https://huggingface.co/facebook/musicgen-stereo-large). "
        "Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.\n\n"
        "_ZeroGPU — stereo large model (~3.3 GB), cold start ~90 s._"
    )
    with gr.Row():
        with gr.Column():
            prompt = gr.Textbox(label="Ambient Description", lines=3,
                                placeholder="eerie cave drips echoing in the dark")
            duration = gr.Slider(label="Duration (seconds)",
                                 minimum=10.0, maximum=60.0, value=20.0, step=5.0)
            btn = gr.Button("Generate Ambient", variant="primary")
        with gr.Column():
            audio = gr.Audio(label="Generated Ambience", type="filepath")
    gr.Examples(EXAMPLES, inputs=[prompt, duration], cache_examples=False)
    btn.click(fn=generate_ambient, inputs=[prompt, duration], outputs=audio)

demo.launch()
