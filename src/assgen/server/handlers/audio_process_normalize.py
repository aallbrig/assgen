"""Handler for audio.process.normalize — LUFS or peak normalization.

Primary dep: pydub
Optional dep: pyloudnorm (for LUFS mode; falls back to peak if not installed)

    pip install pydub pyloudnorm
"""
from __future__ import annotations

try:
    from pydub import AudioSegment
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Normalize audio to LUFS target or peak 0 dBFS."""
    if not _AVAILABLE:
        raise RuntimeError("pydub is not installed. Run: pip install pydub")

    import os
    from pathlib import Path
    from pydub import effects as pydub_effects

    try:
        import pyloudnorm as pyln
        import numpy as np
        _PYLOUDNORM = True
    except ImportError:
        _PYLOUDNORM = False

    input_path = params.get("input")
    if not input_path:
        raise ValueError("Input file not found: None")
    if not os.path.exists(input_path):
        raise ValueError(f"Input file not found: {input_path}")

    lufs_target: float = float(params.get("lufs", -14.0))
    mode: str = params.get("mode", "lufs")

    progress_cb(0.0, "Loading audio…")
    audio = AudioSegment.from_file(input_path)

    ext = Path(input_path).suffix.lstrip(".").lower() or "wav"

    progress_cb(0.3, f"Normalizing ({mode})…")

    if mode == "peak":
        normalized = pydub_effects.normalize(audio)
        meta_mode = "peak"
        meta_extra = {}
    else:
        # LUFS mode
        if _PYLOUDNORM:
            samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
            samples /= float(2 ** (audio.sample_width * 8 - 1))
            if audio.channels == 2:
                samples = samples.reshape((-1, 2))
            else:
                samples = samples.reshape((-1, 1))
            meter = pyln.Meter(audio.frame_rate)
            loudness = meter.integrated_loudness(samples)
            gain_db = lufs_target - loudness
            normalized = audio.apply_gain(gain_db)
            meta_mode = "lufs"
            meta_extra = {"lufs_target": lufs_target, "lufs_measured": float(loudness), "gain_db": float(gain_db)}
        else:
            # Fall back to peak normalization
            normalized = pydub_effects.normalize(audio)
            meta_mode = "lufs_fallback_peak"
            meta_extra = {"lufs_target": lufs_target, "note": "pyloudnorm not installed; used peak normalization"}

    progress_cb(0.8, "Saving output…")
    out_path = Path(output_dir) / f"normalized.{ext}"
    normalized.export(str(out_path), format=ext)

    progress_cb(1.0, "Normalization complete")
    return {
        "files": [str(out_path)],
        "metadata": {
            "mode": meta_mode,
            "input": input_path,
            "channels": audio.channels,
            "frame_rate": audio.frame_rate,
            **meta_extra,
        },
    }
