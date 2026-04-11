"""Handler for proc.terrain.heightmap — procedural heightmap generation.

Generates a greyscale PNG heightmap using Perlin/fractal/ridged noise.
Library: noise (pip install noise). Falls back to a pure-numpy fallback
if noise is not installed.

Params:
    width   (int):   output width in pixels (default 512)
    height  (int):   output height in pixels (default 512)
    type    (str):   "perlin" | "fractal" | "ridged" (default "fractal")
    seed    (int):   random seed (default 42)
    scale   (float): noise coordinate scale factor (default 100.0)
    octaves (int):   fractal octave count (default 6)
"""
from __future__ import annotations

try:
    from PIL import Image  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def _numpy_noise(w: int, h: int, seed: int, scale: float, octaves: int):
    """Minimal fractal noise using numpy only (no external noise library)."""
    import numpy as np
    rng = np.random.default_rng(seed)
    result = np.zeros((h, w), dtype=np.float32)
    amplitude = 1.0
    frequency = 1.0
    max_val = 0.0
    for _ in range(octaves):
        noise_h = max(2, int(h * frequency / scale) + 2)
        noise_w = max(2, int(w * frequency / scale) + 2)
        base = rng.random((noise_h, noise_w)).astype(np.float32)
        # Upsample via zoom
        from PIL import Image as _PILImage
        zoomed = np.array(
            _PILImage.fromarray(base).resize((w, h), _PILImage.BILINEAR)
        )
        result += zoomed * amplitude
        max_val += amplitude
        amplitude *= 0.5
        frequency *= 2.0
    return result / max_val


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Generate a procedural heightmap PNG."""
    if not _AVAILABLE:
        raise RuntimeError("Pillow is not installed. Run: pip install Pillow")

    from pathlib import Path

    import numpy as np
    from PIL import Image

    width: int = int(params.get("width", 512))
    height: int = int(params.get("height", 512))
    noise_type: str = params.get("type", "fractal").lower()
    seed: int = int(params.get("seed", 42))
    scale: float = float(params.get("scale", 100.0))
    octaves: int = int(params.get("octaves", 6))

    try:
        import noise as _noise
        _NOISE_LIB = True
    except ImportError:
        _NOISE_LIB = False

    progress_cb(0.0, f"Generating {noise_type} heightmap ({width}×{height})")

    if _NOISE_LIB:
        import noise as _noise
        arr = np.zeros((height, width), dtype=np.float32)
        for y in range(height):
            ny = (y / height * scale + seed * 777.0) / scale
            for x in range(width):
                nx = (x / width * scale + seed * 1000.0) / scale
                if noise_type == "ridged":
                    val = 1.0 - abs(_noise.pnoise2(nx, ny, octaves=octaves,
                                                    repeatx=width, repeaty=height))
                else:  # fractal (fBm) or perlin
                    val = _noise.pnoise2(nx, ny, octaves=octaves,
                                         persistence=0.5, lacunarity=2.0,
                                         repeatx=width, repeaty=height)
                arr[y, x] = val
            progress_cb(0.05 + 0.85 * (y + 1) / height, "")
    else:
        progress_cb(0.1, "noise library not found — using numpy fallback")
        arr = _numpy_noise(width, height, seed, scale, octaves)
        if noise_type == "ridged":
            arr = 1.0 - np.abs(arr * 2 - 1)

    progress_cb(0.9, "Normalising and saving")
    lo, hi = arr.min(), arr.max()
    if hi > lo:
        arr = (arr - lo) / (hi - lo)
    img_arr = (arr * 255).astype(np.uint8)
    out_path = Path(output_dir) / "heightmap.png"
    Image.fromarray(img_arr, "L").save(str(out_path))

    progress_cb(1.0, "Done")
    return {
        "files": [str(out_path)],
        "metadata": {
            "width": width,
            "height": height,
            "type": noise_type,
            "seed": seed,
            "scale": scale,
            "octaves": octaves,
            "backend": "noise" if _NOISE_LIB else "numpy",
        },
    }
