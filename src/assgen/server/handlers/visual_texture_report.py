"""Handler for visual.texture.report — texture memory/format/dims report.

Scans one or more images (or a directory) and produces a JSON report
with per-file format, dimensions, channel count, and memory estimate.

Params:
    inputs    (list[str]): explicit list of image paths
    directory (str):       directory to scan (used if 'inputs' not provided)
"""
from __future__ import annotations

try:
    from PIL import Image  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tga", ".webp", ".bmp", ".tiff", ".exr"}


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Generate a texture report (format, dimensions, estimated GPU memory)."""
    if not _AVAILABLE:
        raise RuntimeError("Pillow is not installed. Run: pip install Pillow")

    import json
    from pathlib import Path
    from PIL import Image

    inputs: list[str] = params.get("inputs", [])
    directory: str | None = params.get("directory")

    if not inputs and not directory:
        raise ValueError("Provide 'inputs' (list of paths) or 'directory'")

    paths: list[Path] = [Path(p) for p in inputs]
    if directory:
        dir_path = Path(directory)
        if not dir_path.is_dir():
            raise ValueError(f"Directory not found: {directory}")
        for ext in _IMAGE_EXTS:
            paths.extend(dir_path.rglob(f"*{ext}"))
            paths.extend(dir_path.rglob(f"*{ext.upper()}"))

    if not paths:
        raise ValueError("No image files found")

    progress_cb(0.0, f"Reporting on {len(paths)} images")
    entries: list[dict] = []
    total_bytes = 0

    for i, p in enumerate(paths):
        if not p.exists():
            entries.append({"path": str(p), "error": "file not found"})
            continue
        try:
            img = Image.open(str(p))
            w, h = img.size
            mode = img.mode
            channels = len(img.getbands())
            # Uncompressed memory estimate: w × h × channels × 1 byte (8-bit per channel)
            mem_bytes = w * h * channels
            disk_bytes = p.stat().st_size
            entry = {
                "path": str(p),
                "format": img.format or p.suffix.lstrip(".").upper(),
                "mode": mode,
                "width": w,
                "height": h,
                "channels": channels,
                "disk_bytes": disk_bytes,
                "disk_kb": round(disk_bytes / 1024, 1),
                "uncompressed_memory_bytes": mem_bytes,
                "uncompressed_memory_mb": round(mem_bytes / (1024 * 1024), 2),
                "is_power_of_2": (w & (w - 1) == 0) and (h & (h - 1) == 0),
            }
            total_bytes += mem_bytes
            entries.append(entry)
        except Exception as exc:
            entries.append({"path": str(p), "error": str(exc)})

        progress_cb(0.1 + 0.8 * (i + 1) / len(paths), f"Processed {i + 1}/{len(paths)}")

    report = {
        "file_count": len(entries),
        "total_uncompressed_memory_mb": round(total_bytes / (1024 * 1024), 2),
        "files": entries,
    }

    progress_cb(0.95, "Saving report")
    out_path = Path(output_dir) / "texture_report.json"
    out_path.write_text(json.dumps(report, indent=2))

    progress_cb(1.0, "Done")
    return {
        "files": [str(out_path)],
        "metadata": {
            "file_count": len(entries),
            "total_uncompressed_memory_mb": report["total_uncompressed_memory_mb"],
        },
    }
