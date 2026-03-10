"""Handler for pipeline.asset.validate — asset pipeline validation.

Checks for:
  - Textures exceeding a file-size budget
  - Meshes exceeding a vertex budget
  - Non-power-of-2 textures

Outputs:
    validation_report.json — {errors: [...], warnings: [...], checked: N}

Params:
    directory      (str):   directory to scan
    max_texture_mb (float): max texture file size in MB (default 16)
    max_mesh_verts (int):   max vertex count per mesh (default 100 000)
"""
from __future__ import annotations

_AVAILABLE = True  # PIL is optional for dimension checks


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Validate asset sizes and topology budgets."""
    import json
    from pathlib import Path

    directory = params.get("directory", "")
    if not directory:
        raise ValueError("'directory' parameter is required")
    dir_path = Path(directory)
    if not dir_path.is_dir():
        raise ValueError(f"Directory not found: {directory}")

    max_texture_mb: float = float(params.get("max_texture_mb", 16))
    max_mesh_verts: int = int(params.get("max_mesh_verts", 100_000))

    _IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tga", ".webp", ".bmp", ".tiff", ".exr"}
    _MESH_EXTS = {".glb", ".gltf", ".obj", ".ply", ".stl"}

    try:
        from PIL import Image as _PILImage
        _PIL = True
    except ImportError:
        _PIL = False

    try:
        import trimesh as _tm
        _TRIMESH = True
    except ImportError:
        _TRIMESH = False

    all_files = [f for f in dir_path.rglob("*") if f.is_file()]
    errors: list[str] = []
    warnings: list[str] = []
    checked = 0

    progress_cb(0.0, f"Checking {len(all_files)} files")

    for i, f in enumerate(all_files):
        ext = f.suffix.lower()
        rel = str(f.relative_to(dir_path))

        if ext in _IMAGE_EXTS:
            size_mb = f.stat().st_size / (1024 * 1024)
            if size_mb > max_texture_mb:
                errors.append(f"Texture too large: {rel} ({size_mb:.1f} MB > {max_texture_mb} MB)")
            if _PIL:
                try:
                    img = _PILImage.open(str(f))
                    w, h = img.size
                    if not ((w & (w - 1) == 0) and (h & (h - 1) == 0)):
                        warnings.append(f"Non-power-of-2 texture: {rel} ({w}×{h})")
                except Exception:
                    warnings.append(f"Could not open texture for dimension check: {rel}")
            checked += 1

        elif ext in _MESH_EXTS:
            if _TRIMESH:
                try:
                    mesh = _tm.load(str(f), force="mesh")
                    if hasattr(mesh, "vertices"):
                        n_verts = len(mesh.vertices)
                        if n_verts > max_mesh_verts:
                            errors.append(
                                f"High-poly mesh: {rel} ({n_verts:,} verts > {max_mesh_verts:,})"
                            )
                except Exception:
                    warnings.append(f"Could not load mesh for vertex check: {rel}")
            checked += 1

        progress_cb(0.1 + 0.8 * (i + 1) / len(all_files), "")

    report = {"errors": errors, "warnings": warnings, "checked": checked}
    out_path = Path(output_dir) / "validation_report.json"
    out_path.write_text(json.dumps(report, indent=2))

    progress_cb(1.0, "Done")
    return {
        "files": [str(out_path)],
        "metadata": {
            "error_count": len(errors),
            "warning_count": len(warnings),
            "checked": checked,
        },
    }
