"""assgen.audio.music.compose — HuggingFace Space
Generate game music tracks from text descriptions (MusicGen Medium).
CLI equivalent: assgen gen audio music compose
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
def compose_music(description: str, duration: float) -> str:
    result = run(
        "audio.music.compose",
        {"prompt": description, "duration": duration},
        device="cuda",
    )
    return result["files"][0]


EXAMPLES = [
    ["epic orchestral battle music with powerful drums and brass", 15.0],
    ["calm ambient forest exploration with gentle wind and birds", 20.0],
    ["8-bit chiptune dungeon crawl music, retro video game style", 12.0],
    ["tense horror ambience with strings and sudden impacts", 15.0],
    ["upbeat medieval tavern folk music with lute and flute", 15.0],
    ["cinematic space exploration theme with synthesizer and choir", 20.0],
]

with gr.Blocks(title="assgen · Music Composer") as demo:
    gr.Markdown(
        "# 🎵 assgen · Music Composer\n"
        "Generate game music tracks from text. "
        "Powered by [MusicGen Medium](https://huggingface.co/facebook/musicgen-medium). "
        "Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.\n\n"
        "_ZeroGPU — may queue briefly during high traffic._"
    )
    with gr.Row():
        with gr.Column():
            prompt = gr.Textbox(label="Music Description",
                                placeholder="epic orchestral battle music with powerful drums",
                                lines=3)
            duration = gr.Slider(label="Duration (seconds)",
                                 minimum=5.0, maximum=30.0, value=15.0, step=1.0)
            btn = gr.Button("Compose Music", variant="primary")
        with gr.Column():
            audio = gr.Audio(label="Generated Music Track", type="filepath")
    gr.Examples(EXAMPLES, inputs=[prompt, duration], cache_examples=False)
    btn.click(fn=compose_music, inputs=[prompt, duration], outputs=audio)

demo.launch()
