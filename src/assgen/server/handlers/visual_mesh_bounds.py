"""Handler for visual.mesh.bounds — compute bounding volumes.

Outputs a JSON report with AABB, OBB, bounding sphere, and centroid.

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
    """Compute and report bounding volumes for a mesh."""
    if not _AVAILABLE:
        raise RuntimeError("trimesh is not installed. Run: pip install trimesh")

    import json
    from pathlib import Path

    import trimesh as tm

    input_path = params.get("input", "")
    if not Path(input_path).exists():
        raise ValueError(f"Input file not found: {input_path}")

    progress_cb(0.0, "Loading mesh")
    mesh = tm.load(str(input_path), force="mesh")

    progress_cb(0.3, "Computing AABB")
    aabb_min = mesh.bounds[0].tolist()
    aabb_max = mesh.bounds[1].tolist()

    progress_cb(0.5, "Computing OBB")
    obb = mesh.bounding_box_oriented
    obb_center = obb.centroid.tolist()
    obb_extents = obb.extents.tolist()
    obb_transform = obb.primitive.transform.tolist()

    progress_cb(0.7, "Computing bounding sphere")
    bsphere = mesh.bounding_sphere
    bsphere_center = bsphere.centroid.tolist()
    bsphere_radius = float(bsphere.primitive.radius)

    centroid = mesh.centroid.tolist()

    report = {
        "input": str(input_path),
        "centroid": centroid,
        "aabb": {"min": aabb_min, "max": aabb_max},
        "obb": {
            "center": obb_center,
            "extents": obb_extents,
            "transform": obb_transform,
        },
        "bounding_sphere": {
            "center": bsphere_center,
            "radius": bsphere_radius,
        },
    }

    progress_cb(0.9, "Saving report")
    out_path = Path(output_dir) / "bounds_report.json"
    out_path.write_text(json.dumps(report, indent=2))

    progress_cb(1.0, "Done")
    return {
        "files": [str(out_path)],
        "metadata": {
            "aabb_min": aabb_min,
            "aabb_max": aabb_max,
            "bounding_sphere_radius": bsphere_radius,
            "centroid": centroid,
        },
    }
