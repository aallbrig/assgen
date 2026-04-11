"""Handler for proc.foliage.scatter — Poisson disk foliage scatter.

Reads a greyscale density map and scatters instance positions using
Poisson disk sampling weighted by pixel brightness.

Outputs:
    positions.json — {positions: [[x, y, z], ...]}

Params:
    density_map (str):   path to greyscale PNG density image
    count       (int):   maximum number of scatter points (default 100)
    min_dist    (float): minimum distance between points in normalised [0,1] space (default 1.0 / sqrt(count))
    seed        (int):   random seed (default 42)
"""
from __future__ import annotations

try:
    from PIL import Image  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def _poisson_disk_sample(
    density: list,
    count: int,
    min_dist: float,
    rng: object,
) -> list:
    """Simple rejection-sampling Poisson disk using a density map."""
    h, w = density.shape
    placed: list[tuple[float, float]] = []
    max_attempts = count * 30

    for _ in range(max_attempts):
        if len(placed) >= count:
            break
        x = float(rng.random())
        y = float(rng.random())
        px = int(x * (w - 1))
        py = int(y * (h - 1))
        prob = float(density[py, px]) / 255.0
        if rng.random() > prob:
            continue
        # Check minimum distance
        too_close = any(
            (x - ox) ** 2 + (y - oy) ** 2 < (min_dist / 100.0) ** 2
            for ox, oy in placed
        )
        if not too_close:
            placed.append((x, y))

    return placed


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Scatter foliage instances using a density map."""
    if not _AVAILABLE:
        raise RuntimeError("Pillow is not installed. Run: pip install Pillow")

    import json
    from pathlib import Path

    import numpy as np
    from PIL import Image

    density_map_path = params.get("density_map", "")
    if not Path(density_map_path).exists():
        raise ValueError(f"Density map not found: {density_map_path}")

    count: int = int(params.get("count", 100))
    seed: int = int(params.get("seed", 42))
    min_dist: float = float(params.get("min_dist", max(0.1, 100.0 / max(1, count))))

    rng = np.random.default_rng(seed)

    progress_cb(0.0, "Loading density map")
    density = np.array(Image.open(density_map_path).convert("L"))

    progress_cb(0.2, f"Scattering {count} points (min_dist={min_dist:.2f})")

    try:
        from scipy.spatial import cKDTree  # type: ignore
        _SCIPY = True
    except ImportError:
        _SCIPY = False

    if _SCIPY:
        # Weighted random sampling using density as probability
        h, w = density.shape
        probs = density.ravel().astype(np.float32)
        probs /= probs.sum() + 1e-10
        flat_indices = rng.choice(len(probs), size=min(count * 5, len(probs)),
                                  replace=False, p=probs)
        ys = (flat_indices // w).astype(float) / h
        xs = (flat_indices % w).astype(float) / w
        raw_pts = np.stack([xs, ys], axis=1)

        placed: list[list[float]] = []
        tree_pts: list[list[float]] = []
        for pt in raw_pts:
            if len(placed) >= count:
                break
            if tree_pts:
                tree = cKDTree(tree_pts)
                d, _ = tree.query(pt.reshape(1, 2), k=1)
                if d[0] < min_dist / 100.0:
                    continue
            placed.append([float(pt[0]), float(pt[1]), 0.0])
            tree_pts.append(pt.tolist())
            progress_cb(0.2 + 0.6 * len(placed) / count, "")
    else:
        raw = _poisson_disk_sample(density, count, min_dist, rng)
        placed = [[float(x), float(y), 0.0] for x, y in raw]

    progress_cb(0.85, "Saving positions")
    out_path = Path(output_dir) / "positions.json"
    out_path.write_text(json.dumps({"positions": placed}, indent=2))

    progress_cb(1.0, "Done")
    return {
        "files": [str(out_path)],
        "metadata": {
            "point_count": len(placed),
            "requested_count": count,
            "min_dist": min_dist,
            "seed": seed,
        },
    }
