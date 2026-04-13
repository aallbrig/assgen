"""assgen.audio.voice.tts — HuggingFace Space
Generate expressive NPC speech using Bark Small (suno/bark-small).
Supports non-verbal tokens: [laughs], [sighs], [gasps], ... (pause), ♪ (singing).
CLI equivalent: assgen gen audio voice tts

Uses AutoProcessor + BarkModel directly (not pipeline) so that voice_preset
is passed to the processor where Bark expects it, not to model.generate()
where it raises ValueError.
"""
from __future__ import annotations

try:
    import spaces; spaces.GPU  # AttributeError if wrong package
except (ImportError, AttributeError):
    import types
    spaces = types.SimpleNamespace(GPU=lambda fn: fn)

import numpy as np
import scipy.io.wavfile
import tempfile
import gradio as gr
import torch
from transformers import AutoProcessor, BarkModel

MODEL_ID = "suno/bark-small"

_processor: AutoProcessor | None = None
_model: BarkModel | None = None


def _load() -> tuple[AutoProcessor, BarkModel]:
    global _processor, _model
    if _processor is None:
        _processor = AutoProcessor.from_pretrained(MODEL_ID)
        _model = BarkModel.from_pretrained(
            MODEL_ID, torch_dtype=torch.float16
        )
    return _processor, _model


VOICE_PRESETS = [
    ("EN Voice 1",  "v2/en_speaker_0"),
    ("EN Voice 2",  "v2/en_speaker_1"),
    ("EN Voice 3",  "v2/en_speaker_2"),
    ("EN Voice 4",  "v2/en_speaker_3"),
    ("EN Voice 5",  "v2/en_speaker_4"),
    ("EN Voice 6",  "v2/en_speaker_5"),
    ("EN Voice 7",  "v2/en_speaker_6"),
    ("EN Voice 8",  "v2/en_speaker_7"),
    ("EN Voice 9",  "v2/en_speaker_8"),
    ("EN Voice 10", "v2/en_speaker_9"),
]
VOICE_LABELS = [label for label, _ in VOICE_PRESETS]
VOICE_MAP    = dict(VOICE_PRESETS)


@spaces.GPU
def generate_tts(text: str, voice_label: str) -> str:
    processor, model = _load()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)

    voice_preset = VOICE_MAP.get(voice_label, "v2/en_speaker_6")
    # voice_preset must go to the processor, NOT to model.generate()
    inputs = processor(text, voice_preset=voice_preset, return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        audio_array = model.generate(**inputs)

    audio_array = audio_array.cpu().numpy().squeeze()
    sample_rate = model.generation_config.sample_rate

    audio_int16 = (audio_array / (np.max(np.abs(audio_array)) + 1e-8) * 32767).astype(np.int16)

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    scipy.io.wavfile.write(tmp.name, sample_rate, audio_int16)
    return tmp.name


EXAMPLES = [
    ["Halt! Who goes there? State your business at once.", "EN Voice 1"],
    ["The treasure you seek... [sighs] ...it was never in this dungeon.", "EN Voice 6"],
    ["Ha! [laughs] You actually thought you could defeat me?", "EN Voice 4"],
    ["Please... [gasps] ...warn the others. They're coming.", "EN Voice 8"],
    ["Welcome, traveler. I've been expecting you... for a very long time.", "EN Voice 3"],
]

with gr.Blocks(title="assgen · NPC Voice TTS") as demo:
    gr.Markdown(
        "# 🎙️ assgen · NPC Voice TTS\n"
        "Generate expressive NPC speech. Supports non-verbal tokens: "
        "`[laughs]`, `[sighs]`, `[gasps]`, `[clears throat]`, `...` (pause), `♪` (singing).\n"
        "Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.\n\n"
        "_ZeroGPU — may queue briefly during high traffic._"
    )
    with gr.Row():
        with gr.Column():
            text = gr.Textbox(label="NPC Dialogue Text",
                              placeholder="Halt! Who goes there? State your business.", lines=4)
            voice = gr.Radio(label="Voice Preset", choices=VOICE_LABELS, value=VOICE_LABELS[0])
            btn = gr.Button("Generate Speech", variant="primary")
        with gr.Column():
            audio = gr.Audio(label="Generated Speech", type="filepath")
    gr.Examples(EXAMPLES, inputs=[text, voice], cache_examples=False)
    btn.click(fn=generate_tts, inputs=[text, voice], outputs=audio)

demo.launch()
