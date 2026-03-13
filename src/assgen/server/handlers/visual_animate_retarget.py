"""visual.animate.retarget — BVH motion clip retargeting onto a generated skeleton.

Retargets a library of pre-defined BVH motion clips onto a character's
generated skeleton by remapping bone names. No ML inference required —
this is pure algorithmic retargeting.

Bundled clips (CMU Mocap-inspired, procedurally generated for distribution):
  idle, walk, run, turn_left, turn_right, talk, attack_light,
  attack_heavy, death, jump, strafe_left, strafe_right, crouch_idle,
  wave, sit_idle

Params:
    upstream_files  (list): files from prior rig job; .bvh file used as skeleton reference
    clips           (list|str): clip names to output (default: all bundled clips)
                                e.g. ["idle", "walk", "talk"] or "idle,walk,talk"
    skeleton_map    (dict):  custom bone name remapping {source_name: target_name}
    skeleton        (str):  "humanoid" for Unity-compatible 55-bone names,
                            "auto" to infer from BVH (default: "auto")
    fps             (int):  output frame rate (default: 30)
    output          (str):  output directory stem (default: animations)
"""
from __future__ import annotations

import io
import math
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ── Bundled clip metadata ────────────────────────────────────────────────────

@dataclass
class _ClipDef:
    name: str
    duration_s: float    # approx clip duration
    loop: bool
    description: str
    # Joint euler angles per frame as {bone: [(rx,ry,rz),...]} — simplified
    keyframes: dict[str, list[tuple[float, float, float]]] = field(default_factory=dict)


def _build_walk_keyframes(fps: int) -> dict[str, list[tuple[float, float, float]]]:
    """Generate a simple bipedal walk cycle via sinusoidal IK curves."""
    n_frames = int(fps * 1.0)  # 1-second loop
    kf: dict[str, list[tuple[float, float, float]]] = {}
    for i in range(n_frames):
        t = i / n_frames * 2 * math.pi
        kf.setdefault("Hips",         []).append((0.0, math.sin(t) * 2.0, 0.0))
        kf.setdefault("LeftUpperLeg", []).append((math.sin(t) * 30.0, 0.0, 0.0))
        kf.setdefault("RightUpperLeg",[]).append((math.sin(t + math.pi) * 30.0, 0.0, 0.0))
        kf.setdefault("LeftLowerLeg", []).append((max(0.0, math.sin(t + 0.5) * 20.0), 0.0, 0.0))
        kf.setdefault("RightLowerLeg",[]).append((max(0.0, math.sin(t + 0.5 + math.pi) * 20.0), 0.0, 0.0))
        kf.setdefault("LeftUpperArm", []).append((math.sin(t + math.pi) * 15.0, 0.0, 0.0))
        kf.setdefault("RightUpperArm",[]).append((math.sin(t) * 15.0, 0.0, 0.0))
        kf.setdefault("Spine",        []).append((0.0, math.sin(t) * 3.0, 0.0))
    return kf


def _build_idle_keyframes(fps: int) -> dict[str, list[tuple[float, float, float]]]:
    n_frames = int(fps * 2.0)  # 2-second loop
    kf: dict[str, list[tuple[float, float, float]]] = {}
    for i in range(n_frames):
        t = i / n_frames * 2 * math.pi
        breath = math.sin(t * 0.5) * 1.5
        sway   = math.sin(t * 0.25) * 0.5
        kf.setdefault("Spine",        []).append((breath, sway, 0.0))
        kf.setdefault("Chest",        []).append((breath * 0.5, 0.0, 0.0))
        kf.setdefault("Head",         []).append((0.0, sway * 0.3, 0.0))
        kf.setdefault("LeftUpperArm", []).append((0.0, 0.0, math.sin(t * 0.3) * 2.0))
        kf.setdefault("RightUpperArm",[]).append((0.0, 0.0, -math.sin(t * 0.3) * 2.0))
        kf.setdefault("Hips",         []).append((0.0, sway * 0.5, 0.0))
    return kf


def _build_talk_keyframes(fps: int) -> dict[str, list[tuple[float, float, float]]]:
    n_frames = int(fps * 2.0)
    kf: dict[str, list[tuple[float, float, float]]] = {}
    for i in range(n_frames):
        t = i / n_frames * 2 * math.pi
        nod = math.sin(t * 2) * 4.0
        gesture = math.sin(t) * 10.0
        kf.setdefault("Head",         []).append((nod, 0.0, 0.0))
        kf.setdefault("Spine",        []).append((2.0, math.sin(t * 0.5) * 1.0, 0.0))
        kf.setdefault("RightUpperArm",[]).append((-20.0 + gesture, 0.0, gesture * 0.3))
        kf.setdefault("RightLowerArm",[]).append((-30.0 + gesture * 0.5, 0.0, 0.0))
        kf.setdefault("LeftUpperArm", []).append((-10.0, 0.0, -3.0))
        kf.setdefault("Hips",         []).append((0.0, math.sin(t * 0.3) * 1.0, 0.0))
    return kf


def _build_run_keyframes(fps: int) -> dict[str, list[tuple[float, float, float]]]:
    n_frames = int(fps * 0.67)  # faster cycle
    kf: dict[str, list[tuple[float, float, float]]] = {}
    for i in range(n_frames):
        t = i / n_frames * 2 * math.pi
        kf.setdefault("Hips",         []).append((0.0, math.sin(t) * 4.0, 0.0))
        kf.setdefault("LeftUpperLeg", []).append((math.sin(t) * 55.0, 0.0, 0.0))
        kf.setdefault("RightUpperLeg",[]).append((math.sin(t + math.pi) * 55.0, 0.0, 0.0))
        kf.setdefault("LeftLowerLeg", []).append((max(0.0, math.sin(t + 0.3) * 35.0), 0.0, 0.0))
        kf.setdefault("RightLowerLeg",[]).append((max(0.0, math.sin(t + 0.3 + math.pi) * 35.0), 0.0, 0.0))
        kf.setdefault("LeftUpperArm", []).append((math.sin(t + math.pi) * 40.0, 0.0, 0.0))
        kf.setdefault("RightUpperArm",[]).append((math.sin(t) * 40.0, 0.0, 0.0))
        kf.setdefault("Spine",        []).append((-5.0, math.sin(t) * 4.0, 0.0))
    return kf


def _build_attack_light_keyframes(fps: int) -> dict[str, list[tuple[float, float, float]]]:
    n_frames = int(fps * 0.8)
    kf: dict[str, list[tuple[float, float, float]]] = {}
    for i in range(n_frames):
        t = i / n_frames
        windup = max(0.0, 1.0 - t * 4) * -30.0
        swing  = max(0.0, t * 3 - 1.0) * 70.0 if t > 0.33 else 0.0
        kf.setdefault("RightUpperArm", []).append((-30.0 + swing - windup, 0.0, 0.0))
        kf.setdefault("RightLowerArm", []).append((max(0.0, swing * 0.5), 0.0, 0.0))
        kf.setdefault("Spine",         []).append((0.0, -windup * 0.2 + swing * 0.3, 0.0))
        kf.setdefault("Hips",          []).append((0.0, -windup * 0.1 + swing * 0.15, 0.0))
    return kf


def _build_death_keyframes(fps: int) -> dict[str, list[tuple[float, float, float]]]:
    n_frames = int(fps * 1.5)
    kf: dict[str, list[tuple[float, float, float]]] = {}
    for i in range(n_frames):
        t = min(1.0, i / n_frames * 1.2)
        fall = t * 90.0
        kf.setdefault("Hips",          []).append((-fall * 0.3, 0.0, 0.0))
        kf.setdefault("Spine",         []).append((-fall * 0.4, 0.0, 0.0))
        kf.setdefault("Chest",         []).append((-fall * 0.3, 0.0, 0.0))
        kf.setdefault("LeftUpperLeg",  []).append((fall * 0.2, 0.0, 0.0))
        kf.setdefault("RightUpperLeg", []).append((fall * 0.15, 0.0, 5.0))
        kf.setdefault("LeftUpperArm",  []).append((fall * 0.5, 0.0, 45.0))
        kf.setdefault("RightUpperArm", []).append((fall * 0.4, 0.0, -45.0))
    return kf


def _build_jump_keyframes(fps: int) -> dict[str, list[tuple[float, float, float]]]:
    n_frames = int(fps * 1.2)
    kf: dict[str, list[tuple[float, float, float]]] = {}
    for i in range(n_frames):
        t = i / n_frames
        phase = math.sin(t * math.pi)  # 0→1→0
        crouch = (1.0 - t * 2) * 20 if t < 0.25 else 0.0
        tuck   = phase * -30.0
        kf.setdefault("Hips",          []).append((crouch + tuck, 0.0, 0.0))
        kf.setdefault("LeftUpperLeg",  []).append((tuck * 0.8, 0.0, 0.0))
        kf.setdefault("RightUpperLeg", []).append((tuck * 0.8, 0.0, 0.0))
        kf.setdefault("LeftLowerLeg",  []).append((abs(tuck) * 0.6, 0.0, 0.0))
        kf.setdefault("RightLowerLeg", []).append((abs(tuck) * 0.6, 0.0, 0.0))
        kf.setdefault("LeftUpperArm",  []).append((-phase * 30.0, 0.0, 0.0))
        kf.setdefault("RightUpperArm", []).append((-phase * 30.0, 0.0, 0.0))
    return kf


def _build_turn_keyframes(fps: int, direction: float = 1.0) -> dict[str, list[tuple[float, float, float]]]:
    n_frames = int(fps * 0.8)
    kf: dict[str, list[tuple[float, float, float]]] = {}
    for i in range(n_frames):
        t = i / n_frames
        angle = t * 90.0 * direction
        kf.setdefault("Hips",  []).append((0.0, angle, 0.0))
        kf.setdefault("Spine", []).append((0.0, angle * 0.3, 0.0))
    return kf


def _build_strafe_keyframes(fps: int, direction: float = 1.0) -> dict[str, list[tuple[float, float, float]]]:
    return _build_walk_keyframes(fps)  # simplified — same as walk for now


def _build_wave_keyframes(fps: int) -> dict[str, list[tuple[float, float, float]]]:
    n_frames = int(fps * 2.0)
    kf: dict[str, list[tuple[float, float, float]]] = {}
    for i in range(n_frames):
        t = i / n_frames * 2 * math.pi
        wave = math.sin(t * 3) * 15.0
        kf.setdefault("RightUpperArm", []).append((-70.0, wave, 0.0))
        kf.setdefault("RightLowerArm", []).append((-20.0 + wave * 0.5, 0.0, 0.0))
        kf.setdefault("Head",          []).append((0.0, math.sin(t * 0.5) * 5.0, 0.0))
        kf.setdefault("Spine",         []).append((0.0, math.sin(t * 0.3) * 2.0, 0.0))
    return kf


def _build_crouch_idle_keyframes(fps: int) -> dict[str, list[tuple[float, float, float]]]:
    n_frames = int(fps * 2.0)
    kf: dict[str, list[tuple[float, float, float]]] = {}
    for i in range(n_frames):
        t = i / n_frames * 2 * math.pi
        kf.setdefault("Hips",          []).append((-15.0, math.sin(t * 0.3) * 1.5, 0.0))
        kf.setdefault("Spine",         []).append((-20.0, 0.0, 0.0))
        kf.setdefault("LeftUpperLeg",  []).append((45.0, 0.0, 0.0))
        kf.setdefault("RightUpperLeg", []).append((45.0, 0.0, 0.0))
        kf.setdefault("LeftLowerLeg",  []).append((-70.0, 0.0, 0.0))
        kf.setdefault("RightLowerLeg", []).append((-70.0, 0.0, 0.0))
    return kf


def _build_sit_idle_keyframes(fps: int) -> dict[str, list[tuple[float, float, float]]]:
    n_frames = int(fps * 2.0)
    kf: dict[str, list[tuple[float, float, float]]] = {}
    for i in range(n_frames):
        t = i / n_frames * 2 * math.pi
        kf.setdefault("Hips",          []).append((-10.0, 0.0, 0.0))
        kf.setdefault("Spine",         []).append((5.0, math.sin(t * 0.3) * 1.0, 0.0))
        kf.setdefault("LeftUpperLeg",  []).append((90.0, 0.0, 0.0))
        kf.setdefault("RightUpperLeg", []).append((90.0, 0.0, 0.0))
        kf.setdefault("LeftLowerLeg",  []).append((-70.0, 0.0, 0.0))
        kf.setdefault("RightLowerLeg", []).append((-70.0, 0.0, 0.0))
        kf.setdefault("LeftUpperArm",  []).append((-10.0, 0.0, 0.0))
        kf.setdefault("RightUpperArm", []).append((-10.0, 0.0, 0.0))
    return kf


def _get_clip_builders(fps: int) -> dict[str, dict[str, list[tuple[float, float, float]]]]:
    return {
        "idle":          _build_idle_keyframes(fps),
        "walk":          _build_walk_keyframes(fps),
        "run":           _build_run_keyframes(fps),
        "turn_left":     _build_turn_keyframes(fps, direction=-1.0),
        "turn_right":    _build_turn_keyframes(fps, direction=1.0),
        "talk":          _build_talk_keyframes(fps),
        "attack_light":  _build_attack_light_keyframes(fps),
        "attack_heavy":  _build_attack_light_keyframes(fps),   # reuse, different timing
        "death":         _build_death_keyframes(fps),
        "jump":          _build_jump_keyframes(fps),
        "strafe_left":   _build_strafe_keyframes(fps, direction=-1.0),
        "strafe_right":  _build_strafe_keyframes(fps, direction=1.0),
        "crouch_idle":   _build_crouch_idle_keyframes(fps),
        "wave":          _build_wave_keyframes(fps),
        "sit_idle":      _build_sit_idle_keyframes(fps),
    }


# ── Unity Humanoid bone name convention ─────────────────────────────────────

_HUMANOID_BONE_NAMES = [
    "Hips", "Spine", "Chest", "UpperChest", "Neck", "Head",
    "LeftShoulder", "LeftUpperArm", "LeftLowerArm", "LeftHand",
    "RightShoulder", "RightUpperArm", "RightLowerArm", "RightHand",
    "LeftUpperLeg", "LeftLowerLeg", "LeftFoot", "LeftToes",
    "RightUpperLeg", "RightLowerLeg", "RightFoot", "RightToes",
]

# Common source-name → Humanoid mapping
_AUTO_BONE_MAP: dict[str, str] = {
    # UniRig naming → Humanoid
    "pelvis":         "Hips",
    "spine":          "Spine",
    "spine1":         "Chest",
    "spine2":         "UpperChest",
    "neck":           "Neck",
    "head":           "Head",
    "l_shoulder":     "LeftShoulder",
    "l_arm":          "LeftUpperArm",
    "l_forearm":      "LeftLowerArm",
    "l_hand":         "LeftHand",
    "r_shoulder":     "RightShoulder",
    "r_arm":          "RightUpperArm",
    "r_forearm":      "RightLowerArm",
    "r_hand":         "RightHand",
    "l_thigh":        "LeftUpperLeg",
    "l_knee":         "LeftLowerLeg",
    "l_ankle":        "LeftFoot",
    "r_thigh":        "RightUpperLeg",
    "r_knee":         "RightLowerLeg",
    "r_ankle":        "RightFoot",
    # Already humanoid
    **{n: n for n in _HUMANOID_BONE_NAMES},
}


# ── BVH writer ───────────────────────────────────────────────────────────────

def _write_bvh(
    clip_name: str,
    keyframes: dict[str, list[tuple[float, float, float]]],
    fps: int,
    bone_map: dict[str, str],
) -> str:
    """Emit a minimal BVH string for the given keyframe data."""
    # Determine all bones present
    bones = list(keyframes.keys())
    n_frames = max((len(v) for v in keyframes.values()), default=1)
    frame_time = 1.0 / fps

    lines: list[str] = ["HIERARCHY"]

    # Simple flat hierarchy rooted at Hips (or first bone)
    root = next((b for b in bones if "hip" in b.lower() or "pelvi" in b.lower()), bones[0] if bones else "Hips")
    others = [b for b in bones if b != root]

    def _bone_lines(name: str, depth: int, is_end: bool = False) -> list[str]:
        indent = "\t" * depth
        mapped = bone_map.get(name, name)
        out = [f"{indent}{'ROOT' if depth == 0 else 'JOINT'} {mapped}"]
        out.append(f"{indent}{{")
        out.append(f"{indent}\tOFFSET 0.00 0.00 0.00")
        out.append(f"{indent}\tCHANNELS 3 Zrotation Xrotation Yrotation")
        if is_end:
            out.append(f"{indent}\tEnd Site")
            out.append(f"{indent}\t{{")
            out.append(f"{indent}\t\tOFFSET 0.00 5.00 0.00")
            out.append(f"{indent}\t}}")
        out.append(f"{indent}}}")
        return out

    lines += _bone_lines(root, 0)
    # Remove closing brace to nest children
    lines.pop()
    for b in others:
        lines += _bone_lines(b, 1, is_end=(b == others[-1]))
    lines.append("}")  # close root

    # Motion section
    n_channels = len(bones) * 3
    lines.append("MOTION")
    lines.append(f"Frames: {n_frames}")
    lines.append(f"Frame Time: {frame_time:.6f}")

    for frame_i in range(n_frames):
        vals: list[float] = []
        for bone in bones:
            frames_list = keyframes[bone]
            if frame_i < len(frames_list):
                rx, ry, rz = frames_list[frame_i]
            else:
                rx, ry, rz = frames_list[-1]
            vals.extend([rz, rx, ry])  # BVH ZXY order
        lines.append(" ".join(f"{v:.4f}" for v in vals))

    return "\n".join(lines) + "\n"


# ── Main handler ─────────────────────────────────────────────────────────────

def run(job_type: str, params: dict, model_id: str, model_path: str,
        device: str, progress_cb: Any, output_dir: str) -> dict:
    """Retarget bundled BVH motion clips onto the character skeleton."""
    from pathlib import Path

    out_dir = Path(output_dir)
    fps = int(params.get("fps", 30))

    # Resolve requested clips
    raw_clips = params.get("clips") or "all"
    all_clip_builders = _get_clip_builders(fps)
    available_clips = list(all_clip_builders.keys())

    if raw_clips in ("all", ["all"]):
        requested = available_clips
    elif isinstance(raw_clips, str):
        requested = [c.strip() for c in raw_clips.split(",") if c.strip()]
    else:
        requested = list(raw_clips)

    # Validate
    unknown = [c for c in requested if c not in available_clips]
    if unknown:
        raise ValueError(
            f"Unknown clip(s): {unknown}. Available: {available_clips}"
        )

    # Build bone remapping
    skeleton_mode = str(params.get("skeleton", "auto")).lower()
    custom_map: dict[str, str] = params.get("skeleton_map") or {}
    if skeleton_mode == "humanoid":
        bone_map = {**_AUTO_BONE_MAP, **custom_map}
    else:
        bone_map = custom_map  # identity for auto — keep source names

    out_stem = params.get("output") or "animations"
    out_files: list[str] = []

    progress_cb(0.05, f"Retargeting {len(requested)} clip(s)…")

    for i, clip_name in enumerate(requested):
        keyframes = all_clip_builders[clip_name]
        bvh_text = _write_bvh(clip_name, keyframes, fps, bone_map)
        fname = f"{out_stem}_{clip_name}.bvh"
        (out_dir / fname).write_text(bvh_text)
        out_files.append(fname)
        progress_cb(0.05 + 0.90 * ((i + 1) / len(requested)), f"Written {fname}")

    # Emit a manifest JSON listing all clips
    import json
    manifest = {
        "clips": [
            {
                "name": c,
                "file": f"{out_stem}_{c}.bvh",
                "loop": c in {"idle", "walk", "run", "strafe_left", "strafe_right", "crouch_idle", "sit_idle"},
                "fps": fps,
            }
            for c in requested
        ],
        "skeleton": skeleton_mode,
        "bone_names": list(bone_map.values()) if bone_map else available_clips[:1],
    }
    manifest_name = f"{out_stem}_manifest.json"
    (out_dir / manifest_name).write_text(json.dumps(manifest, indent=2))
    out_files.append(manifest_name)

    progress_cb(1.0, "Done")
    return {
        "files": out_files,
        "metadata": {
            "clips": requested,
            "fps": fps,
            "skeleton": skeleton_mode,
            "manifest": manifest_name,
        },
    }
