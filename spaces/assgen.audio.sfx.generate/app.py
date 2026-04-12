"""assgen.audio.sfx.generate — HuggingFace Space
Generate game sound effects from text descriptions (AudioGen Medium).
CLI equivalent: assgen gen audio sfx generate

Uses transformers AudiogenForConditionalGeneration directly — no audiocraft required.
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
from transformers import AutoProcessor, AudiogenForConditionalGeneration

MODEL_ID = "facebook/audiogen-medium"
SAMPLE_RATE = 16_000
# AudioGen EnCodec: 16000 Hz / 320 hop_length = 50 frames per second
FRAME_RATE = 50

_processor: AutoProcessor | None = None
_model: AudiogenForConditionalGeneration | None = None


def _load() -> tuple[AutoProcessor, AudiogenForConditionalGeneration]:
    global _processor, _model
    if _processor is None:
        _processor = AutoProcessor.from_pretrained(MODEL_ID)
        _model = AudiogenForConditionalGeneration.from_pretrained(MODEL_ID)
    return _processor, _model


@spaces.GPU
def generate_sfx(description: str, duration: float) -> str:
    processor, model = _load()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)

    max_new_tokens = int(duration * FRAME_RATE)
    inputs = processor(text=[description], padding=True, return_tensors="pt").to(device)

    with torch.no_grad():
        audio_values = model.generate(**inputs, max_new_tokens=max_new_tokens)

    # shape: (batch=1, channels=1, samples)
    audio_np = audio_values[0, 0].cpu().float().numpy()
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    scipy.io.wavfile.write(tmp.name, SAMPLE_RATE, audio_np)
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
