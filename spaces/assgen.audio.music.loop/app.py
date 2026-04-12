"""assgen.audio.music.loop — HuggingFace Space
Generate seamlessly looping background music for games using MusicGen.
CLI equivalent: assgen gen audio music loop

Uses transformers MusicgenForConditionalGeneration directly — no audiocraft required.
"""
from __future__ import annotations

try:
    import spaces
except (ImportError, AttributeError):
    import types
    spaces = types.SimpleNamespace(GPU=lambda fn: fn)

import scipy.io.wavfile
import tempfile
import gradio as gr
import torch
from transformers import AutoProcessor, MusicgenForConditionalGeneration

MODEL_ID = "facebook/musicgen-stereo-medium"
SAMPLE_RATE = 32_000
FRAME_RATE = 50  # 32000 Hz / 640 hop_length

_processor: AutoProcessor | None = None
_model: MusicgenForConditionalGeneration | None = None


def _load() -> tuple[AutoProcessor, MusicgenForConditionalGeneration]:
    global _processor, _model
    if _processor is None:
        _processor = AutoProcessor.from_pretrained(MODEL_ID)
        _model = MusicgenForConditionalGeneration.from_pretrained(MODEL_ID)
    return _processor, _model


@spaces.GPU
def generate_loop(description: str, duration: float) -> str:
    processor, model = _load()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)

    max_new_tokens = int(duration * FRAME_RATE)
    inputs = processor(text=[description], padding=True, return_tensors="pt").to(device)

    with torch.no_grad():
        audio_values = model.generate(**inputs, max_new_tokens=max_new_tokens)

    # Stereo model: shape (batch=1, channels=2, samples); write as (samples, 2)
    audio_np = audio_values[0].cpu().float().numpy().T
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    scipy.io.wavfile.write(tmp.name, SAMPLE_RATE, audio_np)
    return tmp.name


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
