"""Handler for proc.level.dungeon — BSP dungeon layout generator.

Generates a dungeon map using BSP (Binary Space Partitioning) or
cellular automata.  Pure Python — no external dependencies.

Outputs:
    dungeon.png  — greyscale bitmap (255=floor, 0=wall)
    dungeon.json — {rooms: [{x,y,w,h}], corridors: [{x1,y1,x2,y2}]}

Params:
    width     (int): grid width in tiles (default 64)
    height    (int): grid height in tiles (default 64)
    rooms     (int): target number of rooms for BSP (default 10)
    algorithm (str): "bsp" | "cellular" (default "bsp")
    seed      (int): random seed (default 42)
"""
from __future__ import annotations

import json
import random
from pathlib import Path

try:
    from PIL import Image  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


# ---------------------------------------------------------------------------
# BSP dungeon
# ---------------------------------------------------------------------------

def _bsp_dungeon(width: int, height: int, target_rooms: int, rng: random.Random):
    grid = [[0] * width for _ in range(height)]
    rooms: list[dict] = []
    corridors: list[dict] = []

    min_room = 5

    def split(x: int, y: int, w: int, h: int, depth: int):
        if depth <= 0 or len(rooms) >= target_rooms:
            # Leaf — carve a room
            room_w = rng.randint(min_room, max(min_room, w - 2))
            room_h = rng.randint(min_room, max(min_room, h - 2))
            rx = x + rng.randint(1, max(1, w - room_w - 1))
            ry = y + rng.randint(1, max(1, h - room_h - 1))
            rx = max(x + 1, min(rx, x + w - room_w - 1))
            ry = max(y + 1, min(ry, y + h - room_h - 1))
            rooms.append({"x": rx, "y": ry, "w": room_w, "h": room_h})
            for row in range(ry, ry + room_h):
                for col in range(rx, rx + room_w):
                    if 0 <= row < height and 0 <= col < width:
                        grid[row][col] = 1
            return (rx + room_w // 2, ry + room_h // 2)

        if w > h:
            split_x = x + rng.randint(w // 3, 2 * w // 3)
            c1 = split(x, y, split_x - x, h, depth - 1)
            c2 = split(split_x, y, x + w - split_x, h, depth - 1)
        else:
            split_y = y + rng.randint(h // 3, 2 * h // 3)
            c1 = split(x, y, w, split_y - y, depth - 1)
            c2 = split(x, split_y, w, y + h - split_y, depth - 1)

        if c1 and c2:
            corridors.append({"x1": c1[0], "y1": c1[1], "x2": c2[0], "y2": c2[1]})
            # Carve L-shaped corridor
            cx, cy = c1
            tx, ty = c2
            while cx != tx:
                step = 1 if cx < tx else -1
                cx += step
                if 0 <= cy < height and 0 <= cx < width:
                    grid[cy][cx] = 1
            while cy != ty:
                step = 1 if cy < ty else -1
                cy += step
                if 0 <= cy < height and 0 <= cx < width:
                    grid[cy][cx] = 1

        return c1 or c2

    depth = max(2, int(target_rooms ** 0.5))
    split(0, 0, width, height, depth)
    return grid, rooms, corridors


# ---------------------------------------------------------------------------
# Cellular automata dungeon
# ---------------------------------------------------------------------------

def _cellular_dungeon(width: int, height: int, rng: random.Random):
    # Initialise with 45% wall probability
    grid = [[0 if rng.random() > 0.45 else 1 for _ in range(width)] for _ in range(height)]

    def step(g):
        new_g = [[0] * width for _ in range(height)]
        for y in range(height):
            for x in range(width):
                walls = sum(
                    1
                    for dy in range(-1, 2)
                    for dx in range(-1, 2)
                    if (dx != 0 or dy != 0)
                    and 0 <= y + dy < height
                    and 0 <= x + dx < width
                    and g[y + dy][x + dx] == 0
                )
                new_g[y][x] = 0 if walls >= 5 else 1
        return new_g

    for _ in range(5):
        grid = step(grid)

    # Invert: 1=floor, 0=wall
    grid = [[1 - grid[y][x] for x in range(width)] for y in range(height)]
    return grid, [], []


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Generate a procedural dungeon layout."""
    if not _AVAILABLE:
        raise RuntimeError("Pillow is not installed. Run: pip install Pillow")

    import numpy as np
    from PIL import Image

    width: int = int(params.get("width", 64))
    height: int = int(params.get("height", 64))
    target_rooms: int = int(params.get("rooms", 10))
    algorithm: str = params.get("algorithm", "bsp").lower()
    seed: int = int(params.get("seed", 42))

    rng = random.Random(seed)
    progress_cb(0.0, f"Generating {algorithm} dungeon ({width}×{height})")

    if algorithm == "cellular":
        grid, rooms, corridors = _cellular_dungeon(width, height, rng)
    else:
        grid, rooms, corridors = _bsp_dungeon(width, height, target_rooms, rng)

    progress_cb(0.7, "Saving outputs")
    arr = np.array(grid, dtype=np.uint8) * 255
    img_path = Path(output_dir) / "dungeon.png"
    Image.fromarray(arr, "L").save(str(img_path))

    data = {"rooms": rooms, "corridors": corridors}
    json_path = Path(output_dir) / "dungeon.json"
    json_path.write_text(json.dumps(data, indent=2))

    progress_cb(1.0, "Done")
    return {
        "files": [str(img_path), str(json_path)],
        "metadata": {
            "width": width,
            "height": height,
            "algorithm": algorithm,
            "room_count": len(rooms),
            "corridor_count": len(corridors),
            "seed": seed,
        },
    }
