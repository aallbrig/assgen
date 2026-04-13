"""assgen.audio.ambient.generate — HuggingFace Space
Generate looping ambient soundscapes using MusicGen Stereo Large.
CLI equivalent: assgen gen audio ambient generate

Uses transformers MusicgenForConditionalGeneration directly — no audiocraft required.
"""
from __future__ import annotations

try:
    import spaces; spaces.GPU  # AttributeError if wrong package
except (ImportError, AttributeError):
    import types
    spaces = types.SimpleNamespace(GPU=lambda fn: fn)

import scipy.io.wavfile
import tempfile
import gradio as gr
import torch
from transformers import AutoProcessor, MusicgenForConditionalGeneration

MODEL_ID = "facebook/musicgen-stereo-large"
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
def generate_ambient(description: str, duration: float) -> str:
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
