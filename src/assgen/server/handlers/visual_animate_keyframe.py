"""visual.animate.keyframe — text-guided keyframe animation via AnimateDiff.

Generates a short animated sequence (GIF/MP4/frame PNGs) from a text prompt
using AnimateDiff with a base SDXL checkpoint.

  pip install diffusers transformers accelerate torch imageio[ffmpeg] Pillow

Params:
    prompt          (str):  animation description
    negative_prompt (str):  negative prompt (optional)
    steps           (int):  inference steps (default: 25)
    guidance_scale  (float):CFG scale (default: 7.5)
    num_frames      (int):  frames to generate (default: 16)
    fps             (int):  output FPS for GIF/MP4 (default: 8)
    format          (str):  gif | mp4 | frames (default: gif)
    width           (int):  frame width (default: 512)
    height          (int):  frame height (default: 512)
    output          (str):  output filename stem (default: animation)
"""
from __future__ import annotations

try:
    from diffusers import AnimateDiffPipeline  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Generate a keyframe animation from a text prompt using AnimateDiff."""
    if not _AVAILABLE:
        raise RuntimeError(
            "diffusers is required. Run: pip install diffusers transformers accelerate torch"
        )

    import torch
    from pathlib import Path
    from diffusers import AnimateDiffPipeline, MotionAdapter, EulerDiscreteScheduler
    from diffusers.utils import export_to_gif, export_to_video

    prompt = params.get("prompt", "")
    if not prompt:
        raise ValueError("'prompt' is required")

    negative_prompt = params.get("negative_prompt", "")
    steps = int(params.get("steps", 25))
    guidance = float(params.get("guidance_scale", 7.5))
    num_frames = int(params.get("num_frames", 16))
    fps = int(params.get("fps", 8))
    fmt = (params.get("format") or "gif").lower()
    width = int(params.get("width", 512))
    height = int(params.get("height", 512))
    out_stem = params.get("output") or "animation"
    out_dir = Path(output_dir)

    progress_cb(0.05, "Loading AnimateDiff motion adapter…")
    adapter_id = "guoyww/animatediff-motion-adapter-v1-5-2"
    adapter = MotionAdapter.from_pretrained(adapter_id, torch_dtype=torch.float16)

    base_id = model_path or model_id or "SG161222/Realistic_Vision_V6.0_B1_noVAE"
    progress_cb(0.15, f"Loading base SD pipeline ({base_id})…")
    dtype = torch.float16 if device != "cpu" else torch.float32
    pipe = AnimateDiffPipeline.from_pretrained(
        base_id,
        motion_adapter=adapter,
        torch_dtype=dtype,
    ).to(device)
    pipe.scheduler = EulerDiscreteScheduler.from_config(
        pipe.scheduler.config,
        beta_schedule="linear",
        timestep_spacing="linspace",
        clip_sample=False,
    )

    progress_cb(0.35, f"Generating {num_frames} frames…")
    result = pipe(
        prompt=prompt,
        negative_prompt=negative_prompt or None,
        num_inference_steps=steps,
        guidance_scale=guidance,
        num_frames=num_frames,
        width=width,
        height=height,
    )
    frames = result.frames[0]  # list of PIL images

    out_files: list[str] = []
    progress_cb(0.9, f"Exporting as {fmt}…")

    if fmt == "mp4":
        out_name = f"{out_stem}.mp4"
        export_to_video(frames, str(out_dir / out_name), fps=fps)
        out_files.append(out_name)
    elif fmt == "frames":
        for i, frame in enumerate(frames):
            fn = f"{out_stem}_frame_{i:04d}.png"
            frame.save(str(out_dir / fn))
            out_files.append(fn)
    else:  # gif
        out_name = f"{out_stem}.gif"
        export_to_gif(frames, str(out_dir / out_name))
        out_files.append(out_name)

    progress_cb(1.0, "Done")
    return {
        "files": out_files,
        "metadata": {
            "num_frames": num_frames,
            "fps": fps,
            "width": width,
            "height": height,
        },
    }
