"""visual.concept.generate — text-to-image concept art via SDXL.

Generates concept art images from text prompts using Stable Diffusion XL.
Covers visual.concept.generate, visual.texture.generate, visual.ui.icon,
visual.blockout.create, and visual.vfx.particle (all SDXL-backed).

  pip install diffusers transformers accelerate torch

Quality variants:
  draft    → stabilityai/sdxl-turbo   (1 step, ~2 s on 4070)
  standard → stabilityai/stable-diffusion-xl-base-1.0 (30 steps)
  high     → base + refiner pipeline  (30 + 10 steps)
"""

try:
    from diffusers import (  # type: ignore[import]  # noqa: F401
        StableDiffusionXLImg2ImgPipeline,
        StableDiffusionXLPipeline,
    )
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False

# Job-type-specific prompt prefixes that steer the model towards the right output
_JOB_PREFIXES: dict[str, str] = {
    "visual.concept.generate":  "",
    "visual.texture.generate":  "seamless tileable texture, top-down view, no shadows, ",
    "visual.ui.icon":           "flat vector icon, clean lines, transparent background, game UI, ",
    "visual.blockout.create":   "architectural greybox level sketch, top-down blueprint, orthographic, ",
    "visual.vfx.particle":      "sprite sheet, particle effect frames on black background, transparent, ",
}

_TURBO_MODELS = {"stabilityai/sdxl-turbo"}


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Generate concept art / texture / icon images using SDXL."""
    if not _AVAILABLE:
        raise RuntimeError(
            "diffusers is not installed. Run: pip install diffusers transformers accelerate"
        )

    from pathlib import Path

    import torch

    prompt = params.get("prompt") or params.get("text")
    if not prompt:
        raise ValueError("'prompt' param is required")

    prefix = _JOB_PREFIXES.get(job_type, "")
    full_prompt = prefix + prompt

    negative_prompt = params.get("negative_prompt", "blurry, low quality, watermark, text")
    width = int(params.get("width", 1024))
    height = int(params.get("height", 1024))
    seed = params.get("seed")
    resolved_model = model_id or "stabilityai/stable-diffusion-xl-base-1.0"
    is_turbo = resolved_model in _TURBO_MODELS

    # Turbo uses guidance_scale=0 and 1 step
    guidance_scale = float(params.get("guidance_scale", 0.0 if is_turbo else 7.5))
    num_steps = int(params.get("steps", 1 if is_turbo else 30))
    num_images = int(params.get("num_images", 1))

    progress_cb(0.05, f"Loading SDXL pipeline ({resolved_model})…")

    # Free any VRAM left by prior jobs before loading a new model.
    if device != "cpu":
        torch.cuda.empty_cache()

    dtype = torch.float16 if device != "cpu" else torch.float32
    load_kwargs: dict = dict(
        torch_dtype=dtype,
        use_safetensors=True,
        variant="fp16" if dtype == torch.float16 else None,
    )
    # model_path is the assgen-managed cache dir; try it first to avoid a
    # network round-trip.  Fall back to HF hub (uses ~/.cache/huggingface/hub).
    model_path_ok = (
        model_path
        and Path(model_path).exists()
        and (Path(model_path) / "model_index.json").exists()
    )
    if model_path_ok:
        try:
            pipe = StableDiffusionXLPipeline.from_pretrained(
                model_path, local_files_only=True, **load_kwargs
            )
        except Exception:
            pipe = StableDiffusionXLPipeline.from_pretrained(resolved_model, **load_kwargs)
    else:
        pipe = StableDiffusionXLPipeline.from_pretrained(resolved_model, **load_kwargs)
    pipe = pipe.to("cpu") if device == "cpu" else pipe
    pipe.set_progress_bar_config(disable=True)

    # Sequential CPU offload moves one layer at a time to GPU — needs <1 GB VRAM.
    # Fall back to pure CPU if CUDA is not available.
    if device != "cpu":
        pipe.enable_sequential_cpu_offload()
    else:
        pipe = pipe.to(device)

    if hasattr(pipe, "enable_xformers_memory_efficient_attention"):
        try:
            pipe.enable_xformers_memory_efficient_attention()
        except Exception:
            pass

    generator = None
    if seed is not None:
        # After cpu_offload the pipeline manages device placement; use CPU generator.
        gen_device = "cpu" if device != "cpu" else device
        generator = torch.Generator(device=gen_device).manual_seed(int(seed))

    progress_cb(0.3, f"Generating {num_images} image(s) — {num_steps} steps…")

    kwargs: dict = dict(
        prompt=full_prompt,
        negative_prompt=negative_prompt,
        width=width,
        height=height,
        num_inference_steps=num_steps,
        num_images_per_prompt=num_images,
        generator=generator,
    )
    if not is_turbo:
        kwargs["guidance_scale"] = guidance_scale

    result = pipe(**kwargs)
    images = result.images

    progress_cb(0.9, "Saving images…")
    out_files = []
    for i, img in enumerate(images):
        suffix = f"_{i:02d}" if len(images) > 1 else ""
        out_path = Path(output_dir) / f"concept{suffix}.png"
        img.save(str(out_path))
        out_files.append(str(out_path))

    return {
        "files": out_files,
        "metadata": {
            "model": resolved_model,
            "prompt": full_prompt,
            "width": width,
            "height": height,
            "steps": num_steps,
            "guidance_scale": guidance_scale,
            "seed": seed,
            "count": len(out_files),
        },
    }
