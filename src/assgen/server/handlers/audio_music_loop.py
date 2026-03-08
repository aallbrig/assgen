"""Handler for audio.music.loop — looping game music with crossfade stitching.

Generates a music clip with MusicGen and applies a crossfade at the loop point
so the audio loops seamlessly in a game engine.

Requires the ``audiocraft`` package (Meta):
    pip install audiocraft

Falls back to the stub handler if audiocraft is not installed.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

try:
    from audiocraft.models import MusicGen
    from audiocraft.data.audio import audio_write
    _AUDIOCRAFT_AVAILABLE = True
except ImportError:
    _AUDIOCRAFT_AVAILABLE = False


ProgressCallback = Callable[[float, str], None]

# Default crossfade length in seconds
_DEFAULT_FADE_SEC = 1.5


def _crossfade_loop(audio: "np.ndarray", sample_rate: int, fade_sec: float = _DEFAULT_FADE_SEC) -> "np.ndarray":
    """Apply a crossfade between the tail and the head of *audio*.

    Returns a slightly shorter clip whose end blends into its beginning,
    creating a seamless loop point.

    Args:
        audio: Float32 array of shape ``(channels, samples)``.
        sample_rate: Audio sample rate in Hz.
        fade_sec: Duration of the crossfade in seconds.

    Returns:
        Crossfaded float32 array of the same channel count.
    """
    fade_samples = int(fade_sec * sample_rate)
    if fade_samples * 2 >= audio.shape[-1]:
        # Track too short to crossfade — return as-is
        return audio

    fade_out = np.linspace(1.0, 0.0, fade_samples, dtype=np.float32)
    fade_in  = np.linspace(0.0, 1.0, fade_samples, dtype=np.float32)

    result = audio.copy()
    # Blend the last *fade_samples* of the tail into the first *fade_samples* of the head
    result[..., :fade_samples]  = audio[..., :fade_samples]  * fade_in  + audio[..., -fade_samples:] * fade_out
    # Drop the tail (it has been folded into the head)
    result = result[..., :-fade_samples]
    return result


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
    import numpy as np  # lazy — only required when audiocraft is installed

    if not _AUDIOCRAFT_AVAILABLE:
        raise RuntimeError(
            "audiocraft is not installed.  "
            "Run: pip install audiocraft"
        )

    prompt: str = params.get("prompt") or params.get("description") or "ambient game loop"
    duration: float = float(params.get("duration", 20.0))
    fade_sec: float = float(params.get("fade_sec", _DEFAULT_FADE_SEC))

    progress_cb(0.25, "Loading MusicGen Stereo model…")
    load_from = model_path or model_id or "facebook/musicgen-stereo-medium"
    model = MusicGen.get_pretrained(load_from)
    # Generate slightly longer than requested so the crossfade doesn't shorten below target
    generate_sec = duration + fade_sec
    model.set_generation_params(duration=generate_sec)

    progress_cb(0.40, "Generating loop clip…")
    wavs = model.generate([prompt])
    audio_np = wavs[0].cpu().numpy()  # shape: (channels, samples)

    progress_cb(0.75, "Applying crossfade loop stitching…")
    looped = _crossfade_loop(audio_np, model.sample_rate, fade_sec=fade_sec)

    progress_cb(0.88, "Writing loop WAV…")
    import torch
    looped_tensor = torch.from_numpy(looped)
    out_path = output_dir / "loop"
    audio_write(
        str(out_path),
        looped_tensor,
        model.sample_rate,
        strategy="loudness",
    )
    wav_name = out_path.with_suffix(".wav").name

    progress_cb(1.0, "Loop generation complete")
    return {
        "files": [wav_name],
        "metadata": {
            "model_id": model_id or "facebook/musicgen-stereo-medium",
            "prompt": prompt,
            "requested_duration_seconds": duration,
            "fade_sec": fade_sec,
            "sample_rate": model.sample_rate,
            "loop_ready": True,
        },
    }
