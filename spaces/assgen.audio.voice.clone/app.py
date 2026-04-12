"""assgen.audio.voice.clone — HuggingFace Space
Clone a voice from a reference clip and synthesize speech using XTTS-v2.
CLI equivalent: assgen gen audio voice clone
"""
from __future__ import annotations

try:
    import spaces
except (ImportError, AttributeError):
    import types
    spaces = types.SimpleNamespace(GPU=lambda fn: fn)

import gradio as gr
from assgen.sdk import run

LANGUAGES = ["en", "es", "fr", "de", "it", "pt", "nl", "pl", "cs", "ar", "tr", "ru", "hi", "zh"]


@spaces.GPU
def clone_voice(reference_audio: str, text: str, language: str) -> str:
    result = run(
        "audio.voice.clone",
        {"speaker_wav": reference_audio, "prompt": text, "language": language},
        device="cuda",
    )
    return result["files"][0]


with gr.Blocks(title="assgen · Voice Cloning") as demo:
    gr.Markdown(
        "# assgen · Voice Cloning\n"
        "Clone a voice from a 5–30 s reference clip and synthesize speech in that voice. "
        "Powered by [Coqui XTTS-v2](https://huggingface.co/coqui/XTTS-v2). "
        "Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.\n\n"
        "_ZeroGPU — cold start ~60 s. Reference clip must be clear speech, 5–30 s._"
    )
    with gr.Row():
        with gr.Column():
            reference = gr.Audio(label="Reference Voice Clip (5–30 s WAV/MP3)",
                                 type="filepath")
            text = gr.Textbox(label="Text to Synthesize", lines=4,
                              placeholder="Hello, brave adventurer. I have a quest for you.")
            language = gr.Dropdown(label="Language", choices=LANGUAGES, value="en")
            btn = gr.Button("Clone & Synthesize", variant="primary")
        with gr.Column():
            audio = gr.Audio(label="Synthesized Voice", type="filepath")
    btn.click(fn=clone_voice, inputs=[reference, text, language], outputs=audio)

demo.launch()
