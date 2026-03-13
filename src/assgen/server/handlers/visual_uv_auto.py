"""visual.uv.auto — algorithmic UV unwrapping via xatlas.

Unwraps the input mesh and writes a new GLB with UV coordinates baked in.
Falls back to trimesh's built-in planar UV if xatlas is not installed.

  pip install xatlas trimesh[easy]
"""

try:
    import xatlas  # type: ignore[import]
    _XATLAS_AVAILABLE = True
except ImportError:
    _XATLAS_AVAILABLE = False


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """UV-unwrap a mesh and return the result as a GLB file."""
    import numpy as np
    import trimesh
    from pathlib import Path

    mesh_exts = {".glb", ".obj", ".fbx", ".ply", ".gltf"}
    input_file = params.get("input")
    if not input_file:
        upstream = params.get("upstream_files", [])
        input_file = next((f for f in upstream if Path(f).suffix.lower() in mesh_exts), None)
    if not input_file:
        raise ValueError("'input' param or upstream mesh file is required")
    input_path = Path(input_file)
    if not input_path.exists():
        raise ValueError(f"Input file not found: {input_path}")

    padding = int(params.get("padding", 2))
    resolution = int(params.get("resolution", 1024))

    progress_cb(0.1, "Loading mesh…")
    scene_or_mesh = trimesh.load(str(input_path), force="mesh")

    if isinstance(scene_or_mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(
            [g for g in scene_or_mesh.geometry.values() if isinstance(g, trimesh.Trimesh)]
        )
    else:
        mesh = scene_or_mesh

    if not isinstance(mesh, trimesh.Trimesh):
        raise ValueError("Could not load a valid triangle mesh from the input file")

    vertices = np.array(mesh.vertices, dtype=np.float32)
    faces = np.array(mesh.faces, dtype=np.uint32)

    progress_cb(0.3, "Unwrapping UVs…")

    if _XATLAS_AVAILABLE:
        vmapping, indices, uvs = xatlas.parametrize(vertices, faces)
        new_vertices = vertices[vmapping]
        new_faces = indices.reshape(-1, 3)
        uv_coords = uvs
        method = "xatlas"
    else:
        # Trimesh fallback: simple spherical projection
        import warnings
        warnings.warn("xatlas not installed — using spherical UV fallback. pip install xatlas for better results.")
        center = vertices.mean(axis=0)
        vn = vertices - center
        norms = np.linalg.norm(vn, axis=1, keepdims=True) + 1e-8
        vn = vn / norms
        u = 0.5 + np.arctan2(vn[:, 2], vn[:, 0]) / (2 * np.pi)
        v = 0.5 - np.arcsin(np.clip(vn[:, 1], -1, 1)) / np.pi
        uv_coords = np.stack([u, v], axis=1).astype(np.float32)
        new_vertices = vertices
        new_faces = faces
        method = "spherical-fallback"

    progress_cb(0.7, "Building output mesh…")

    out_mesh = trimesh.Trimesh(
        vertices=new_vertices,
        faces=new_faces,
        process=False,
    )
    # Attach UVs as a TextureVisuals
    material = trimesh.visual.material.PBRMaterial()
    out_mesh.visual = trimesh.visual.TextureVisuals(uv=uv_coords, material=material)

    out_path = Path(output_dir) / "unwrapped.glb"
    progress_cb(0.9, "Exporting GLB…")
    out_mesh.export(str(out_path))

    return {
        "files": [str(out_path)],
        "metadata": {
            "method": method,
            "vertex_count": len(new_vertices),
            "face_count": len(new_faces),
            "resolution_hint": resolution,
            "padding": padding,
        },
    }
