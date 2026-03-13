"""scene.physics.collider — collision mesh generation.

Generates a physics collision shape from an input mesh. Supports convex hull
(single convex), approximate convex decomposition (compound), and simple
primitive fitting (box, sphere, capsule).

  pip install trimesh
  pip install coacd  # optional, for better compound convex decomposition

Params:
    input       (str): path to source mesh
    type        (str): convex | compound | box | sphere | capsule (default: convex)
    max_shapes  (int): max convex pieces for compound decomposition (default: 8)
    output      (str): output filename (default: <stem>_collider.<ext>)
    format      (str): output format (glb/obj/ply/stl, default: glb)
"""
from __future__ import annotations

try:
    import trimesh  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Generate a physics collider mesh from the input asset."""
    if not _AVAILABLE:
        raise RuntimeError("trimesh is not installed. Run: pip install trimesh")

    import numpy as np
    import trimesh as tm
    from pathlib import Path

    mesh_exts = {".glb", ".obj", ".fbx", ".ply", ".gltf"}
    input_path = params.get("input", "")
    if not input_path or not Path(input_path).is_file():
        upstream = params.get("upstream_files", [])
        input_path = next((f for f in upstream if Path(f).suffix.lower() in mesh_exts), input_path)
    if not input_path or not Path(input_path).is_file():
        raise ValueError(f"Input file not found: {input_path!r}")

    collider_type = (params.get("type") or "convex").lower()
    max_shapes = int(params.get("max_shapes", 8))
    output_fmt = (params.get("format") or "glb").lower()
    stem = Path(input_path).stem
    out_name = params.get("output") or f"{stem}_collider.{output_fmt}"
    out_path = Path(output_dir) / out_name

    progress_cb(0.0, "Loading mesh…")
    mesh = tm.load(str(input_path), force="mesh")
    progress_cb(0.2, f"Generating {collider_type} collider…")

    if collider_type == "box":
        to_origin, extents = tm.bounds.oriented_bounds(mesh)
        box = tm.creation.box(extents=extents)
        box.apply_transform(np.linalg.inv(to_origin))
        result = box

    elif collider_type == "sphere":
        center, radius = tm.nsphere.minimum_nsphere(mesh)
        result = tm.creation.icosphere(radius=float(radius))
        result.apply_translation(center)

    elif collider_type == "capsule":
        # Fit capsule along the longest axis
        obb_transform, extents = tm.bounds.oriented_bounds(mesh)
        longest_axis = int(np.argmax(extents))
        height = float(extents[longest_axis])
        radius = float(np.max(np.delete(extents, longest_axis))) / 2.0
        result = tm.creation.capsule(height=height, radius=radius)
        result.apply_transform(np.linalg.inv(obb_transform))

    elif collider_type == "compound":
        try:
            import coacd  # type: ignore[import]
            progress_cb(0.3, f"Running CoACD decomposition (max {max_shapes} shapes)…")
            parts = coacd.run_coacd(
                coacd.Mesh(mesh.vertices, mesh.faces),
                max_convex_hull=max_shapes,
            )
            meshes = [tm.Trimesh(vertices=p[0], faces=p[1]) for p in parts]
            result = tm.util.concatenate(meshes)
        except ImportError:
            # Fallback: single convex hull
            progress_cb(0.3, "coacd not installed, using single convex hull fallback…")
            result = mesh.convex_hull

    else:  # convex (default)
        result = mesh.convex_hull

    progress_cb(0.85, f"Exporting collider ({len(result.faces)} faces)…")
    result.export(str(out_path))
    progress_cb(1.0, "Done")

    return {
        "files": [out_name],
        "metadata": {
            "type": collider_type,
            "faces": len(result.faces),
            "source_faces": len(mesh.faces),
        },
    }
