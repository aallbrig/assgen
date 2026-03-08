"""Handler for visual.texture.pbr — algorithmic PBR map derivation.

Derives a full PBR material set (normal, roughness, metallic, AO, height)
from an input albedo image using gradient and luminance analysis.

No ML model required — uses numpy and Pillow (already in ``[inference]`` extras).
scipy is used for Sobel filtering if available; falls back to a pure-numpy
central-difference approximation otherwise.

Input param: ``albedo`` (str) — path to the source albedo/diffuse PNG or JPEG.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

try:
    from scipy.ndimage import convolve, uniform_filter
    _SCIPY_AVAILABLE = True
except ImportError:
    _SCIPY_AVAILABLE = False


ProgressCallback = Callable[[float, str], None]


def _to_gray(rgb: Any) -> Any:
    """Convert uint8 RGB (H, W, C) → float32 luminance (H, W) in [0, 1]."""
    import numpy as np
    weights = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    return (rgb[:, :, :3].astype(np.float32) / 255.0) @ weights


def _convolve2d(image: Any, kernel: Any) -> Any:
    """2-D convolution; uses scipy if available, otherwise numpy-based loop."""
    import numpy as np
    if _SCIPY_AVAILABLE:
        return convolve(image, kernel, mode="reflect")
    kh, kw = kernel.shape
    ph, pw = kh // 2, kw // 2
    padded = np.pad(image, ((ph, ph), (pw, pw)), mode="reflect")
    out = np.zeros_like(image)
    for i in range(kh):
        for j in range(kw):
            out += kernel[i, j] * padded[i:i + image.shape[0], j:j + image.shape[1]]
    return out


def _make_normal_map(gray: Any, strength: float = 2.0) -> Any:
    """Derive a tangent-space normal map from a grayscale height field.

    Returns uint8 RGB array with normals encoded in [0, 255].
    """
    import numpy as np
    sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32)
    sobel_y = np.array([[1, 2, 1], [0, 0, 0], [-1, -2, -1]], dtype=np.float32)
    gx = _convolve2d(gray, sobel_x)
    gy = _convolve2d(gray, sobel_y)

    nx = -gx * strength
    ny = -gy * strength
    nz = np.ones_like(nx)

    length = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2) + 1e-8
    nx /= length
    ny /= length
    nz /= length

    rgb = np.stack(
        [(nx + 1.0) * 127.5, (ny + 1.0) * 127.5, (nz + 1.0) * 127.5],
        axis=2,
    ).clip(0, 255).astype(np.uint8)
    return rgb


def _make_roughness_map(gray: Any) -> Any:
    """Derive roughness from inverse luminance (bright → smooth, dark → rough)."""
    import numpy as np
    return ((1.0 - gray) * 255).clip(0, 255).astype(np.uint8)


def _make_metallic_map(gray: Any, threshold: float = 0.72) -> Any:
    """Rough metallic estimate: very bright, low-variance regions → metallic."""
    import numpy as np
    if _SCIPY_AVAILABLE:
        local_mean = uniform_filter(gray, size=9)
        local_sq = uniform_filter(gray ** 2, size=9)
        variance = np.clip(local_sq - local_mean ** 2, 0, None)
    else:
        variance = np.abs(gray - gray.mean())
    return np.where((gray > threshold) & (variance < 0.02), 255, 0).astype(np.uint8)


def _make_ao_map(gray: Any) -> Any:
    """Estimate ambient occlusion from local darkness (crevices/cavities)."""
    import numpy as np
    if _SCIPY_AVAILABLE:
        local_mean = uniform_filter(gray, size=19)
    else:
        local_mean = np.full_like(gray, gray.mean())
    ao = np.clip(local_mean * 1.3, 0.0, 1.0)
    return (ao * 255).astype(np.uint8)


def _make_height_map(gray: Any) -> Any:
    """Height map: direct grayscale luminance."""
    import numpy as np
    return (gray * 255).astype(np.uint8)


def run(
    job_type: str,
    params: dict[str, Any],
    model_id: str | None,
    model_path: str | None,
    device: str,
    progress_cb: ProgressCallback,
    output_dir: Path,
) -> dict[str, Any]:
    """Derive a full PBR map set from an albedo image."""
    import numpy as np
    from PIL import Image
    albedo_path_str: str | None = params.get("albedo") or params.get("prompt")
    if not albedo_path_str:
        raise ValueError("visual.texture.pbr requires an 'albedo' param pointing to the source image.")

    albedo_path = Path(albedo_path_str)
    if not albedo_path.exists():
        # Try to resolve relative to the upstream job's output directory
        upstream_id = params.get("upstream_job_id")
        if upstream_id:
            from assgen.config import get_outputs_dir
            candidate = get_outputs_dir() / upstream_id / albedo_path.name
            if candidate.exists():
                albedo_path = candidate

    if not albedo_path.exists():
        raise FileNotFoundError(f"Albedo image not found: {albedo_path_str!r}")

    requested_maps: list[str] = params.get("maps") or ["normal", "roughness", "metallic", "ao", "height"]
    normal_strength: float = float(params.get("normal_strength", 2.0))
    resolution: int | None = params.get("resolution")

    progress_cb(0.20, "Loading albedo image…")
    img = Image.open(albedo_path).convert("RGB")
    if resolution:
        img = img.resize((resolution, resolution), Image.LANCZOS)
    rgb = np.array(img, dtype=np.uint8)
    gray = _to_gray(rgb)

    # Copy the albedo into the output dir so the full set is co-located
    import shutil
    albedo_out = output_dir / "albedo.png"
    shutil.copy2(albedo_path, albedo_out)

    progress_cb(0.30, "Deriving PBR maps…")
    saved = ["albedo.png"]

    generators = {
        "normal":    lambda: (_make_normal_map(gray, normal_strength), "normal.png",    "RGB"),
        "roughness": lambda: (_make_roughness_map(gray),               "roughness.png", "L"),
        "metallic":  lambda: (_make_metallic_map(gray),                "metallic.png",  "L"),
        "ao":        lambda: (_make_ao_map(gray),                      "ao.png",        "L"),
        "height":    lambda: (_make_height_map(gray),                  "height.png",    "L"),
    }

    step_size = 0.55 / max(len(requested_maps), 1)
    for i, map_name in enumerate(requested_maps):
        gen = generators.get(map_name)
        if gen is None:
            continue
        progress_cb(0.30 + i * step_size, f"Generating {map_name} map…")
        data, filename, mode = gen()
        if mode == "L":
            pil_img = Image.fromarray(data, mode="L")
        else:
            pil_img = Image.fromarray(data, mode="RGB")
        out_file = output_dir / filename
        pil_img.save(out_file, format="PNG")
        saved.append(filename)

    progress_cb(0.92, "Writing material manifest…")
    manifest = {
        "albedo":    "albedo.png",
        "maps_generated": requested_maps,
    }
    for name in requested_maps:
        if name in generators:
            manifest[name] = f"{name}.png"
    manifest_path = output_dir / "material.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    saved.append("material.json")

    progress_cb(1.0, "PBR map generation complete")
    return {
        "files": saved,
        "metadata": {
            "source_albedo": str(albedo_path),
            "maps": requested_maps,
            "resolution": resolution,
            "normal_strength": normal_strength,
        },
    }
