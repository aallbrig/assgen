"""pipeline.integrate.export — game engine asset exporter.

Converts meshes + textures into the canonical folder structure and settings
expected by Unreal Engine 5, Godot 4, or Unity (URP/HDRP).

  pip install trimesh Pillow

Params:
    input        (str | list[str]): mesh file(s) to export
    textures     (list[str]):        optional texture files to copy/rename
    engine       (str): unreal | godot | unity  (default: godot)
    format       (str): mesh format override — glb/fbx/obj (default: engine default)
    asset_name   (str): base name for the exported asset (default: input stem)
    output_dir   (str): sub-folder inside job output dir (default: engine name)
"""
from __future__ import annotations

try:
    import trimesh  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False

# Engine defaults
_ENGINE_DEFAULTS = {
    "unreal":  {"format": "fbx", "mesh_dir": "Content/Meshes",   "tex_dir": "Content/Textures"},
    "godot":   {"format": "glb", "mesh_dir": "assets/meshes",    "tex_dir": "assets/textures"},
    "unity":   {"format": "fbx", "mesh_dir": "Assets/Models",    "tex_dir": "Assets/Textures"},
}

# Godot .import sidecar template
_GODOT_IMPORT_TPL = """\
[remap]
importer="scene"
importer_version=1
type="PackedScene"
uid="uid://{uid}"
path=".godot/imported/{name}.glb-{uid}.scn"

[deps]
source_file="res://{src_path}"
dest_files=[".godot/imported/{name}.glb-{uid}.scn"]

[params]
nodes/root_type="Node3D"
nodes/root_name="Scene Root"
meshes/ensure_tangents=true
meshes/generate_lods=true
skins/use_named_skins=true
"""


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Export assets to a game engine project layout."""
    if not _AVAILABLE:
        raise RuntimeError("trimesh is not installed. Run: pip install trimesh")

    import shutil
    import uuid
    from pathlib import Path

    import trimesh as tm

    engine = (params.get("engine") or "godot").lower()
    if engine not in _ENGINE_DEFAULTS:
        raise ValueError(f"Unknown engine {engine!r}. Choose: unreal, godot, unity")

    defaults = _ENGINE_DEFAULTS[engine]
    fmt = (params.get("format") or defaults["format"]).lower().lstrip(".")

    # Normalise input to a list — also accept upstream_files from prior steps
    raw_input = params.get("input") or params.get("inputs") or []
    if isinstance(raw_input, str):
        raw_input = [raw_input]
    if not raw_input:
        upstream = params.get("upstream_files", [])
        mesh_exts = {".glb", ".obj", ".fbx", ".ply", ".gltf", ".bvh", ".png", ".jpg"}
        raw_input = [f for f in upstream if Path(f).suffix.lower() in mesh_exts]
    if not raw_input:
        raise ValueError("'input' param or upstream files are required")

    textures: list[str] = params.get("textures") or []
    if isinstance(textures, str):
        textures = [textures]

    out_root = Path(output_dir)
    mesh_out = out_root / defaults["mesh_dir"]
    tex_out = out_root / defaults["tex_dir"]
    mesh_out.mkdir(parents=True, exist_ok=True)
    tex_out.mkdir(parents=True, exist_ok=True)

    out_files: list[str] = []
    total = len(raw_input) + len(textures)
    done = 0

    # Export meshes
    for src in raw_input:
        src_path = Path(src)
        if not src_path.exists():
            raise ValueError(f"Input mesh not found: {src!r}")

        asset_name = params.get("asset_name") or src_path.stem
        dest_name = f"{asset_name}.{fmt}"
        dest = mesh_out / dest_name

        progress_cb(done / total * 0.8, f"Exporting {dest_name}…")
        if src_path.suffix.lower().lstrip(".") == fmt:
            shutil.copy2(src_path, dest)
        else:
            mesh = tm.load(str(src_path), force="mesh")
            _TRIMESH_FORMATS = {"glb", "gltf", "obj", "ply", "stl", "off"}
            if fmt not in _TRIMESH_FORMATS:
                # Fall back to GLB when requested format (e.g. fbx) is unsupported
                dest_name = f"{asset_name}.glb"
                dest = mesh_out / dest_name
            mesh.export(str(dest))

        rel = str(dest.relative_to(out_root))
        out_files.append(rel)

        # Godot .import sidecar
        if engine == "godot" and fmt == "glb":
            uid = uuid.uuid4().hex[:16]
            import_content = _GODOT_IMPORT_TPL.format(
                uid=uid,
                name=asset_name,
                src_path=f"{defaults['mesh_dir']}/{dest_name}",
            )
            import_path = dest.with_suffix(".glb.import")
            import_path.write_text(import_content)
            out_files.append(str(import_path.relative_to(out_root)))

        done += 1

    # Copy textures
    for tex_src in textures:
        tex_path = Path(tex_src)
        if not tex_path.exists():
            progress_cb(done / total * 0.8, f"Warning: texture not found: {tex_src}")
            done += 1
            continue
        dest = tex_out / tex_path.name
        progress_cb(done / total * 0.8, f"Copying texture {tex_path.name}…")
        shutil.copy2(tex_path, dest)
        out_files.append(str(dest.relative_to(out_root)))
        done += 1

    progress_cb(1.0, "Done")
    return {
        "files": out_files,
        "metadata": {"engine": engine, "format": fmt, "asset_count": len(raw_input)},
    }
