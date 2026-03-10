"""Handler for visual.mesh.merge — combine multiple meshes into one.

Params:
    inputs (list[str]): paths to mesh files
    format (str):       output format (default "glb")
"""
from __future__ import annotations

try:
    import trimesh  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Merge multiple meshes into a single exported file."""
    if not _AVAILABLE:
        raise RuntimeError("trimesh is not installed. Run: pip install trimesh")

    import trimesh as tm
    from pathlib import Path

    inputs = params.get("inputs", [])
    fmt = params.get("format", "glb").lower().lstrip(".")

    if not inputs:
        raise ValueError("No input files provided")
    for p in inputs:
        if not Path(p).exists():
            raise ValueError(f"Input file not found: {p}")

    progress_cb(0.0, "Loading meshes")
    meshes = []
    for i, p in enumerate(inputs):
        progress_cb(i / len(inputs) * 0.6, f"Loading {Path(p).name}")
        meshes.append(tm.load(str(p), force="mesh"))

    progress_cb(0.7, "Merging meshes")
    merged = tm.util.concatenate(meshes)

    progress_cb(0.9, f"Exporting as {fmt}")
    out_path = Path(output_dir) / f"merged.{fmt}"
    merged.export(str(out_path))

    progress_cb(1.0, "Done")
    return {
        "files": [str(out_path)],
        "metadata": {
            "mesh_count": len(meshes),
            "format": fmt,
            "vertex_count": int(len(merged.vertices)),
            "face_count": int(len(merged.faces)),
        },
    }
