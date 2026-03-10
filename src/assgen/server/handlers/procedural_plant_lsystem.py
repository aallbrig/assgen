"""Handler for proc.plant.lsystem — L-system plant skeleton generator.

Implements a turtle-graphics L-system renderer in pure Python.
Outputs an SVG file and a branch segments JSON.

Outputs:
    plant.svg            — SVG vector illustration
    plant_branches.json  — {branches: [{x1,y1,x2,y2,depth}]}

Params:
    axiom      (str):   starting string (default "F")
    rules      (str):   JSON string mapping symbols to replacements
                        e.g. '{"F":"F[+F]F[-F]F"}' (default)
    iterations (int):   rewrite iterations (default 4)
    angle      (float): turning angle in degrees (default 25.0)
    step       (float): segment length in pixels (default 10.0)
"""
from __future__ import annotations

import json
import math
from pathlib import Path


_AVAILABLE = True  # pure Python — no optional deps


def _apply_rules(s: str, rules: dict[str, str], iterations: int) -> str:
    for _ in range(iterations):
        s = "".join(rules.get(c, c) for c in s)
    return s


def _turtle_render(
    lstring: str,
    step: float,
    angle_deg: float,
) -> tuple[list[dict], float, float, float, float]:
    """Run turtle graphics and return (branches, min_x, min_y, max_x, max_y)."""
    angle_rad = math.radians(angle_deg)
    x, y, heading = 0.0, 0.0, math.pi / 2  # heading = up
    stack: list[tuple[float, float, float]] = []
    depth = 0
    branches: list[dict] = []
    min_x = max_x = x
    min_y = max_y = y

    for cmd in lstring:
        if cmd in ("F", "G"):
            nx = x + step * math.cos(heading)
            ny = y - step * math.sin(heading)  # SVG y increases downward
            branches.append({"x1": x, "y1": y, "x2": nx, "y2": ny, "depth": depth})
            x, y = nx, ny
        elif cmd == "+":
            heading -= angle_rad
        elif cmd == "-":
            heading += angle_rad
        elif cmd == "[":
            stack.append((x, y, heading))
            depth += 1
        elif cmd == "]":
            if stack:
                x, y, heading = stack.pop()
                depth = max(0, depth - 1)
        min_x = min(min_x, x)
        min_y = min(min_y, y)
        max_x = max(max_x, x)
        max_y = max(max_y, y)

    return branches, min_x, min_y, max_x, max_y


def _build_svg(branches: list[dict], min_x: float, min_y: float,
               max_x: float, max_y: float, margin: float = 20.0) -> str:
    pad_x = -min_x + margin
    pad_y = -min_y + margin
    vw = max_x - min_x + 2 * margin
    vh = max_y - min_y + 2 * margin

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {vw:.1f} {vh:.1f}" width="{vw:.0f}" height="{vh:.0f}">',
        '<rect width="100%" height="100%" fill="#1a1a2e"/>',
    ]
    max_depth = max((b["depth"] for b in branches), default=0) or 1
    for b in branches:
        frac = b["depth"] / max_depth
        # Colour shifts from brown (trunk) to green (tips)
        r = int(100 * (1 - frac) + 50 * frac)
        g = int(60 * (1 - frac) + 180 * frac)
        bv = int(20 * (1 - frac) + 30 * frac)
        stroke_w = max(0.5, 3.0 * (1 - frac * 0.7))
        lines.append(
            f'<line x1="{b["x1"] + pad_x:.2f}" y1="{b["y1"] + pad_y:.2f}" '
            f'x2="{b["x2"] + pad_x:.2f}" y2="{b["y2"] + pad_y:.2f}" '
            f'stroke="rgb({r},{g},{bv})" stroke-width="{stroke_w:.2f}"/>'
        )
    lines.append("</svg>")
    return "\n".join(lines)


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Generate an L-system plant skeleton."""
    axiom: str = params.get("axiom", "F")
    rules_raw: str = params.get("rules", '{"F":"F[+F]F[-F]F"}')
    iterations: int = int(params.get("iterations", 4))
    angle: float = float(params.get("angle", 25.0))
    step: float = float(params.get("step", 10.0))

    try:
        rules: dict[str, str] = json.loads(rules_raw) if isinstance(rules_raw, str) else dict(rules_raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"'rules' must be a valid JSON string: {exc}") from exc

    progress_cb(0.0, f"Rewriting L-system ({iterations} iterations)")
    lstring = _apply_rules(axiom, rules, iterations)

    # Guard against absurdly long strings
    max_len = 500_000
    if len(lstring) > max_len:
        lstring = lstring[:max_len]

    progress_cb(0.4, f"Rendering turtle ({len(lstring)} symbols)")
    branches, min_x, min_y, max_x, max_y = _turtle_render(lstring, step, angle)

    progress_cb(0.7, "Building SVG")
    svg = _build_svg(branches, min_x, min_y, max_x, max_y)

    out_svg = Path(output_dir) / "plant.svg"
    out_json = Path(output_dir) / "plant_branches.json"
    out_svg.write_text(svg, encoding="utf-8")
    out_json.write_text(json.dumps({"branches": branches}, indent=2))

    progress_cb(1.0, "Done")
    return {
        "files": [str(out_svg), str(out_json)],
        "metadata": {
            "axiom": axiom,
            "iterations": iterations,
            "angle": angle,
            "step": step,
            "symbol_count": len(lstring),
            "branch_count": len(branches),
        },
    }
