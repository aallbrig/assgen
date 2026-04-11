"""Handler for audio.process.waveform — generate a waveform PNG preview.

Reads raw sample data from an audio file via pydub and draws a waveform
image using only standard library + numpy + Pillow.

Params:
    input  (str): audio file path
    width  (int): output image width in pixels (default 1200)
    height (int): output image height in pixels (default 200)
    color  (str): hex colour for waveform, e.g. "#00ff88" (default "#00ff88")
"""
from __future__ import annotations

try:
    from pydub import AudioSegment  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Generate a waveform PNG preview of an audio file."""
    if not _AVAILABLE:
        raise RuntimeError("pydub is not installed. Run: pip install pydub")

    import os
    from pathlib import Path

    import numpy as np
    from PIL import Image, ImageDraw
    from pydub import AudioSegment

    input_path = params.get("input")
    if not input_path or not os.path.exists(input_path):
        raise ValueError(f"Input file not found: {input_path}")

    width: int = int(params.get("width", 1200))
    height: int = int(params.get("height", 200))
    color_hex: str = str(params.get("color", "#00ff88")).strip()

    # Parse hex colour
    color_hex = color_hex.lstrip("#")
    if len(color_hex) == 3:
        color_hex = "".join(c * 2 for c in color_hex)
    try:
        r, g, b = int(color_hex[0:2], 16), int(color_hex[2:4], 16), int(color_hex[4:6], 16)
        wave_color = (r, g, b, 255)
    except Exception:
        wave_color = (0, 255, 136, 255)

    progress_cb(0.0, "Loading audio")
    audio = AudioSegment.from_file(input_path)
    if audio.channels > 1:
        audio = audio.set_channels(1)

    samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
    max_val = float(2 ** (audio.sample_width * 8 - 1))
    samples /= max_val  # normalise to [-1, 1]

    progress_cb(0.4, "Computing waveform")
    chunk_size = max(1, len(samples) // width)
    n_chunks = min(width, len(samples))
    peak_pos = np.zeros(n_chunks, dtype=np.float32)
    peak_neg = np.zeros(n_chunks, dtype=np.float32)

    for i in range(n_chunks):
        chunk = samples[i * chunk_size: (i + 1) * chunk_size]
        if len(chunk) > 0:
            peak_pos[i] = float(np.max(chunk))
            peak_neg[i] = float(np.min(chunk))

    progress_cb(0.7, "Drawing waveform image")
    img = Image.new("RGBA", (width, height), (20, 20, 20, 255))
    draw = ImageDraw.Draw(img)
    mid_y = height // 2

    for x in range(n_chunks):
        top = mid_y - int(peak_pos[x] * mid_y)
        bot = mid_y - int(peak_neg[x] * mid_y)
        draw.line([(x, top), (x, bot)], fill=wave_color, width=1)

    progress_cb(0.9, "Saving")
    stem = Path(input_path).stem
    out_path = Path(output_dir) / f"{stem}_waveform.png"
    img.save(str(out_path))

    progress_cb(1.0, "Done")
    return {
        "files": [str(out_path)],
        "metadata": {
            "width": width,
            "height": height,
            "duration_ms": len(audio),
            "sample_rate": audio.frame_rate,
        },
    }
