"""assgen.audio.sfx.generate — HuggingFace Space
Generate game sound effects from text descriptions using AudioLDM2.
CLI equivalent: assgen gen audio sfx generate

AudioLDM2 (cvssp/audioldm2) is trained on general audio / sound effects —
not music — which makes it the right model for game SFX prompts.
MusicGen was tried but produces music-like noise for SFX prompts.
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
from diffusers import AudioLDM2Pipeline

MODEL_ID = "cvssp/audioldm2"
SAMPLE_RATE = 16_000  # AudioLDM2 outputs at 16 kHz
NEGATIVE_PROMPT = "Low quality, average quality, noise, hum."

_pipe: AudioLDM2Pipeline | None = None


def _load() -> AudioLDM2Pipeline:
    global _pipe
    if _pipe is None:
        _pipe = AudioLDM2Pipeline.from_pretrained(
            MODEL_ID, torch_dtype=torch.float16
        )
    return _pipe


@spaces.GPU
def generate_sfx(description: str, duration: float) -> str:
    pipe = _load()
    pipe.to("cuda" if torch.cuda.is_available() else "cpu")

    output = pipe(
        description,
        negative_prompt=NEGATIVE_PROMPT,
        num_inference_steps=100,
        audio_length_in_s=duration,
        num_waveforms_per_prompt=1,
    )
    audio = np.array(output.audios[0]).squeeze()

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    scipy.io.wavfile.write(tmp.name, SAMPLE_RATE, audio.astype(np.float32))
    return tmp.name


EXAMPLES = [
    ["sword clashing against metal armor", 2.0],
    ["footsteps on stone dungeon floor", 3.0],
    ["explosion with debris and rumble", 2.5],
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
        "Powered by [AudioLDM2](https://huggingface.co/cvssp/audioldm2) — "
        "trained on general audio and sound effects. "
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
