"""visual.ui.iconset — themed icon pack generation via SDXL + IP-Adapter style lock.

Generates a batch of N icons sharing a consistent visual language by using
IP-Adapter to lock the style from a reference icon image.

  pip install diffusers transformers accelerate torch Pillow

Params:
    prompt          (str):  base icon theme, e.g. "fantasy RPG inventory icons"
    icon_names      (list|str): specific icon names, e.g. ["sword","shield","potion"]
                              or comma-separated string; if omitted, generates generic set
    style_image     (str):  optional path to a reference icon for style-locking
    count           (int):  number of icons if icon_names not given (default: 8)
    size            (int):  icon size in pixels, square (default: 128)
    steps           (int):  inference steps (default: 25)
    ip_adapter_scale (float): style influence when style_image provided (default: 0.7)
    output_dir_name (str):  sub-folder name inside job output dir (default: iconset)
"""
from __future__ import annotations

try:
    from diffusers import StableDiffusionXLPipeline  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Generate a coherent themed icon set."""
    if not _AVAILABLE:
        raise RuntimeError(
            "diffusers is required. Run: pip install diffusers transformers accelerate torch"
        )

    import torch
    from pathlib import Path
    from PIL import Image
    from diffusers import StableDiffusionXLPipeline

    prompt = params.get("prompt", "")
    if not prompt:
        raise ValueError("'prompt' is required")

    raw_names = params.get("icon_names") or []
    if isinstance(raw_names, str):
        raw_names = [n.strip() for n in raw_names.split(",") if n.strip()]
    count = int(params.get("count", 8))
    icon_list = raw_names if raw_names else [f"icon_{i+1}" for i in range(count)]

    style_image_path = params.get("style_image", "")
    size = int(params.get("size", 128))
    size = max(8, size - (size % 8))
    steps = int(params.get("steps", 25))
    ip_scale = float(params.get("ip_adapter_scale", 0.7))
    sub_dir_name = params.get("output_dir_name") or "iconset"
    out_dir = Path(output_dir) / sub_dir_name
    out_dir.mkdir(parents=True, exist_ok=True)

    has_style = bool(style_image_path) and Path(style_image_path).exists()

    progress_cb(0.05, "Loading SDXL pipeline…")
    hf_id = model_path or model_id or "stabilityai/stable-diffusion-xl-base-1.0"
    dtype = torch.float16 if device != "cpu" else torch.float32
    pipe = StableDiffusionXLPipeline.from_pretrained(hf_id, torch_dtype=dtype).to(device)

    if has_style:
        progress_cb(0.1, "Loading IP-Adapter for style consistency…")
        try:
            pipe.load_ip_adapter("h94/IP-Adapter", subfolder="sdxl_models", weight_name="ip-adapter_sdxl.bin")
            pipe.set_ip_adapter_scale(ip_scale)
        except Exception:
            has_style = False  # graceful fallback

    style_img = Image.open(style_image_path).convert("RGB") if has_style else None

    out_files: list[str] = []
    negative = "background, frame, clutter, text, watermark"

    for i, name in enumerate(icon_list):
        progress_cb(0.15 + 0.8 * (i / len(icon_list)), f"Generating icon: {name}…")
        icon_prompt = f"{prompt}, {name}, flat icon, isolated, transparent background, game asset"

        kwargs = {"ip_adapter_image": style_img} if style_img else {}
        image = pipe(
            prompt=icon_prompt,
            negative_prompt=negative,
            num_inference_steps=steps,
            width=size,
            height=size,
            **kwargs,
        ).images[0]

        safe_name = name.replace(" ", "_").replace("/", "_")
        file_name = f"{sub_dir_name}/{safe_name}.png"
        image.save(str(Path(output_dir) / file_name))
        out_files.append(file_name)

    progress_cb(1.0, "Done")
    return {
        "files": out_files,
        "metadata": {
            "count": len(icon_list),
            "size": size,
            "style_locked": has_style,
        },
    }
