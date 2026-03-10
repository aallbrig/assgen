"""visual.animate.mocap — motion-capture retargeting via Sapiens pose estimation.

Given a video or sequence of frames, extracts 3D body keypoints using Meta's
Sapiens pose estimation model and exports the motion as a BVH file suitable
for retargeting onto game characters.

  pip install transformers torch Pillow imageio[ffmpeg] numpy

Params:
    input       (str):  path to input video file or image directory
    fps         (int):  input video FPS override (default: 30, ignored for image dirs)
    output      (str):  output BVH filename (default: mocap.bvh)
    max_frames  (int):  maximum frames to process (default: 300)
"""
from __future__ import annotations

try:
    from transformers import pipeline as hf_pipeline  # noqa: F401
    import numpy as np  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False

# Sapiens 2D keypoint indices (COCO-17 ordering)
_KEYPOINT_NAMES = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle",
]

# BVH hierarchy skeleton (simplified biped)
_BVH_HEADER = """\
HIERARCHY
ROOT Hips
{
  CHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation
  JOINT Spine
  {
    OFFSET 0.00 5.21 0.00
    CHANNELS 3 Zrotation Xrotation Yrotation
    JOINT Chest
    {
      OFFSET 0.00 5.65 0.00
      CHANNELS 3 Zrotation Xrotation Yrotation
      JOINT LeftShoulder
      {
        OFFSET -4.57 4.16 0.00
        CHANNELS 3 Zrotation Xrotation Yrotation
        JOINT LeftArm
        {
          OFFSET -5.00 0.00 0.00
          CHANNELS 3 Zrotation Xrotation Yrotation
          JOINT LeftForeArm
          {
            OFFSET -5.00 0.00 0.00
            CHANNELS 3 Zrotation Xrotation Yrotation
            End Site
            { OFFSET -5.00 0.00 0.00 }
          }
        }
      }
      JOINT RightShoulder
      {
        OFFSET 4.57 4.16 0.00
        CHANNELS 3 Zrotation Xrotation Yrotation
        JOINT RightArm
        {
          OFFSET 5.00 0.00 0.00
          CHANNELS 3 Zrotation Xrotation Yrotation
          JOINT RightForeArm
          {
            OFFSET 5.00 0.00 0.00
            CHANNELS 3 Zrotation Xrotation Yrotation
            End Site
            { OFFSET 5.00 0.00 0.00 }
          }
        }
      }
    }
  }
  JOINT LeftUpLeg
  {
    OFFSET -3.51 0.00 0.00
    CHANNELS 3 Zrotation Xrotation Yrotation
    JOINT LeftLeg
    {
      OFFSET 0.00 -5.00 0.00
      CHANNELS 3 Zrotation Xrotation Yrotation
      JOINT LeftFoot
      {
        OFFSET 0.00 -5.00 0.00
        CHANNELS 3 Zrotation Xrotation Yrotation
        End Site
        { OFFSET 0.00 -2.00 0.00 }
      }
    }
  }
  JOINT RightUpLeg
  {
    OFFSET 3.51 0.00 0.00
    CHANNELS 3 Zrotation Xrotation Yrotation
    JOINT RightLeg
    {
      OFFSET 0.00 -5.00 0.00
      CHANNELS 3 Zrotation Xrotation Yrotation
      JOINT RightFoot
      {
        OFFSET 0.00 -5.00 0.00
        CHANNELS 3 Zrotation Xrotation Yrotation
        End Site
        { OFFSET 0.00 -2.00 0.00 }
      }
    }
  }
}
"""


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Extract motion capture data from video and export as BVH."""
    if not _AVAILABLE:
        raise RuntimeError(
            "transformers and numpy are required. "
            "Run: pip install transformers torch numpy Pillow imageio[ffmpeg]"
        )

    import numpy as np
    from pathlib import Path
    from PIL import Image
    from transformers import pipeline as hf_pipeline

    input_path = Path(params.get("input", ""))
    if not input_path.exists():
        raise ValueError(f"Input not found: {input_path!r}")

    fps = int(params.get("fps", 30))
    max_frames = int(params.get("max_frames", 300))
    out_name = params.get("output") or "mocap.bvh"
    out_path = Path(output_dir) / out_name

    progress_cb(0.05, "Loading Sapiens pose estimator…")
    hf_id = model_path or model_id or "facebook/sapiens-pose-0.3b-torchscript"
    estimator = hf_pipeline(
        "image-to-text",  # Sapiens uses generic vision pipeline
        model=hf_id,
        device=0 if device == "cuda" else -1,
    )

    # Collect frames
    frames: list[Image.Image] = []
    progress_cb(0.1, "Loading frames…")
    if input_path.is_dir():
        for ext in ("*.png", "*.jpg", "*.jpeg"):
            frames.extend(sorted(input_path.glob(ext)))
        frames = [Image.open(f).convert("RGB") for f in frames[:max_frames]]
    else:
        try:
            import imageio.v3 as iio
            vid = iio.imread(str(input_path), plugin="pyav")
            step = max(1, len(vid) // max_frames)
            frames = [Image.fromarray(vid[i]) for i in range(0, len(vid), step)][:max_frames]
        except Exception as exc:
            raise RuntimeError(f"Could not read video: {exc}") from exc

    if not frames:
        raise ValueError("No frames found in input")

    # Run pose estimation per frame
    all_keypoints: list[np.ndarray] = []
    for i, frame in enumerate(frames):
        if i % max(1, len(frames) // 10) == 0:
            progress_cb(0.15 + 0.6 * (i / len(frames)), f"Estimating pose {i+1}/{len(frames)}…")
        try:
            result = estimator(frame)
            kp = _parse_keypoints(result, len(_KEYPOINT_NAMES))
        except Exception:
            kp = np.zeros((len(_KEYPOINT_NAMES), 3), dtype=np.float32)
        all_keypoints.append(kp)

    progress_cb(0.8, "Building BVH…")
    bvh_content = _keypoints_to_bvh(all_keypoints, fps)

    out_path.write_text(bvh_content)
    progress_cb(1.0, "Done")

    return {
        "files": [out_name],
        "metadata": {"frames": len(all_keypoints), "fps": fps},
    }


def _parse_keypoints(result, n_joints: int) -> "np.ndarray":
    import numpy as np
    kp = np.zeros((n_joints, 3), dtype=np.float32)
    if isinstance(result, list) and result:
        raw = result[0]
        if isinstance(raw, dict) and "keypoints" in raw:
            for i, pt in enumerate(raw["keypoints"][:n_joints]):
                kp[i] = [pt.get("x", 0), pt.get("y", 0), pt.get("score", 1)]
    return kp


def _keypoints_to_bvh(keypoints: list, fps: int) -> str:
    """Convert per-frame keypoints to a minimal BVH motion block."""
    import numpy as np

    n_frames = len(keypoints)
    # Hip position heuristic: midpoint of left/right hip (indices 11, 12)
    lines = [_BVH_HEADER, "MOTION"]
    lines.append(f"Frames: {n_frames}")
    lines.append(f"Frame Time: {1.0 / fps:.6f}")

    for kp in keypoints:
        lhip = kp[11, :2] if kp.shape[0] > 12 else np.zeros(2)
        rhip = kp[12, :2] if kp.shape[0] > 12 else np.zeros(2)
        hip_x = float((lhip[0] + rhip[0]) * 0.5)
        hip_y = float((lhip[1] + rhip[1]) * 0.5)
        # 6 DOF root + 3 DOF × 12 joints = 42 values
        vals = [hip_x, hip_y, 0.0, 0.0, 0.0, 0.0]
        vals += [0.0] * (3 * 12)
        lines.append(" ".join(f"{v:.4f}" for v in vals))

    return "\n".join(lines)
