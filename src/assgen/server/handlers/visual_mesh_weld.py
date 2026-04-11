"""Handler for visual.mesh.weld — merge near-duplicate vertices.

Params:
    input     (str):   path to mesh file
    threshold (float): merge tolerance (default 1e-5)
"""
from __future__ import annotations

try:
    import trimesh  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Weld near-duplicate vertices within the given tolerance."""
    if not _AVAILABLE:
        raise RuntimeError("trimesh is not installed. Run: pip install trimesh")

    from pathlib import Path

    import trimesh as tm

    input_path = params.get("input", "")
    threshold = float(params.get("threshold", 1e-5))
    if not Path(input_path).exists():
        raise ValueError(f"Input file not found: {input_path}")

    progress_cb(0.0, "Loading mesh")
    mesh = tm.load(str(input_path), force="mesh")
    verts_before = int(len(mesh.vertices))

    progress_cb(0.4, "Merging vertices")
    try:
        mesh.merge_vertices(merge_tolerance=threshold)
    except TypeError:
        # Older trimesh versions don't accept merge_tolerance
        mesh.merge_vertices()

    verts_after = int(len(mesh.vertices))

    progress_cb(0.8, "Exporting")
    out_path = Path(output_dir) / "welded.glb"
    mesh.export(str(out_path))

    progress_cb(1.0, "Done")
    return {
        "files": [str(out_path)],
        "metadata": {
            "vertices_before": verts_before,
            "vertices_after": verts_after,
            "vertices_removed": verts_before - verts_after,
            "threshold": threshold,
        },
    }
