"""Handler for audio.process.convert — audio format conversion.

Primary dep: pydub (requires ffmpeg for ogg/mp3 output)

    pip install pydub
"""
from __future__ import annotations

try:
    from pydub import AudioSegment
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Convert audio to a different format (WAV, OGG, MP3, FLAC)."""
    if not _AVAILABLE:
        raise RuntimeError("pydub is not installed. Run: pip install pydub")

    import os
    from pathlib import Path

    input_path = params.get("input")
    if not input_path:
        raise ValueError("Input file not found: None")
    if not os.path.exists(input_path):
        raise ValueError(f"Input file not found: {input_path}")

    target_format: str = params.get("format", "ogg").lower().lstrip(".")

    progress_cb(0.0, "Loading audio…")
    audio = AudioSegment.from_file(input_path)

    progress_cb(0.5, f"Converting to {target_format}…")
    out_path = Path(output_dir) / f"output.{target_format}"

    export_kwargs = {}
    if target_format == "mp3":
        export_kwargs["bitrate"] = "192k"
    elif target_format == "ogg":
        export_kwargs["codec"] = "libvorbis"

    audio.export(str(out_path), format=target_format, **export_kwargs)

    progress_cb(1.0, "Conversion complete")
    return {
        "files": [str(out_path)],
        "metadata": {
            "input": input_path,
            "input_format": Path(input_path).suffix.lstrip(".").lower(),
            "output_format": target_format,
            "channels": audio.channels,
            "frame_rate": audio.frame_rate,
            "sample_width": audio.sample_width,
            "duration_ms": len(audio),
        },
    }
