"""visual.texture.bake — software ambient-occlusion and lightmap baking.

Generates AO / lightmap / cavity textures from a mesh without a GPU rasteriser.
Uses a ray-sampling approach over the mesh surface UV space via trimesh + numpy.

  pip install trimesh numpy Pillow

Params:
    input        (str):  path to source mesh (must have UVs for best results)
    bake_type    (str):  ao | cavity | lightmap (default: ao)
    width        (int):  output texture width in pixels (default: 1024)
    height       (int):  output texture height in pixels (default: 1024)
    samples      (int):  AO ray samples per texel (default: 64)
    bias         (float):ray origin offset to avoid self-intersection (default: 0.001)
    output       (str):  output filename (default: <stem>_<bake_type>.png)
"""
from __future__ import annotations

try:
    import trimesh  # noqa: F401
    import numpy as np  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Bake AO/lightmap/cavity texture from a mesh."""
    if not _AVAILABLE:
        raise RuntimeError(
            "trimesh and numpy are required. Run: pip install trimesh numpy Pillow"
        )

    import trimesh as tm
    from pathlib import Path
    from PIL import Image

    input_path = params.get("input", "")
    if not input_path or not Path(input_path).exists():
        raise ValueError(f"Input file not found: {input_path!r}")

    bake_type = (params.get("bake_type") or "ao").lower()
    width = int(params.get("width", 1024))
    height = int(params.get("height", 1024))
    samples = int(params.get("samples", 64))
    bias = float(params.get("bias", 1e-3))

    stem = Path(input_path).stem
    out_name = params.get("output") or f"{stem}_{bake_type}.png"
    out_path = Path(output_dir) / out_name

    progress_cb(0.0, "Loading mesh…")
    scene = tm.load(str(input_path))
    if isinstance(scene, tm.Scene):
        mesh = tm.util.concatenate(list(scene.geometry.values()))
    else:
        mesh = scene

    if not isinstance(mesh, tm.Trimesh):
        raise ValueError("Could not extract a triangle mesh from the input file.")

    progress_cb(0.15, f"Baking {bake_type} ({width}×{height}, {samples} samples)…")

    if bake_type == "cavity":
        texture = _bake_cavity(mesh, width, height, progress_cb)
    elif bake_type == "lightmap":
        texture = _bake_lightmap(mesh, width, height, samples, bias, progress_cb)
    else:
        texture = _bake_ao(mesh, width, height, samples, bias, progress_cb)

    progress_cb(0.95, "Saving texture…")
    img = Image.fromarray(texture, mode="L")
    img.save(str(out_path))
    progress_cb(1.0, "Done")

    return {
        "files": [out_name],
        "metadata": {"bake_type": bake_type, "width": width, "height": height},
    }


# ---------------------------------------------------------------------------
# Bake implementations
# ---------------------------------------------------------------------------

def _face_normals_and_centers(mesh) -> tuple:
    centers = mesh.triangles_center          # (F, 3)
    normals = mesh.face_normals              # (F, 3)
    return centers, normals


def _bake_ao(mesh, width, height, samples, bias, progress_cb) -> "np.ndarray":
    """Per-face ambient occlusion, projected to a solid-color UV texture."""
    import numpy as np
    from trimesh.ray.ray_triangle import RayMeshIntersector

    centers, normals = _face_normals_and_centers(mesh)
    intersector = RayMeshIntersector(mesh)

    n_faces = len(centers)
    ao_per_face = np.zeros(n_faces, dtype=np.float32)

    rng = np.random.default_rng(42)
    for i in range(n_faces):
        if i % max(1, n_faces // 20) == 0:
            progress_cb(0.15 + 0.75 * (i / n_faces), f"AO bake {i}/{n_faces}…")
        n = normals[i]
        origin = centers[i] + n * bias
        # Sample hemisphere around the face normal
        raw = rng.standard_normal((samples, 3)).astype(np.float32)
        raw /= (np.linalg.norm(raw, axis=1, keepdims=True) + 1e-8)
        # Keep directions in the upper hemisphere
        dot = raw @ n
        raw[dot < 0] *= -1
        hits = intersector.intersects_any(
            ray_origins=np.tile(origin, (samples, 1)),
            ray_directions=raw,
        )
        ao_per_face[i] = 1.0 - hits.sum() / samples

    return _project_face_values_to_image(mesh, ao_per_face, width, height)


def _bake_cavity(mesh, width, height, progress_cb) -> "np.ndarray":
    """Per-vertex curvature (cavity) projected to texture."""
    import numpy as np
    progress_cb(0.2, "Computing discrete curvature…")
    try:
        curv = tm_discrete_mean_curvature(mesh)
    except Exception:
        curv = np.zeros(len(mesh.vertices))
    # Map to [0,1]: negative curvature (concave) → dark
    curv_norm = np.clip(-curv, 0, None)
    if curv_norm.max() > 0:
        curv_norm /= curv_norm.max()
    # Average per face
    face_vals = curv_norm[mesh.faces].mean(axis=1)
    return _project_face_values_to_image(mesh, 1.0 - face_vals, width, height)


def _bake_lightmap(mesh, width, height, samples, bias, progress_cb) -> "np.ndarray":
    """Simple directional lightmap (single overhead light)."""
    import numpy as np
    progress_cb(0.2, "Computing simple lightmap…")
    light_dir = np.array([0.3, 0.8, 0.5], dtype=np.float32)
    light_dir /= np.linalg.norm(light_dir)
    face_normals = mesh.face_normals
    diffuse = np.clip(face_normals @ light_dir, 0, 1).astype(np.float32)
    # Slight ambient
    diffuse = 0.15 + 0.85 * diffuse
    return _project_face_values_to_image(mesh, diffuse, width, height)


def tm_discrete_mean_curvature(mesh) -> "np.ndarray":
    """Estimate per-vertex mean curvature via discrete Laplacian."""
    import numpy as np
    verts = mesh.vertices
    n = len(verts)
    laplacian = np.zeros(n, dtype=np.float64)
    count = np.zeros(n, dtype=np.float64)
    for edge in mesh.edges_unique:
        i, j = edge
        diff = np.linalg.norm(verts[i] - verts[j])
        laplacian[i] += diff
        laplacian[j] += diff
        count[i] += 1
        count[j] += 1
    count = np.maximum(count, 1)
    return laplacian / count


def _project_face_values_to_image(mesh, face_values, width, height) -> "np.ndarray":
    """Rasterise per-face scalar values into a UV-space image."""
    import numpy as np

    img = np.ones((height, width), dtype=np.float32) * 0.5  # default mid-grey

    # Use UV coords if available, else fall back to spherical projection
    uvs = _get_uvs(mesh)
    if uvs is None:
        # Spherical projection fallback
        norms = mesh.face_normals
        u = (np.arctan2(norms[:, 0], norms[:, 2]) / (2 * np.pi) + 0.5)
        v = (np.arcsin(np.clip(norms[:, 1], -1, 1)) / np.pi + 0.5)
        px = (u * (width - 1)).astype(int)
        py = ((1.0 - v) * (height - 1)).astype(int)
        for fi in range(len(face_values)):
            img[py[fi], px[fi]] = face_values[fi]
    else:
        # Per-face UV centroid rasterisation
        face_uvs = uvs.reshape(-1, 3, 2) if uvs.shape[0] == len(mesh.faces) * 3 else None
        if face_uvs is not None:
            centroids = face_uvs.mean(axis=1)  # (F, 2)
            px = (centroids[:, 0] * (width - 1)).astype(int).clip(0, width - 1)
            py = ((1.0 - centroids[:, 1]) * (height - 1)).astype(int).clip(0, height - 1)
            for fi in range(len(face_values)):
                img[py[fi], px[fi]] = face_values[fi]

    return (img * 255).clip(0, 255).astype(np.uint8)


def _get_uvs(mesh) -> "np.ndarray | None":
    """Extract per-vertex or per-face UV coordinates from a trimesh."""
    if hasattr(mesh, "visual") and hasattr(mesh.visual, "uv"):
        uv = mesh.visual.uv
        if uv is not None and len(uv) > 0:
            return uv
    return None
