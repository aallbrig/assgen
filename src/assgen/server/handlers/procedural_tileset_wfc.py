"""Handler for proc.tileset.wfc — Wave Function Collapse from a sample image.

Implements a simple overlapping WFC algorithm in pure Python.
Reads a sample image, extracts N×N tiles, learns adjacency constraints,
and synthesises a new output grid.

Outputs:
    wfc_output.png — synthesised tileset image
    wfc_map.json   — 2D tile ID array {width, height, tile_size, map: [[int]]}

Params:
    sample    (str): path to sample image
    width     (int): output grid width in tiles (default 20)
    height    (int): output grid height in tiles (default 20)
    tile_size (int): tile size in pixels (default 16)
    seed      (int): random seed (default 42)
"""
from __future__ import annotations

try:
    from PIL import Image  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Run Wave Function Collapse from a sample tileset image."""
    if not _AVAILABLE:
        raise RuntimeError("Pillow is not installed. Run: pip install Pillow")

    import json
    import random
    import numpy as np
    from pathlib import Path
    from PIL import Image

    sample_path = params.get("sample", "")
    if not Path(sample_path).exists():
        raise ValueError(f"Sample image not found: {sample_path}")

    out_w: int = int(params.get("width", 20))
    out_h: int = int(params.get("height", 20))
    tile_size: int = int(params.get("tile_size", 16))
    seed: int = int(params.get("seed", 42))

    rng = random.Random(seed)

    progress_cb(0.0, "Loading sample image")
    sample = Image.open(sample_path).convert("RGB")
    sw, sh = sample.size

    # Extract unique tiles
    tiles: list[np.ndarray] = []
    tile_lookup: dict[bytes, int] = {}

    def get_tile_id(arr: np.ndarray) -> int:
        key = arr.tobytes()
        if key not in tile_lookup:
            tile_lookup[key] = len(tiles)
            tiles.append(arr)
        return tile_lookup[key]

    progress_cb(0.1, "Extracting tiles")
    sample_arr = np.array(sample)
    tile_grid_w = sw // tile_size
    tile_grid_h = sh // tile_size

    sample_ids: list[list[int]] = []
    for ty in range(tile_grid_h):
        row: list[int] = []
        for tx in range(tile_grid_w):
            patch = sample_arr[ty * tile_size:(ty + 1) * tile_size,
                               tx * tile_size:(tx + 1) * tile_size]
            row.append(get_tile_id(patch))
        sample_ids.append(row)

    n_tiles = len(tiles)
    if n_tiles == 0:
        raise ValueError("No tiles could be extracted from the sample image")

    # Build adjacency rules from sample
    right_allowed: dict[int, set[int]] = {i: set() for i in range(n_tiles)}
    down_allowed: dict[int, set[int]] = {i: set() for i in range(n_tiles)}

    for ty in range(tile_grid_h):
        for tx in range(tile_grid_w):
            tid = sample_ids[ty][tx]
            if tx + 1 < tile_grid_w:
                right_allowed[tid].add(sample_ids[ty][tx + 1])
            if ty + 1 < tile_grid_h:
                down_allowed[tid].add(sample_ids[ty + 1][tx])

    # If any tile has no rules, allow all (fallback)
    for i in range(n_tiles):
        if not right_allowed[i]:
            right_allowed[i] = set(range(n_tiles))
        if not down_allowed[i]:
            down_allowed[i] = set(range(n_tiles))

    progress_cb(0.3, f"Running WFC ({out_w}×{out_h}, {n_tiles} tiles)")

    # Simple WFC with backtracking-free collapse (greedy, may leave collapsed = -1)
    grid: list[list[int]] = [[-1] * out_w for _ in range(out_h)]
    wave: list[list[set[int]]] = [[set(range(n_tiles)) for _ in range(out_w)] for _ in range(out_h)]

    def propagate(gy: int, gx: int, chosen: int) -> None:
        for nx in range(gx + 1, out_w):
            wave[gy][nx] &= right_allowed.get(grid[gy][nx - 1], set(range(n_tiles)))
            if not wave[gy][nx]:
                break
        for ny in range(gy + 1, out_h):
            wave[ny][gx] &= down_allowed.get(grid[ny - 1][gx], set(range(n_tiles)))
            if not wave[ny][gx]:
                break

    for gy in range(out_h):
        for gx in range(out_w):
            candidates = wave[gy][gx]
            if not candidates:
                candidates = set(range(n_tiles))
            chosen = rng.choice(sorted(candidates))
            grid[gy][gx] = chosen
            propagate(gy, gx, chosen)
        progress_cb(0.3 + 0.5 * (gy + 1) / out_h, "")

    progress_cb(0.82, "Rendering output image")
    out_img_arr = np.zeros((out_h * tile_size, out_w * tile_size, 3), dtype=np.uint8)
    for gy in range(out_h):
        for gx in range(out_w):
            tid = grid[gy][gx]
            if 0 <= tid < n_tiles:
                out_img_arr[gy * tile_size:(gy + 1) * tile_size,
                            gx * tile_size:(gx + 1) * tile_size] = tiles[tid]

    img_path = Path(output_dir) / "wfc_output.png"
    map_path = Path(output_dir) / "wfc_map.json"
    Image.fromarray(out_img_arr, "RGB").save(str(img_path))
    map_path.write_text(json.dumps({
        "width": out_w,
        "height": out_h,
        "tile_size": tile_size,
        "tile_count": n_tiles,
        "map": grid,
    }, indent=2))

    progress_cb(1.0, "Done")
    return {
        "files": [str(img_path), str(map_path)],
        "metadata": {
            "output_width": out_w,
            "output_height": out_h,
            "tile_size": tile_size,
            "unique_tiles": n_tiles,
            "seed": seed,
        },
    }
