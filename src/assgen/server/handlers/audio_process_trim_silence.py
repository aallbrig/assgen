"""Handler for audio.process.trim_silence — strip leading/trailing silence.

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
    """Strip leading and trailing silence from an audio file."""
    if not _AVAILABLE:
        raise RuntimeError("pydub is not installed. Run: pip install pydub")

    import os
    from pathlib import Path

    from pydub.silence import detect_leading_silence

    input_path = params.get("input")
    if not input_path:
        raise ValueError("Input file not found: None")
    if not os.path.exists(input_path):
        raise ValueError(f"Input file not found: {input_path}")

    threshold_db: float = float(params.get("threshold_db", -50))

    progress_cb(0.0, "Loading audio…")
    audio = AudioSegment.from_file(input_path)
    original_duration_ms = len(audio)

    ext = Path(input_path).suffix.lstrip(".").lower() or "wav"

    progress_cb(0.3, "Detecting leading silence…")
    start_trim = detect_leading_silence(audio, silence_threshold=threshold_db)

    progress_cb(0.6, "Detecting trailing silence…")
    reversed_audio = audio.reverse()
    end_trim = detect_leading_silence(reversed_audio, silence_threshold=threshold_db)

    trimmed = audio[start_trim : len(audio) - end_trim] if end_trim > 0 else audio[start_trim:]
    trimmed_ms = original_duration_ms - len(trimmed)

    progress_cb(0.85, "Saving trimmed audio…")
    out_path = Path(output_dir) / f"trimmed.{ext}"
    trimmed.export(str(out_path), format=ext)

    progress_cb(1.0, "Trim silence complete")
    return {
        "files": [str(out_path)],
        "metadata": {
            "input": input_path,
            "original_duration_ms": original_duration_ms,
            "trimmed_duration_ms": len(trimmed),
            "trimmed_ms": trimmed_ms,
            "leading_trimmed_ms": start_trim,
            "trailing_trimmed_ms": end_trim,
            "threshold_db": threshold_db,
        },
    }
