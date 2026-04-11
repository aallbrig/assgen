"""visual.model.retopo — mesh retopology via QEM decimation.

Reduces polygon count while preserving surface shape. Uses pyfqmr (fast quadric
mesh simplification) when available, falling back to trimesh's built-in simplifier.

Params:
    input          (str):  path to source mesh (glb/obj/fbx/ply/stl)
    target_faces   (int):  desired face count in the output (default 5000)
    preserve_uvs   (bool): attempt to preserve UV seams (default True)
    output         (str):  output filename (default: <stem>_retopo.<ext>)
    format         (str):  output format override (glb/obj/ply/stl)
"""
from __future__ import annotations

try:
    import trimesh  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Retopologise a mesh to a target face count via QEM decimation."""
    if not _AVAILABLE:
        raise RuntimeError("trimesh is not installed. Run: pip install trimesh")

    from pathlib import Path

    import trimesh as tm

    input_path = params.get("input", "")
    if not input_path or not Path(input_path).exists():
        raise ValueError(f"Input file not found: {input_path!r}")

    target_faces = int(params.get("target_faces", 5000))
    output_fmt = (params.get("format") or Path(input_path).suffix.lstrip(".") or "glb").lower()
    stem = Path(input_path).stem
    out_name = params.get("output") or f"{stem}_retopo.{output_fmt}"
    out_path = Path(output_dir) / out_name

    progress_cb(0.0, "Loading mesh…")
    mesh = tm.load(str(input_path), force="mesh")
    original_faces = len(mesh.faces)
    progress_cb(0.15, f"Loaded {original_faces:,} faces → targeting {target_faces:,}")

    if target_faces >= original_faces:
        # Nothing to do — copy as-is
        mesh.export(str(out_path))
        return {
            "files": [out_name],
            "metadata": {
                "original_faces": original_faces,
                "output_faces": original_faces,
                "reduction_pct": 0,
            },
        }

    try:
        import pyfqmr
        progress_cb(0.3, "Running QEM simplification (pyfqmr)…")
        simplifier = pyfqmr.Simplify()
        simplifier.setMesh(mesh.vertices, mesh.faces)
        simplifier.simplify_mesh(
            target_count=target_faces,
            aggressiveness=7,
            preserve_border=bool(params.get("preserve_uvs", True)),
            verbose=False,
        )
        verts, faces, _ = simplifier.getMesh()
        result_mesh = tm.Trimesh(vertices=verts, faces=faces, process=False)
    except ImportError:
        progress_cb(0.3, "Running QEM simplification (trimesh fallback)…")
        result_mesh = mesh.simplify_quadric_decimation(target_faces)

    progress_cb(0.85, f"Exporting {len(result_mesh.faces):,}-face mesh…")
    result_mesh.export(str(out_path))
    progress_cb(1.0, "Done")

    reduction_pct = round(100 * (1 - len(result_mesh.faces) / original_faces), 1)
    return {
        "files": [out_name],
        "metadata": {
            "original_faces": original_faces,
            "output_faces": len(result_mesh.faces),
            "reduction_pct": reduction_pct,
        },
    }
