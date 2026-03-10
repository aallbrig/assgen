"""Handler for audio.process.downmix — stereo↔mono channel conversion.

Primary dep: pydub

    pip install pydub
"""
from __future__ import annotations

try:
    from pydub import AudioSegment
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Downmix or upmix audio channels (stereo→mono or mono→stereo)."""
    if not _AVAILABLE:
        raise RuntimeError("pydub is not installed. Run: pip install pydub")

    import os
    from pathlib import Path
    from pydub import AudioSegment

    input_path = params.get("input")
    if not input_path:
        raise ValueError("Input file not found: None")
    if not os.path.exists(input_path):
        raise ValueError(f"Input file not found: {input_path}")

    target_channels: int = int(params.get("channels", 1))
    if target_channels not in (1, 2):
        raise ValueError("channels must be 1 (mono) or 2 (stereo)")

    progress_cb(0.0, "Loading audio…")
    audio = AudioSegment.from_file(input_path)
    original_channels = audio.channels
    ext = Path(input_path).suffix.lstrip(".").lower() or "wav"

    progress_cb(0.4, f"Converting {original_channels}ch → {target_channels}ch…")

    if target_channels == original_channels:
        result = audio
    elif target_channels == 1:
        # Stereo → mono: average channels
        result = audio.set_channels(1)
    else:
        # Mono → stereo: duplicate channel
        result = AudioSegment.from_mono_audiosegments(audio, audio)

    progress_cb(0.85, "Saving output…")
    out_path = Path(output_dir) / f"downmixed.{ext}"
    result.export(str(out_path), format=ext)

    progress_cb(1.0, "Downmix complete")
    return {
        "files": [str(out_path)],
        "metadata": {
            "input": input_path,
            "original_channels": original_channels,
            "output_channels": target_channels,
            "frame_rate": audio.frame_rate,
            "duration_ms": len(audio),
        },
    }
