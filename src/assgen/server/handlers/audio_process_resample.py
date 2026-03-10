"""Handler for audio.process.resample — change audio sample rate.

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
    """Resample audio to a target sample rate."""
    if not _AVAILABLE:
        raise RuntimeError("pydub is not installed. Run: pip install pydub")

    import os
    from pathlib import Path

    input_path = params.get("input")
    if not input_path:
        raise ValueError("Input file not found: None")
    if not os.path.exists(input_path):
        raise ValueError(f"Input file not found: {input_path}")

    target_rate: int = int(params.get("rate", 48000))

    progress_cb(0.0, "Loading audio…")
    audio = AudioSegment.from_file(input_path)
    original_rate = audio.frame_rate
    ext = Path(input_path).suffix.lstrip(".").lower() or "wav"

    progress_cb(0.4, f"Resampling {original_rate} Hz → {target_rate} Hz…")
    resampled = audio.set_frame_rate(target_rate)

    progress_cb(0.85, "Saving output…")
    out_path = Path(output_dir) / f"resampled.{ext}"
    resampled.export(str(out_path), format=ext)

    progress_cb(1.0, "Resample complete")
    return {
        "files": [str(out_path)],
        "metadata": {
            "input": input_path,
            "original_rate": original_rate,
            "output_rate": target_rate,
            "channels": audio.channels,
            "duration_ms": len(audio),
        },
    }
