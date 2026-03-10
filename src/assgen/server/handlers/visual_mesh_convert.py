"""Handler for visual.mesh.convert — mesh format conversion.

Converts between glb, obj, ply, stl and other trimesh-supported formats.

Params:
    input  (str): path to source mesh
    format (str): target format (default "glb")
"""
from __future__ import annotations

try:
    import trimesh  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Convert a mesh to the requested format."""
    if not _AVAILABLE:
        raise RuntimeError("trimesh is not installed. Run: pip install trimesh")

    import trimesh as tm
    from pathlib import Path

    input_path = params.get("input", "")
    fmt = params.get("format", "glb").lower().lstrip(".")
    if not Path(input_path).exists():
        raise ValueError(f"Input file not found: {input_path}")

    original_format = Path(input_path).suffix.lstrip(".").lower()

    progress_cb(0.0, "Loading mesh")
    mesh = tm.load(str(input_path))

    progress_cb(0.5, f"Exporting as {fmt}")
    out_path = Path(output_dir) / f"output.{fmt}"
    mesh.export(str(out_path))

    progress_cb(1.0, "Done")
    return {
        "files": [str(out_path)],
        "metadata": {
            "format": fmt,
            "original_format": original_format,
        },
    }
