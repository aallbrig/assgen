"""visual.ui.button — styled game button / control generation via SDXL.

Generates isolated PNG button/control assets with transparent backgrounds,
optionally in multiple state variants, DPI scales, and with 9-slice metadata.

  pip install diffusers transformers accelerate torch Pillow

Params:
    prompt          (str):   button description, e.g. "medieval stone button START"
    style           (str):   visual style hint, e.g. "flat", "pixel-art", "3d-embossed"
    width           (int):   output width in px at base (1x) scale (default: 256)
    height          (int):   output height in px at base (1x) scale (default: 128)
    states          (list):  state variants to generate (default: ["normal"])
                             choices: normal|hover|pressed|disabled|focused|selected|locked
    steps           (int):   inference steps (default: 25)
    nine_slice      (str):   "auto" → emit .meta.json sidecar with inset margins;
                             "off" → no metadata (default: "off")
    nine_slice_inset (int):  border inset in px for auto 9-slice (default: 16% of min(w,h))
    dpi             (str):   comma-separated scale multipliers, e.g. "1x,2x,3x"
                             base image is generated at the highest requested scale
                             and downsampled for the rest (default: "1x")
    greyscale_base  (bool):  convert output to greyscale+alpha so engine can tint at
                             runtime (default: False)
    output          (str):   output filename stem (default: button)
"""
from __future__ import annotations
import json

try:
    from diffusers import StableDiffusionXLPipeline  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False

# Prompt modifiers per state — appended to the base prompt before inference
_STATE_MODIFIERS: dict[str, str] = {
    "normal":   "",
    "hover":    ", soft glow highlight, slightly lighter tone",
    "pressed":  ", darker, depressed inset, inner shadow, pushed down",
    "disabled": ", greyscale, desaturated, flat, low contrast, muted",
    "focused":  ", bright outline border, keyboard focus ring, glowing edge",
    "selected": ", strongly lit, toggled-on, active state, highlighted fill",
    "locked":   ", desaturated, dark overlay, padlock motif, inaccessible look",
}


def _parse_dpi_scales(raw: str | None) -> list[int]:
    """Parse "1x,2x,3x" → [1, 2, 3], deduplicated and sorted descending."""
    if not raw:
        return [1]
    scales: list[int] = []
    for token in str(raw).split(","):
        token = token.strip().lower().rstrip("x")
        try:
            scales.append(int(token))
        except ValueError:
            pass
    return sorted(set(scales or [1]), reverse=True)


def _nine_slice_insets(width: int, height: int, override: int | None) -> dict[str, int]:
    """Return sensible 9-slice border insets (≈16 % of shortest edge, min 4 px)."""
    if override is not None:
        v = max(4, int(override))
        return {"left": v, "right": v, "top": v, "bottom": v}
    inset = max(4, int(min(width, height) * 0.16))
    return {"left": inset, "right": inset, "top": inset, "bottom": inset}


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Generate styled game button assets with state variants, DPI scales, and 9-slice metadata."""
    if not _AVAILABLE:
        raise RuntimeError(
            "diffusers is required. Run: pip install diffusers transformers accelerate torch"
        )

    import torch
    from pathlib import Path
    from PIL import Image, ImageOps
    from diffusers import StableDiffusionXLPipeline

    prompt = params.get("prompt", "")
    if not prompt:
        raise ValueError("'prompt' is required")

    style          = params.get("style", "")
    base_width     = max(8, int(params.get("width", 256)))
    base_height    = max(8, int(params.get("height", 128)))
    # snap to multiples of 8 (SDXL requirement)
    base_width  -= base_width  % 8
    base_height -= base_height % 8

    raw_states = params.get("states") or ["normal"]
    if isinstance(raw_states, str):
        raw_states = [s.strip() for s in raw_states.split(",")]
    valid_states = [s for s in raw_states if s in _STATE_MODIFIERS]
    if not valid_states:
        valid_states = ["normal"]

    steps          = int(params.get("steps", 25))
    nine_slice     = str(params.get("nine_slice", "off")).lower()
    ns_inset_raw   = params.get("nine_slice_inset")
    ns_override    = int(ns_inset_raw) if ns_inset_raw is not None else None
    dpi_scales     = _parse_dpi_scales(params.get("dpi", "1x"))
    greyscale_base = bool(params.get("greyscale_base", False))
    out_stem       = params.get("output") or "button"
    out_dir        = Path(output_dir)
    multi_state    = len(valid_states) > 1

    # Generate at the highest requested DPI scale, then downsample
    max_scale   = dpi_scales[0]
    gen_width   = base_width  * max_scale
    gen_height  = base_height * max_scale
    # keep snapped to 8 after scaling
    gen_width  -= gen_width  % 8
    gen_height -= gen_height % 8

    progress_cb(0.05, "Loading SDXL pipeline…")
    hf_id  = model_path or model_id or "stabilityai/stable-diffusion-xl-base-1.0"
    dtype  = torch.float16 if device != "cpu" else torch.float32
    pipe   = StableDiffusionXLPipeline.from_pretrained(hf_id, torch_dtype=dtype).to(device)

    style_tag   = f", {style} style" if style else ""
    base_prompt = (
        f"{prompt}{style_tag}, game UI button, isolated on transparent background, "
        "clean sharp edges, no background, no text, PNG asset"
    )
    negative = "background, scenery, clutter, text, watermark, frame, border"

    out_files: list[str] = []
    all_meta:  list[dict] = []
    n = len(valid_states)

    for i, state in enumerate(valid_states):
        modifier    = _STATE_MODIFIERS[state]
        full_prompt = base_prompt + modifier
        progress_cb(0.1 + 0.75 * (i / n), f"Generating '{state}' state…")

        image = pipe(
            prompt=full_prompt,
            negative_prompt=negative,
            num_inference_steps=steps,
            width=gen_width,
            height=gen_height,
        ).images[0]

        if greyscale_base:
            # Preserve alpha channel while converting RGB to greyscale
            grey = ImageOps.grayscale(image.convert("RGB"))
            if image.mode == "RGBA":
                alpha = image.split()[3]
                image = Image.merge("LA", (grey, alpha)).convert("RGBA")
            else:
                image = grey.convert("RGBA")

        state_suffix = f"_{state}" if multi_state else ""

        for scale in dpi_scales:
            scale_suffix = f"@{scale}x" if len(dpi_scales) > 1 else ""
            fname = f"{out_stem}{state_suffix}{scale_suffix}.png"

            if scale == max_scale:
                save_img = image
            else:
                w = max(1, base_width  * scale)
                h = max(1, base_height * scale)
                save_img = image.resize((w, h), Image.LANCZOS)

            save_img.save(str(out_dir / fname))
            out_files.append(fname)

            if nine_slice == "auto":
                sw, sh    = save_img.size
                insets    = _nine_slice_insets(sw, sh, ns_override)
                meta_name = fname.replace(".png", ".meta.json")
                meta_obj  = {"file": fname, "nine_slice": insets}
                (out_dir / meta_name).write_text(json.dumps(meta_obj, indent=2))
                out_files.append(meta_name)
                all_meta.append(meta_obj)

    progress_cb(1.0, "Done")
    metadata: dict = {
        "base_width":     base_width,
        "base_height":    base_height,
        "states":         valid_states,
        "dpi_scales":     dpi_scales,
        "greyscale_base": greyscale_base,
    }
    if nine_slice == "auto":
        metadata["nine_slice"] = all_meta
    return {"files": out_files, "metadata": metadata}
