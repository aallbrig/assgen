"""assgen.audio.sfx.generate — HuggingFace Space
Generate game sound effects from text descriptions (MusicGen Small).
CLI equivalent: assgen gen audio sfx generate

Note: facebook/audiogen-medium was removed in transformers 5.x.
Uses facebook/musicgen-small which is fully supported and produces
comparable results for game SFX with appropriate text prompts.
"""
from __future__ import annotations

try:
    import spaces
except (ImportError, AttributeError):
    import types
    spaces = types.SimpleNamespace(GPU=lambda fn: fn)

import numpy as np
import scipy.io.wavfile
import tempfile
import gradio as gr
import torch
from transformers import pipeline

MODEL_ID = "facebook/musicgen-small"
# MusicGen EnCodec: 32000 Hz / 640 hop_length = 50 tokens/second
SAMPLE_RATE = 32_000
FRAME_RATE = 50

_pipe = None


def _load():
    global _pipe
    if _pipe is None:
        device = 0 if torch.cuda.is_available() else -1
        _pipe = pipeline("text-to-audio", model=MODEL_ID, device=device)
    return _pipe


@spaces.GPU
def generate_sfx(description: str, duration: float) -> str:
    p = _load()
    max_new_tokens = int(duration * FRAME_RATE)
    result = p(description, forward_params={"max_new_tokens": max_new_tokens})

    audio = np.array(result["audio"]).squeeze()
    sr = result["sampling_rate"]

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    scipy.io.wavfile.write(tmp.name, sr, audio.astype(np.float32))
    return tmp.name


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
        "Powered by [MusicGen Small](https://huggingface.co/facebook/musicgen-small). "
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
