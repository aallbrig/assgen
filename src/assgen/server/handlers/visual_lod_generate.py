"""Handler for visual.lod.generate — LOD mesh generation via QEM decimation.

Uses pyfqmr (Python bindings for QEM / fast quadric mesh simplification).
Falls back to trimesh built-in decimation if pyfqmr is not installed.

Params:
    input         (str): path to source mesh
    num_lods      (int): number of LOD levels (default 3)
    min_poly_count(int): minimum face count for the most-reduced LOD (default 100)
"""
from __future__ import annotations

try:
    import trimesh  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Generate N LOD meshes via QEM decimation."""
    if not _AVAILABLE:
        raise RuntimeError("trimesh is not installed. Run: pip install trimesh")

    from pathlib import Path

    import trimesh as tm

    mesh_exts = {".glb", ".obj", ".fbx", ".ply", ".gltf"}
    input_path = params.get("input", "")
    if not input_path or not Path(input_path).is_file():
        upstream = params.get("upstream_files", [])
        input_path = next((f for f in upstream if Path(f).suffix.lower() in mesh_exts), input_path)
    if not input_path or not Path(input_path).is_file():
        raise ValueError(f"Input file not found: {input_path}")

    num_lods: int = int(params.get("num_lods", 3))
    min_poly_count: int = int(params.get("min_poly_count", 100))

    progress_cb(0.0, "Loading mesh")
    mesh = tm.load(str(input_path), force="mesh")
    original_face_count = len(mesh.faces)

    try:
        import pyfqmr
        _PYFQMR = True
    except ImportError:
        _PYFQMR = False

    out_files = []
    metadata_lods = []

    for i in range(num_lods):
        fraction = (i + 1) / num_lods
        # LOD0 is full resolution, LOD(n-1) is most reduced
        if i == 0:
            lod_mesh = mesh
        else:
            # Exponentially reduce face count
            reduction_ratio = fraction
            target_faces = max(min_poly_count, int(original_face_count * (1.0 - reduction_ratio)))
            progress_cb(fraction * 0.8, f"Generating LOD{i} (target {target_faces} faces)…")

            if _PYFQMR:
                simplifier = pyfqmr.Simplify()
                simplifier.setMesh(mesh.vertices, mesh.faces)
                simplifier.simplify_mesh(target_count=target_faces, aggressiveness=7, verbose=False)
                verts, faces, _ = simplifier.getMesh()
                lod_mesh = tm.Trimesh(vertices=verts, faces=faces, process=False)
            else:
                target_reduction = max(0.0, min(0.99, 1.0 - target_faces / max(original_face_count, 1)))
                lod_mesh = mesh.simplify_quadric_decimation(target_reduction)

        out_path = Path(output_dir) / f"LOD{i}.glb"
        lod_mesh.export(str(out_path))
        out_files.append(str(out_path))
        metadata_lods.append({
            "level": i,
            "face_count": int(len(lod_mesh.faces)),
            "vertex_count": int(len(lod_mesh.vertices)),
            "file": f"LOD{i}.glb",
        })

    progress_cb(1.0, "Done")
    return {
        "files": out_files,
        "metadata": {
            "num_lods": num_lods,
            "original_face_count": original_face_count,
            "lods": metadata_lods,
            "backend": "pyfqmr" if _PYFQMR else "trimesh",
        },
    }
