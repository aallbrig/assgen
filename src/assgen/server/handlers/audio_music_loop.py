"""Handler for audio.music.loop — looping game music with crossfade stitching.

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

_DEFAULT_MODEL = "facebook/musicgen-stereo-medium"
# MusicGen EnCodec: 32 kHz / 640 hop_length = 50 frames/second
_SAMPLE_RATE = 32_000
_FRAME_RATE = 50
_DEFAULT_FADE_SEC = 1.5


def _crossfade_loop(audio: "Any", fade_sec: float = _DEFAULT_FADE_SEC) -> "Any":
    """Apply a crossfade between the tail and the head of *audio*.

    Returns a slightly shorter clip whose end blends into its beginning,
    creating a seamless loop point.

    Args:
        audio:    Float32 numpy array of shape ``(channels, samples)`` or ``(samples,)``
                  for mono.
        fade_sec: Duration of the crossfade in seconds.

    Returns:
        Crossfaded float32 array of the same leading dimensions.
    """
    import numpy as np

    fade_samples = int(fade_sec * _SAMPLE_RATE)
    if fade_samples * 2 >= audio.shape[-1]:
        return audio  # track too short to crossfade — return as-is

    fade_out = np.linspace(1.0, 0.0, fade_samples, dtype=np.float32)
    fade_in  = np.linspace(0.0, 1.0, fade_samples, dtype=np.float32)

    result = audio.copy()
    result[..., :fade_samples] = (
        audio[..., :fade_samples] * fade_in
        + audio[..., -fade_samples:] * fade_out
    )
    return result[..., :-fade_samples]


def run(
    job_type: str,
    params: dict[str, Any],
    model_id: str | None,
    model_path: str | None,
    device: str,
    progress_cb: ProgressCallback,
    output_dir: Path,
) -> dict[str, Any]:
    """Generate a seamlessly looping music clip."""
    if not _AVAILABLE:
        raise RuntimeError(
            "transformers is required.  "
            "Run: pip install transformers accelerate torch scipy numpy"
        )

    import scipy.io.wavfile
    import torch
    from transformers import AutoProcessor, MusicgenForConditionalGeneration

    prompt: str = params.get("prompt") or params.get("description") or "ambient game loop"
    duration: float = float(params.get("duration", 20.0))
    fade_sec: float = float(params.get("fade_sec", _DEFAULT_FADE_SEC))

    # Generate slightly longer than requested so crossfade doesn't shorten below target
    generate_sec = duration + fade_sec

    progress_cb(0.1, "Loading MusicGen model…")
    load_from = model_path or model_id or _DEFAULT_MODEL
    processor = AutoProcessor.from_pretrained(load_from)
    model = MusicgenForConditionalGeneration.from_pretrained(load_from)
    model.to(device)

    max_new_tokens = int(generate_sec * _FRAME_RATE)

    progress_cb(0.3, "Generating loop clip…")
    inputs = processor(text=[prompt], padding=True, return_tensors="pt").to(device)
    with torch.no_grad():
        audio_values = model.generate(**inputs, max_new_tokens=max_new_tokens)

    # audio_values shape: (batch=1, channels, samples)
    audio_np = audio_values[0].cpu().float().numpy()  # (channels, samples)

    progress_cb(0.75, "Applying crossfade loop stitching…")
    looped = _crossfade_loop(audio_np, fade_sec=fade_sec)

    progress_cb(0.9, "Writing loop WAV…")
    out_name = "loop.wav"
    out_path = Path(output_dir) / out_name

    channels = looped.shape[0]
    if channels > 1:
        # Stereo: (channels, samples) → (samples, channels) for scipy
        scipy.io.wavfile.write(str(out_path), _SAMPLE_RATE, looped.T)
    else:
        # Mono: (1, samples) → (samples,)
        scipy.io.wavfile.write(str(out_path), _SAMPLE_RATE, looped[0])

    progress_cb(1.0, "Loop generation complete")
    return {
        "files": [out_name],
        "metadata": {
            "model_id": load_from,
            "prompt": prompt,
            "requested_duration_seconds": duration,
            "fade_sec": fade_sec,
            "sample_rate": _SAMPLE_RATE,
            "loop_ready": True,
        },
    }
