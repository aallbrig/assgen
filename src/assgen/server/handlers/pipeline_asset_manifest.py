"""Handler for pipeline.asset.manifest — walk a directory and produce a manifest.

Scans a directory recursively and outputs a JSON manifest with per-file
metadata: path, size, SHA-256 hash, type category, and image dimensions.

Params:
    directory (str): root directory to scan
"""
from __future__ import annotations

_AVAILABLE = True  # pure Python stdlib only


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Generate a file manifest for an asset directory."""
    import hashlib
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
            return "texture"
        if ext in _MESH_EXTS:
            return "mesh"
        if ext in _AUDIO_EXTS:
            return "audio"
        return "other"

    all_files = [f for f in dir_path.rglob("*") if f.is_file()]
    progress_cb(0.0, f"Scanning {len(all_files)} files")

    entries: list[dict] = []
    for i, f in enumerate(all_files):
        data = f.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        entry: dict = {
            "path": str(f.relative_to(dir_path)),
            "size_bytes": len(data),
            "sha256": sha,
            "type": file_type(f),
        }
        # Image dimensions
        if entry["type"] == "texture":
            try:
                from PIL import Image
                img = Image.open(str(f))
                entry["width"] = img.width
                entry["height"] = img.height
            except Exception:
                pass
        entries.append(entry)
        if (i + 1) % 10 == 0:
            progress_cb(0.1 + 0.8 * (i + 1) / len(all_files), "")

    manifest = {"directory": str(dir_path), "file_count": len(entries), "files": entries}
    out_path = Path(output_dir) / "manifest.json"
    out_path.write_text(json.dumps(manifest, indent=2))

    progress_cb(1.0, "Done")
    return {
        "files": [str(out_path)],
        "metadata": {"file_count": len(entries), "directory": str(dir_path)},
    }
