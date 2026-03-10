"""Handler for proc.texture.noise — tileable noise texture generation.

Generates a tileable greyscale (or RGBA) noise texture.
Library: noise (pip install noise). Voronoi mode uses scipy if available.

Params:
    width      (int):   output width in pixels (default 512)
    height     (int):   output height in pixels (default 512)
    noise_type (str):   "perlin" | "voronoi" | "fbm" (default "fbm")
    seed       (int):   random seed (default 42)
    scale      (float): noise coordinate scale factor (default 100.0)
    octaves    (int):   octave count for fBm/perlin (default 6)
"""
from __future__ import annotations

try:
    from PIL import Image  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Generate a tileable noise texture PNG."""
    if not _AVAILABLE:
        raise RuntimeError("Pillow is not installed. Run: pip install Pillow")

    import numpy as np
    from pathlib import Path
    from PIL import Image

    width: int = int(params.get("width", 512))
    height: int = int(params.get("height", 512))
    noise_type: str = params.get("noise_type", "fbm").lower()
    seed: int = int(params.get("seed", 42))
    scale: float = float(params.get("scale", 100.0))
    octaves: int = int(params.get("octaves", 6))

    rng = np.random.default_rng(seed)
    arr = np.zeros((height, width), dtype=np.float32)

    progress_cb(0.0, f"Generating {noise_type} noise ({width}×{height})")

    if noise_type == "voronoi":
        try:
            from scipy.spatial import Voronoi, cKDTree  # type: ignore
            n_pts = max(10, width * height // 2000)
            pts = rng.random((n_pts, 2)) * np.array([width, height])
            tree = cKDTree(pts)
            ys, xs = np.mgrid[0:height, 0:width]
            coords = np.stack([xs.ravel(), ys.ravel()], axis=1).astype(float)
            dists, _ = tree.query(coords, k=1)
            arr = dists.reshape(height, width).astype(np.float32)
            progress_cb(0.8, "Voronoi computed")
        except ImportError:
            # Pure-python fallback: random scattered cells
            n_pts = max(10, width * height // 4000)
            pts = rng.random((n_pts, 2)) * np.array([width, height])
            ys, xs = np.mgrid[0:height, 0:width]
            arr_min = np.full((height, width), float("inf"), dtype=np.float32)
            for px, py in pts:
                d = np.sqrt((xs - px) ** 2 + (ys - py) ** 2)
                arr_min = np.minimum(arr_min, d)
            arr = arr_min
    else:
        try:
            import noise as _noise
            for y in range(height):
                for x in range(width):
                    nx = (x / width * scale + seed * 100.0) / scale
                    ny = (y / height * scale + seed * 77.0) / scale
                    if noise_type == "perlin":
                        arr[y, x] = _noise.pnoise2(nx, ny, octaves=1,
                                                    repeatx=width, repeaty=height)
                    else:  # fbm
                        arr[y, x] = _noise.pnoise2(nx, ny, octaves=octaves,
                                                    persistence=0.5, lacunarity=2.0,
                                                    repeatx=width, repeaty=height)
                if y % 64 == 0:
                    progress_cb(0.05 + 0.8 * (y + 1) / height, "")
        except ImportError:
            # Numpy fallback: sum of random bilinearly-interpolated grids
            amplitude, frequency = 1.0, 1.0
            max_val = 0.0
            for _oct in range(octaves):
                gw = max(2, int(width * frequency / scale) + 2)
                gh = max(2, int(height * frequency / scale) + 2)
                base = rng.random((gh, gw)).astype(np.float32)
                zoomed = np.array(
                    Image.fromarray(base).resize((width, height), Image.BILINEAR)
                )
                arr += zoomed * amplitude
                max_val += amplitude
                amplitude *= 0.5
                frequency *= 2.0
            arr /= max_val

    progress_cb(0.9, "Normalising and saving")
    lo, hi = arr.min(), arr.max()
    if hi > lo:
        arr = (arr - lo) / (hi - lo)
    img_arr = (arr * 255).astype(np.uint8)
    out_path = Path(output_dir) / "noise_texture.png"
    Image.fromarray(img_arr, "L").save(str(out_path))

    progress_cb(1.0, "Done")
    return {
        "files": [str(out_path)],
        "metadata": {
            "width": width,
            "height": height,
            "noise_type": noise_type,
            "seed": seed,
        },
    }
