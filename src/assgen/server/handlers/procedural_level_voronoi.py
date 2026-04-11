"""Handler for proc.level.voronoi — Voronoi region map generator.

Generates a colour-coded Voronoi region map image and a regions JSON.
Uses scipy if available, falls back to a pure-Python implementation.

Outputs:
    voronoi.png   — colour map image
    regions.json  — {regions: [{id, seed_x, seed_y, color}]}

Params:
    width   (int): output width in pixels (default 512)
    height  (int): output height in pixels (default 512)
    regions (int): number of Voronoi regions (default 12)
    seed    (int): random seed (default 42)
"""
from __future__ import annotations

try:
    from PIL import Image  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Generate a Voronoi region map."""
    if not _AVAILABLE:
        raise RuntimeError("Pillow is not installed. Run: pip install Pillow")

    import json
    from pathlib import Path

    import numpy as np
    from PIL import Image

    width: int = int(params.get("width", 512))
    height: int = int(params.get("height", 512))
    n_regions: int = int(params.get("regions", 12))
    seed: int = int(params.get("seed", 42))

    rng = np.random.default_rng(seed)
    points = rng.random((n_regions, 2)) * np.array([width, height])
    colors = rng.integers(50, 230, size=(n_regions, 3), dtype=np.uint8)

    progress_cb(0.0, f"Computing Voronoi ({width}×{height}, {n_regions} regions)")

    # Build pixel → nearest seed index
    ys, xs = np.mgrid[0:height, 0:width]
    coords = np.stack([xs.ravel(), ys.ravel()], axis=1).astype(np.float32)

    try:
        from scipy.spatial import cKDTree  # type: ignore
        tree = cKDTree(points)
        _, indices = tree.query(coords, k=1)
        indices = indices.reshape(height, width)
        progress_cb(0.6, "KD-tree query complete")
    except ImportError:
        # Pure-numpy brute-force (slow for large images; fine for ≤512)
        pts = points.astype(np.float32)
        dists = np.full((height * width, n_regions), np.inf, dtype=np.float32)
        for i, (px, py) in enumerate(pts):
            dists[:, i] = (coords[:, 0] - px) ** 2 + (coords[:, 1] - py) ** 2
        indices = np.argmin(dists, axis=1).reshape(height, width)
        progress_cb(0.6, "Brute-force Voronoi complete")

    progress_cb(0.7, "Painting regions")
    img_arr = colors[indices]
    img = Image.fromarray(img_arr.astype(np.uint8), "RGB")

    # Draw region seed points
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    for px, py in points:
        draw.ellipse(
            [int(px) - 3, int(py) - 3, int(px) + 3, int(py) + 3],
            fill=(255, 255, 255),
        )

    progress_cb(0.9, "Saving outputs")
    img_path = Path(output_dir) / "voronoi.png"
    json_path = Path(output_dir) / "regions.json"
    img.save(str(img_path))

    regions_data = [
        {
            "id": int(i),
            "seed_x": float(points[i, 0]),
            "seed_y": float(points[i, 1]),
            "color": [int(colors[i, 0]), int(colors[i, 1]), int(colors[i, 2])],
        }
        for i in range(n_regions)
    ]
    json_path.write_text(json.dumps({"regions": regions_data}, indent=2))

    progress_cb(1.0, "Done")
    return {
        "files": [str(img_path), str(json_path)],
        "metadata": {
            "width": width,
            "height": height,
            "region_count": n_regions,
            "seed": seed,
        },
    }
