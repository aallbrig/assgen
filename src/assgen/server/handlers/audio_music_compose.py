"""Handler for audio.music.compose — MusicGen single-stem track generation.

Requires transformers and torch:
    pip install transformers accelerate torch scipy numpy
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

try:
    from transformers import MusicgenForConditionalGeneration  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False

ProgressCallback = Callable[[float, str], None]

_DEFAULT_MODEL = "facebook/musicgen-large"
# MusicGen EnCodec: 32 kHz / 640 hop_length = 50 frames/second
_SAMPLE_RATE = 32_000
_FRAME_RATE = 50


def run(
    job_type: str,
    params: dict[str, Any],
    model_id: str | None,
    model_path: str | None,
    device: str,
    progress_cb: ProgressCallback,
    output_dir: Path,
) -> dict[str, Any]:
    """Generate a music track from a text prompt."""
    if not _AVAILABLE:
        raise RuntimeError(
            "transformers is required.  "
            "Run: pip install transformers accelerate torch scipy numpy"
        )

    import scipy.io.wavfile
    import torch
    from transformers import AutoProcessor, MusicgenForConditionalGeneration

    prompt: str = params.get("prompt") or params.get("description") or "game soundtrack"
    duration: float = float(params.get("duration", 30.0))
    variations: int = max(1, int(params.get("variations", 1)))

    progress_cb(0.1, "Loading MusicGen model…")
    load_from = model_path or model_id or _DEFAULT_MODEL
    processor = AutoProcessor.from_pretrained(load_from)
    model = MusicgenForConditionalGeneration.from_pretrained(load_from)
    model.to(device)

    max_new_tokens = int(duration * _FRAME_RATE)
    prompts = [prompt] * variations

    progress_cb(0.3, f"Composing {variations} track(s)…")
    inputs = processor(text=prompts, padding=True, return_tensors="pt").to(device)
    with torch.no_grad():
        audio_values = model.generate(**inputs, max_new_tokens=max_new_tokens)

    # audio_values shape: (batch, channels, samples)
    # channels=1 for mono models, channels=2 for stereo models
    channels = audio_values.shape[1]

    progress_cb(0.85, "Writing WAV files…")
    saved: list[str] = []
    for idx in range(variations):
        stem = f"track_{idx:02d}" if variations > 1 else "track"
        out_name = f"{stem}.wav"
        out_path = Path(output_dir) / out_name

        if channels > 1:
            # Stereo: (channels, samples) → (samples, channels) for scipy
            audio_np = audio_values[idx].cpu().float().numpy().T
        else:
            # Mono: (1, samples) → (samples,)
            audio_np = audio_values[idx, 0].cpu().float().numpy()

        scipy.io.wavfile.write(str(out_path), _SAMPLE_RATE, audio_np)
        saved.append(out_name)

    progress_cb(1.0, "Music generation complete")
    return {
        "files": saved,
        "metadata": {
            "model_id": load_from,
            "prompt": prompt,
            "duration_seconds": duration,
            "variations": variations,
            "sample_rate": _SAMPLE_RATE,
        },
    }
