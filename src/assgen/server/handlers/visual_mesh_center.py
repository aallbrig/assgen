"""Handler for visual.mesh.center — reposition mesh pivot to origin.

Params:
    input (str): path to mesh file
    mode  (str): "bbox" (default) or "origin"
               - "bbox"   → translate so bounding-box center is at origin
               - "origin" → translate so centroid is at origin
"""
from __future__ import annotations

try:
    import trimesh  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Center a mesh at the world origin."""
    if not _AVAILABLE:
        raise RuntimeError("trimesh is not installed. Run: pip install trimesh")

    from pathlib import Path

    import trimesh as tm

    input_path = params.get("input", "")
    mode = params.get("mode", "bbox")
    if not Path(input_path).exists():
        raise ValueError(f"Input file not found: {input_path}")

    progress_cb(0.0, "Loading mesh")
    mesh = tm.load(str(input_path), force="mesh")

    progress_cb(0.4, f"Centering (mode={mode})")
    if mode == "bbox":
        translation = -mesh.bounding_box.centroid
    else:
        translation = -mesh.centroid

    mesh.apply_translation(translation)

    progress_cb(0.8, "Exporting")
    out_path = Path(output_dir) / "centered.glb"
    mesh.export(str(out_path))

    progress_cb(1.0, "Done")
    return {
        "files": [str(out_path)],
        "metadata": {
            "mode": mode,
            "translation_applied": translation.tolist(),
        },
    }
