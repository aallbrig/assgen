"""Handler for visual.texture.atlas_pack — pack images into a texture atlas.

Packs N images into a single atlas and outputs a UV manifest JSON.
Uses rectpack if available, else falls back to simple row-based packing.

Params:
    inputs  (list[str]): list of image paths
    size    (str): atlas dimensions, e.g. "2048x2048" (default "2048x2048")
"""
from __future__ import annotations

try:
    from PIL import Image  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Pack multiple images into a single texture atlas."""
    if not _AVAILABLE:
        raise RuntimeError("Pillow is not installed. Run: pip install Pillow")

    import json
    from pathlib import Path
    from PIL import Image

    inputs = params.get("inputs", [])
    if not inputs:
        raise ValueError("'inputs' must be a non-empty list of image paths")

    size_str = params.get("size", "2048x2048")
    try:
        atlas_w, atlas_h = (int(v) for v in size_str.lower().split("x"))
    except Exception:
        raise ValueError(f"Invalid 'size' format — expected WxH e.g. '2048x2048', got '{size_str}'")

    for p in inputs:
        if not Path(p).exists():
            raise ValueError(f"Input image not found: {p}")

    progress_cb(0.0, "Loading images")
    images = [(Path(p).stem, Image.open(p).convert("RGBA")) for p in inputs]

    # Try rectpack for bin-packing
    try:
        import rectpack  # type: ignore
        _RECTPACK = True
    except ImportError:
        _RECTPACK = False

    uv_map: list[dict] = []

    if _RECTPACK:
        packer = rectpack.newPacker(rotation=False)
        for name, img in images:
            packer.add_rect(img.width, img.height, name)
        packer.add_bin(atlas_w, atlas_h)
        packer.pack()

        atlas = Image.new("RGBA", (atlas_w, atlas_h), (0, 0, 0, 0))
        placements = {r.rid: (r.x, r.y, r.width, r.height) for r in packer.rect_list()}
        for name, img in images:
            if name in placements:
                x, y, w, h = placements[name]
                atlas.paste(img.resize((w, h)), (x, y))
                uv_map.append({
                    "name": name,
                    "x": x, "y": y, "w": w, "h": h,
                    "u": x / atlas_w, "v": y / atlas_h,
                    "u2": (x + w) / atlas_w, "v2": (y + h) / atlas_h,
                })
            else:
                uv_map.append({"name": name, "packed": False})
    else:
        # Simple row-based packing
        progress_cb(0.2, "Packing (row mode — install rectpack for optimal packing)")
        atlas = Image.new("RGBA", (atlas_w, atlas_h), (0, 0, 0, 0))
        cursor_x, cursor_y, row_height = 0, 0, 0
        for name, img in images:
            w, h = img.size
            if cursor_x + w > atlas_w:
                cursor_x = 0
                cursor_y += row_height
                row_height = 0
            if cursor_y + h > atlas_h:
                uv_map.append({"name": name, "packed": False, "reason": "atlas full"})
                continue
            atlas.paste(img, (cursor_x, cursor_y))
            uv_map.append({
                "name": name,
                "x": cursor_x, "y": cursor_y, "w": w, "h": h,
                "u": cursor_x / atlas_w, "v": cursor_y / atlas_h,
                "u2": (cursor_x + w) / atlas_w, "v2": (cursor_y + h) / atlas_h,
            })
            cursor_x += w
            row_height = max(row_height, h)

    progress_cb(0.8, "Saving atlas")
    atlas_path = Path(output_dir) / "atlas.png"
    manifest_path = Path(output_dir) / "uv_manifest.json"
    atlas.save(str(atlas_path))
    manifest_path.write_text(json.dumps({"atlas_size": [atlas_w, atlas_h], "sprites": uv_map}, indent=2))

    progress_cb(1.0, "Done")
    return {
        "files": [str(atlas_path), str(manifest_path)],
        "metadata": {
            "atlas_size": [atlas_w, atlas_h],
            "sprite_count": len(images),
            "backend": "rectpack" if _RECTPACK else "row",
        },
    }
