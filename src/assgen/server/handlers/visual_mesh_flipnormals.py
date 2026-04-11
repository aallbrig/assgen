"""Handler for visual.mesh.flipnormals — invert face winding order.

Params:
    input (str): path to mesh file
"""
from __future__ import annotations

try:
    import trimesh  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Flip face normals by reversing winding order."""
    if not _AVAILABLE:
        raise RuntimeError("trimesh is not installed. Run: pip install trimesh")

    from pathlib import Path

    import trimesh as tm

    input_path = params.get("input", "")
    if not Path(input_path).exists():
        raise ValueError(f"Input file not found: {input_path}")

    progress_cb(0.0, "Loading mesh")
    mesh = tm.load(str(input_path), force="mesh")

    progress_cb(0.5, "Flipping normals")
    mesh.faces = mesh.faces[:, ::-1]
    mesh._cache.clear()

    progress_cb(0.8, "Exporting")
    out_path = Path(output_dir) / "flipped.glb"
    mesh.export(str(out_path))

    progress_cb(1.0, "Done")
    return {
        "files": [str(out_path)],
        "metadata": {
            "vertex_count": int(len(mesh.vertices)),
            "face_count": int(len(mesh.faces)),
        },
    }
