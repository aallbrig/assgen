"""Handler for pipeline.asset.report — size budget report grouped by asset type.

Walks a directory and produces a JSON budget report and a printed table
grouping files by type (meshes / textures / audio / other) with totals.

Params:
    directory (str): root directory to scan
"""
from __future__ import annotations

_AVAILABLE = True  # pure Python stdlib


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Generate a size-budget report for an asset directory."""
    import json
    from pathlib import Path

    directory = params.get("directory", "")
    if not directory:
        raise ValueError("'directory' parameter is required")
    dir_path = Path(directory)
    if not dir_path.is_dir():
        raise ValueError(f"Directory not found: {directory}")

    _IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tga", ".webp", ".bmp", ".tiff", ".exr", ".hdr"}
    _MESH_EXTS = {".glb", ".gltf", ".obj", ".fbx", ".ply", ".stl", ".dae"}
    _AUDIO_EXTS = {".wav", ".ogg", ".mp3", ".flac", ".aiff", ".aac"}

    def file_type(p: Path) -> str:
        ext = p.suffix.lower()
        if ext in _IMAGE_EXTS:
            return "textures"
        if ext in _MESH_EXTS:
            return "meshes"
        if ext in _AUDIO_EXTS:
            return "audio"
        return "other"

    all_files = [f for f in dir_path.rglob("*") if f.is_file()]
    progress_cb(0.0, f"Scanning {len(all_files)} files")

    groups: dict[str, list[dict]] = {
        "meshes": [],
        "textures": [],
        "audio": [],
        "other": [],
    }

    for i, f in enumerate(all_files):
        category = file_type(f)
        size_bytes = f.stat().st_size
        groups[category].append({
            "path": str(f.relative_to(dir_path)),
            "size_bytes": size_bytes,
            "size_kb": round(size_bytes / 1024, 1),
        })
        progress_cb(0.1 + 0.7 * (i + 1) / len(all_files), "")

    summary: list[dict] = []
    for cat, files in groups.items():
        total = sum(e["size_bytes"] for e in files)
        summary.append({
            "category": cat,
            "file_count": len(files),
            "total_bytes": total,
            "total_mb": round(total / (1024 * 1024), 2),
        })

    grand_total = sum(s["total_bytes"] for s in summary)

    report = {
        "directory": str(dir_path),
        "grand_total_mb": round(grand_total / (1024 * 1024), 2),
        "summary": summary,
        "detail": groups,
    }

    progress_cb(0.9, "Saving report")
    out_path = Path(output_dir) / "budget_report.json"
    out_path.write_text(json.dumps(report, indent=2))

    progress_cb(1.0, "Done")
    return {
        "files": [str(out_path)],
        "metadata": {
            "grand_total_mb": report["grand_total_mb"],
            "summary": summary,
        },
    }
