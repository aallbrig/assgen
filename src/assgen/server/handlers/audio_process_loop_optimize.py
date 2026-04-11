"""Handler for audio.process.loop_optimize — find zero-crossing loop points.

Primary dep: pydub (for audio loading); numpy (optional, falls back to array module)

    pip install pydub numpy
"""
from __future__ import annotations

try:
    from pydub import AudioSegment
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Find zero-crossing loop points and export trimmed loop audio."""
    if not _AVAILABLE:
        raise RuntimeError("pydub is not installed. Run: pip install pydub")

    import json
    import os
    from pathlib import Path

    try:
        import numpy as np
        _NP = True
    except ImportError:
        _NP = False

    input_path = params.get("input")
    if not input_path:
        raise ValueError("Input file not found: None")
    if not os.path.exists(input_path):
        raise ValueError(f"Input file not found: {input_path}")

    progress_cb(0.0, "Loading audio…")
    audio = AudioSegment.from_file(input_path)
    ext = Path(input_path).suffix.lstrip(".").lower() or "wav"
    sample_rate = audio.frame_rate
    channels = audio.channels

    # Convert to list of samples (mono mix)
    raw = audio.get_array_of_samples()
    if _NP:
        samples = np.array(raw)
        if channels == 2:
            samples = samples.reshape((-1, 2)).mean(axis=1).astype(samples.dtype)
    else:
        samples_list = list(raw)
        if channels == 2:
            samples_list = [(samples_list[i] + samples_list[i + 1]) // 2
                            for i in range(0, len(samples_list) - 1, 2)]
        samples = samples_list

    n = len(samples)

    def _get_sample(idx):
        return int(samples[idx]) if not _NP else int(samples[idx])

    def _find_zero_crossing_after(start_idx, end_idx):
        for i in range(start_idx, end_idx - 1):
            if _get_sample(i) <= 0 <= _get_sample(i + 1) or _get_sample(i) >= 0 >= _get_sample(i + 1):
                return i
        return start_idx

    def _find_zero_crossing_before(start_idx, end_idx):
        for i in range(end_idx, start_idx, -1):
            if _get_sample(i) <= 0 <= _get_sample(i - 1) or _get_sample(i) >= 0 >= _get_sample(i - 1):
                return i
        return end_idx

    progress_cb(0.3, "Finding zero crossings…")
    ten_pct = int(n * 0.10)
    twenty_pct = int(n * 0.20)
    loop_start = _find_zero_crossing_after(ten_pct, twenty_pct)

    eighty_pct = int(n * 0.80)
    ninety_pct = int(n * 0.90)
    loop_end = _find_zero_crossing_before(eighty_pct, ninety_pct)

    progress_cb(0.6, "Optimizing loop end by energy matching…")
    # Search window around loop_end for best match to loop_start amplitude
    window = min(1000, (ninety_pct - eighty_pct) // 2)
    best_idx = loop_end
    best_diff = abs(_get_sample(loop_end) - _get_sample(loop_start))
    for i in range(max(eighty_pct, loop_end - window), min(ninety_pct, loop_end + window)):
        if _get_sample(i) <= 0 <= _get_sample(i + 1) or _get_sample(i) >= 0 >= _get_sample(i + 1):
            diff = abs(_get_sample(i) - _get_sample(loop_start))
            if diff < best_diff:
                best_diff = diff
                best_idx = i
    loop_end = best_idx

    progress_cb(0.75, "Exporting loop audio…")
    # Convert sample indices to milliseconds
    loop_start_ms = int(loop_start / sample_rate * 1000)
    loop_end_ms = int(loop_end / sample_rate * 1000)
    loop_audio = audio[loop_start_ms:loop_end_ms]
    loop_audio_path = Path(output_dir) / f"loop.{ext}"
    loop_audio.export(str(loop_audio_path), format=ext)

    progress_cb(0.9, "Saving loop points JSON…")
    loop_data = {
        "loop_start_sample": int(loop_start),
        "loop_end_sample": int(loop_end),
        "loop_start_ms": loop_start_ms,
        "loop_end_ms": loop_end_ms,
        "sample_rate": sample_rate,
        "channels": channels,
        "total_samples": n,
    }
    json_path = Path(output_dir) / "loop_points.json"
    with open(json_path, "w") as f:
        json.dump(loop_data, f, indent=2)

    progress_cb(1.0, "Loop optimization complete")
    return {
        "files": [str(loop_audio_path), str(json_path)],
        "metadata": {
            "input": input_path,
            "loop_start_sample": int(loop_start),
            "loop_end_sample": int(loop_end),
            "loop_duration_ms": loop_end_ms - loop_start_ms,
            "sample_rate": sample_rate,
        },
    }
