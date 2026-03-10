"""Handler for visual.mesh.scale — scale a mesh.

Supports a direct scale factor or unit conversion (e.g. mm → m).

Params:
    input      (str):   path to mesh file
    scale      (float): uniform scale factor (default 1.0)
    units_from (str):   source unit (mm|cm|m|km|in|ft)  — optional
    units_to   (str):   target unit (mm|cm|m|km|in|ft)  — optional
"""
from __future__ import annotations

try:
    import trimesh  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False

_UNITS_TO_METERS = {
    "mm": 0.001,
    "cm": 0.01,
    "m": 1.0,
    "km": 1000.0,
    "in": 0.0254,
    "ft": 0.3048,
}


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Scale a mesh by a factor or between unit systems."""
    if not _AVAILABLE:
        raise RuntimeError("trimesh is not installed. Run: pip install trimesh")

    import trimesh as tm
    from pathlib import Path

    input_path = params.get("input", "")
    if not Path(input_path).exists():
        raise ValueError(f"Input file not found: {input_path}")

    units_from = params.get("units_from")
    units_to = params.get("units_to")

    if units_from and units_to:
        if units_from not in _UNITS_TO_METERS:
            raise ValueError(f"Unknown units_from: {units_from}")
        if units_to not in _UNITS_TO_METERS:
            raise ValueError(f"Unknown units_to: {units_to}")
        scale_factor = _UNITS_TO_METERS[units_from] / _UNITS_TO_METERS[units_to]
    else:
        scale_factor = float(params.get("scale", 1.0))

    progress_cb(0.0, "Loading mesh")
    mesh = tm.load(str(input_path), force="mesh")

    progress_cb(0.5, f"Applying scale {scale_factor}")
    mesh.apply_scale(scale_factor)

    progress_cb(0.8, "Exporting")
    out_path = Path(output_dir) / "scaled.glb"
    mesh.export(str(out_path))

    progress_cb(1.0, "Done")
    return {
        "files": [str(out_path)],
        "metadata": {
            "scale_factor": scale_factor,
            "units_from": units_from,
            "units_to": units_to,
        },
    }
