"""Handler for visual.sprite.pack — pack animation frames into a sprite sheet.

Arranges individual frame images into a sprite sheet grid and outputs
a manifest JSON with per-frame UV data.

Params:
    inputs (list[str]): ordered list of frame image paths
    cols   (int):       number of columns in the grid (default 4)
"""
from __future__ import annotations

try:
    from PIL import Image  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Pack animation frames into a sprite sheet + manifest."""
    if not _AVAILABLE:
        raise RuntimeError("Pillow is not installed. Run: pip install Pillow")

    import json
    import math
    from pathlib import Path
    from PIL import Image

    inputs: list[str] = params.get("inputs", [])
    if not inputs:
        raise ValueError("'inputs' must be a non-empty list of frame image paths")

    for p in inputs:
        if not Path(p).exists():
            raise ValueError(f"Frame image not found: {p}")

    cols: int = int(params.get("cols", 4))
    cols = max(1, cols)
    rows = math.ceil(len(inputs) / cols)

    progress_cb(0.0, "Loading frames")
    frames = [Image.open(p).convert("RGBA") for p in inputs]

    # All frames must be the same size; resize if needed
    frame_w, frame_h = frames[0].size
    frames = [f.resize((frame_w, frame_h), Image.LANCZOS) for f in frames]

    sheet_w = frame_w * cols
    sheet_h = frame_h * rows

    progress_cb(0.3, f"Building {cols}×{rows} sprite sheet ({sheet_w}×{sheet_h})")
    sheet = Image.new("RGBA", (sheet_w, sheet_h), (0, 0, 0, 0))

    manifest_frames: list[dict] = []
    for idx, frame in enumerate(frames):
        col = idx % cols
        row = idx // cols
        x = col * frame_w
        y = row * frame_h
        sheet.paste(frame, (x, y))
        manifest_frames.append({
            "index": idx,
            "file": Path(inputs[idx]).name,
            "x": x, "y": y,
            "w": frame_w, "h": frame_h,
            "u": x / sheet_w, "v": y / sheet_h,
            "u2": (x + frame_w) / sheet_w, "v2": (y + frame_h) / sheet_h,
        })
        progress_cb(0.3 + 0.5 * (idx + 1) / len(frames), f"Placed frame {idx + 1}/{len(frames)}")

    progress_cb(0.85, "Saving sprite sheet")
    sheet_path = Path(output_dir) / "spritesheet.png"
    manifest_path = Path(output_dir) / "manifest.json"
    sheet.save(str(sheet_path))

    manifest = {
        "frame_count": len(frames),
        "frame_width": frame_w,
        "frame_height": frame_h,
        "cols": cols,
        "rows": rows,
        "sheet_width": sheet_w,
        "sheet_height": sheet_h,
        "frames": manifest_frames,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))

    progress_cb(1.0, "Done")
    return {
        "files": [str(sheet_path), str(manifest_path)],
        "metadata": {
            "frame_count": len(frames),
            "cols": cols,
            "rows": rows,
            "sheet_size": [sheet_w, sheet_h],
        },
    }
