"""Handler for visual.mesh.validate — mesh integrity report.

Checks manifold-ness, winding consistency, non-manifold edges, and
duplicate vertices.  Outputs a JSON report.

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
    """Validate a mesh and write a JSON report."""
    if not _AVAILABLE:
        raise RuntimeError("trimesh is not installed. Run: pip install trimesh")

    import json
    import numpy as np
    import trimesh as tm
    from pathlib import Path

    input_path = params.get("input", "")
    if not Path(input_path).exists():
        raise ValueError(f"Input file not found: {input_path}")

    progress_cb(0.0, "Loading mesh")
    mesh = tm.load(str(input_path), force="mesh")

    progress_cb(0.3, "Checking topology")
    is_watertight = bool(mesh.is_watertight)
    is_winding_consistent = bool(mesh.is_winding_consistent)

    progress_cb(0.5, "Finding non-manifold edges")
    try:
        nm_edges = mesh.as_open3d.get_non_manifold_edges() if hasattr(mesh, "as_open3d") else []
        non_manifold_edge_count = len(nm_edges)
    except Exception:
        # Fallback: edges referenced by != 2 faces are non-manifold
        from trimesh import graph as tg
        try:
            nm_edge_arr = tg.nonmanifold_edges(mesh)
            non_manifold_edge_count = int(len(nm_edge_arr))
        except Exception:
            non_manifold_edge_count = -1

    progress_cb(0.7, "Finding duplicate vertices")
    verts = mesh.vertices
    _, inverse = np.unique(np.round(verts, decimals=8), axis=0, return_inverse=True)
    unique_count = int(np.unique(inverse).shape[0])
    duplicate_vertex_count = int(len(verts) - unique_count)

    report = {
        "input": str(input_path),
        "vertex_count": int(len(mesh.vertices)),
        "face_count": int(len(mesh.faces)),
        "is_watertight": is_watertight,
        "is_winding_consistent": is_winding_consistent,
        "non_manifold_edge_count": non_manifold_edge_count,
        "duplicate_vertex_count": duplicate_vertex_count,
    }

    progress_cb(0.9, "Saving report")
    out_path = Path(output_dir) / "validation_report.json"
    out_path.write_text(json.dumps(report, indent=2))

    progress_cb(1.0, "Done")
    return {
        "files": [str(out_path)],
        "metadata": {
            "is_watertight": is_watertight,
            "is_winding_consistent": is_winding_consistent,
            "non_manifold_edge_count": non_manifold_edge_count,
            "duplicate_vertex_count": duplicate_vertex_count,
            "vertex_count": report["vertex_count"],
            "face_count": report["face_count"],
        },
    }
