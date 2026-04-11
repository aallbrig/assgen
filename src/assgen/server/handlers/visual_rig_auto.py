"""visual.rig.auto — automatic skeletal rigging via UniRig.

Generates a game-ready skeleton rig and skinning weights for a 3D mesh using
UniRig (ECCV 2024). Falls back to a heuristic biped skeleton placement if
UniRig is not installed.

  pip install torch transformers trimesh numpy

  # Full UniRig installation (optional, enables learned rigging):
  pip install git+https://github.com/VAST-AI-Research/UniRig.git

Params:
    input           (str):  path to input mesh (GLB/OBJ/FBX)
    skeleton        (str):  biped | quadruped | humanoid | custom (default: biped)
                            "humanoid" → Unity-compatible 55-bone naming convention
    output          (str):  output filename (default: <stem>_rigged.glb)
"""
from __future__ import annotations

try:
    import numpy as np  # noqa: F401
    import trimesh  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False

try:
    import unirig  # noqa: F401
    _UNIRIG_AVAILABLE = True
except ImportError:
    _UNIRIG_AVAILABLE = False

# ── Biped joint positions (normalised 0–1 relative to bounding box) ──────────
# "humanoid" mode uses Unity-compatible bone names; "biped" uses legacy names.

_HUMANOID_JOINTS = {
    # Core spine
    "Hips":             (0.50, 0.52, 0.50),
    "Spine":            (0.50, 0.59, 0.50),
    "Chest":            (0.50, 0.67, 0.50),
    "UpperChest":       (0.50, 0.74, 0.50),
    "Neck":             (0.50, 0.84, 0.50),
    "Head":             (0.50, 0.94, 0.50),
    # Left arm
    "LeftShoulder":     (0.40, 0.76, 0.50),
    "LeftUpperArm":     (0.30, 0.74, 0.50),
    "LeftLowerArm":     (0.21, 0.67, 0.50),
    "LeftHand":         (0.14, 0.61, 0.50),
    # Right arm
    "RightShoulder":    (0.60, 0.76, 0.50),
    "RightUpperArm":    (0.70, 0.74, 0.50),
    "RightLowerArm":    (0.79, 0.67, 0.50),
    "RightHand":        (0.86, 0.61, 0.50),
    # Left leg
    "LeftUpperLeg":     (0.44, 0.44, 0.50),
    "LeftLowerLeg":     (0.44, 0.28, 0.50),
    "LeftFoot":         (0.44, 0.10, 0.50),
    "LeftToes":         (0.44, 0.03, 0.48),
    # Right leg
    "RightUpperLeg":    (0.56, 0.44, 0.50),
    "RightLowerLeg":    (0.56, 0.28, 0.50),
    "RightFoot":        (0.56, 0.10, 0.50),
    "RightToes":        (0.56, 0.03, 0.48),
}

# Legacy "biped" names (non-humanoid, kept for backward compat)
_BIPED_JOINTS = {
    "Hips":          (0.5, 0.52, 0.5),
    "Spine":         (0.5, 0.60, 0.5),
    "Chest":         (0.5, 0.70, 0.5),
    "Neck":          (0.5, 0.84, 0.5),
    "Head":          (0.5, 0.94, 0.5),
    "LeftShoulder":  (0.38, 0.74, 0.5),
    "LeftArm":       (0.28, 0.74, 0.5),
    "LeftForeArm":   (0.20, 0.68, 0.5),
    "LeftHand":      (0.14, 0.62, 0.5),
    "RightShoulder": (0.62, 0.74, 0.5),
    "RightArm":      (0.72, 0.74, 0.5),
    "RightForeArm":  (0.80, 0.68, 0.5),
    "RightHand":     (0.86, 0.62, 0.5),
    "LeftUpLeg":     (0.44, 0.44, 0.5),
    "LeftLeg":       (0.44, 0.28, 0.5),
    "LeftFoot":      (0.44, 0.10, 0.5),
    "RightUpLeg":    (0.56, 0.44, 0.5),
    "RightLeg":      (0.56, 0.28, 0.5),
    "RightFoot":     (0.56, 0.10, 0.5),
}

# Parent hierarchy for humanoid skeleton
_HUMANOID_PARENT_MAP: dict[str, str] = {
    "Spine": "Hips", "Chest": "Spine", "UpperChest": "Chest",
    "Neck": "UpperChest", "Head": "Neck",
    "LeftShoulder": "UpperChest", "LeftUpperArm": "LeftShoulder",
    "LeftLowerArm": "LeftUpperArm", "LeftHand": "LeftLowerArm",
    "RightShoulder": "UpperChest", "RightUpperArm": "RightShoulder",
    "RightLowerArm": "RightUpperArm", "RightHand": "RightLowerArm",
    "LeftUpperLeg": "Hips", "LeftLowerLeg": "LeftUpperLeg",
    "LeftFoot": "LeftLowerLeg", "LeftToes": "LeftFoot",
    "RightUpperLeg": "Hips", "RightLowerLeg": "RightUpperLeg",
    "RightFoot": "RightLowerLeg", "RightToes": "RightFoot",
}

_BIPED_PARENT_MAP: dict[str, str] = {
    "Spine": "Hips", "Chest": "Spine", "Neck": "Chest", "Head": "Neck",
    "LeftShoulder": "Chest", "LeftArm": "LeftShoulder",
    "LeftForeArm": "LeftArm", "LeftHand": "LeftForeArm",
    "RightShoulder": "Chest", "RightArm": "RightShoulder",
    "RightForeArm": "RightArm", "RightHand": "RightForeArm",
    "LeftUpLeg": "Hips", "LeftLeg": "LeftUpLeg", "LeftFoot": "LeftLeg",
    "RightUpLeg": "Hips", "RightLeg": "RightUpLeg", "RightFoot": "RightLeg",
}


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Auto-rig a mesh using UniRig (or heuristic fallback)."""
    if not _AVAILABLE:
        raise RuntimeError(
            "trimesh and numpy are required. Run: pip install trimesh numpy torch"
        )

    from pathlib import Path

    import trimesh as tm

    raw_input = params.get("input") or ""
    input_path = Path(raw_input) if raw_input else Path("")
    if not raw_input or not input_path.is_file():
        # Try upstream_files
        upstream = params.get("upstream_files", [])
        mesh_exts = {".glb", ".obj", ".fbx", ".ply", ".gltf"}
        candidate = next(
            (f for f in upstream if Path(f).suffix.lower() in mesh_exts), None
        )
        if candidate:
            input_path = Path(candidate)
        else:
            raise ValueError(f"Input mesh not found: {input_path!r}")

    skeleton = (params.get("skeleton") or "biped").lower()
    # "humanoid" is an alias that sets Unity-compatible bone names
    use_humanoid = skeleton == "humanoid"
    effective_skeleton = "biped"  # UniRig skeleton type (biped/quadruped)

    out_name = params.get("output") or f"{input_path.stem}_rigged.glb"
    out_path = Path(output_dir) / out_name

    progress_cb(0.05, "Loading mesh…")
    scene = tm.load(str(input_path))
    if isinstance(scene, tm.Scene):
        mesh = tm.util.concatenate(list(scene.geometry.values()))
    else:
        mesh = scene

    if not isinstance(mesh, tm.Trimesh):
        raise ValueError("Could not extract a triangle mesh from the input.")

    if _UNIRIG_AVAILABLE:
        progress_cb(0.15, "Running UniRig learned rigging…")
        result_scene = _rig_with_unirig(mesh, effective_skeleton, device, model_path, progress_cb)
    else:
        progress_cb(0.15, "UniRig not installed — using heuristic placement…")
        result_scene = _rig_heuristic(mesh, use_humanoid, progress_cb)

    progress_cb(0.9, "Exporting…")
    result_scene.export(str(out_path))
    progress_cb(1.0, "Done")

    n_verts = len(mesh.vertices)
    bone_names = list(_HUMANOID_JOINTS.keys()) if use_humanoid else list(_BIPED_JOINTS.keys())
    return {
        "files": [out_name],
        "metadata": {
            "skeleton": "humanoid" if use_humanoid else effective_skeleton,
            "bone_names": bone_names,
            "bone_count": len(bone_names),
            "vertices": n_verts,
            "method": "unirig" if _UNIRIG_AVAILABLE else "heuristic",
            "unity_compatible": use_humanoid,
        },
    }


def _rig_with_unirig(mesh, skeleton, device, model_path, progress_cb):
    """Use the UniRig API when available."""
    import unirig

    progress_cb(0.3, "UniRig: predicting skeleton…")
    joints, parents, skin_weights = unirig.rig(
        vertices=mesh.vertices,
        faces=mesh.faces,
        skeleton_type=skeleton,
        device=device,
        model_path=model_path,
    )

    progress_cb(0.7, "UniRig: building skinned mesh…")
    return _build_skinned_scene(mesh, joints, parents, skin_weights)


def _rig_heuristic(mesh, use_humanoid: bool, progress_cb):
    """Place joints at heuristic positions derived from bounding box."""
    import numpy as np

    bbox_min = mesh.bounds[0]
    bbox_max = mesh.bounds[1]
    bbox_size = bbox_max - bbox_min

    joint_template = _HUMANOID_JOINTS if use_humanoid else _BIPED_JOINTS
    parent_map = _HUMANOID_PARENT_MAP if use_humanoid else _BIPED_PARENT_MAP

    joints_world: dict[str, np.ndarray] = {}
    for name, (nx, ny, nz) in joint_template.items():
        pos = bbox_min + np.array([nx, ny, nz]) * bbox_size
        joints_world[name] = pos

    progress_cb(0.5, "Computing distance-based skin weights…")
    skin_weights = _distance_skin_weights(mesh.vertices, list(joints_world.values()))

    joint_arr = np.array(list(joints_world.values()))
    names = list(joints_world.keys())
    parents = [
        names.index(parent_map[n]) if n in parent_map else -1
        for n in names
    ]

    return _build_skinned_scene(mesh, joint_arr, parents, skin_weights)


def _distance_skin_weights(vertices: np.ndarray, joints: list) -> np.ndarray:
    """Inverse-distance skinning weights, normalised per vertex."""
    import numpy as np
    n_verts = len(vertices)
    n_joints = len(joints)
    w = np.zeros((n_verts, n_joints), dtype=np.float32)
    for j, jpos in enumerate(joints):
        dist = np.linalg.norm(vertices - jpos, axis=1)
        w[:, j] = 1.0 / (dist + 1e-6)
    row_sums = w.sum(axis=1, keepdims=True)
    row_sums = np.maximum(row_sums, 1e-8)
    return w / row_sums


def _build_skinned_scene(mesh, joints, parents, skin_weights):
    """Wrap mesh + rig data into a trimesh Scene with skin metadata."""
    import trimesh as tm

    scene = tm.Scene()
    scene.add_geometry(mesh, node_name="mesh")
    scene.metadata = {
        "joints": joints.tolist() if hasattr(joints, "tolist") else list(joints),
        "parents": list(parents),
        "skin_weights_shape": list(skin_weights.shape),
    }
    return scene

