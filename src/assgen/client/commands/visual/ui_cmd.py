"""assgen visual ui — UI/HUD elements and 2D overlays.

  assgen visual ui icon      generate icons and sprites
  assgen visual ui hud       health bars, minimaps, meters
  assgen visual ui overlay   2D canvas elements for 3D games
"""
from __future__ import annotations
from typing import Optional
import typer
from assgen.client.commands.submit import submit_job

app = typer.Typer(help="UI icons, HUD elements, and 2D overlays.", no_args_is_help=True)

_WAIT_OPT = typer.Option(None, "--wait/--no-wait")
_OUT_OPT  = typer.Option(None, "--output", "-o")


@app.command("icon")
def ui_icon(
    prompt: str = typer.Argument(..., help="Icon description, e.g. 'crossed swords inventory icon'"),
    size: int = typer.Option(256, "--size", "-s", help="Icon size in pixels"),
    style: Optional[str] = typer.Option(None, "--style", help="e.g. 'flat' 'pixel-art' 'realistic'"),
    count: int = typer.Option(1, "--count", "-n", help="Number of variants to generate"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Generate game UI icons or inventory sprites."""
    submit_job("visual.ui.icon", {
        "prompt": prompt,
        "size": size,
        "style": style,
        "count": count,
        "output": output,
    }, wait=wait)


@app.command("hud")
def ui_hud(
    prompt: str = typer.Argument(..., help="HUD element description, e.g. 'health bar sci-fi'"),
    width: int = typer.Option(512, "--width"),
    height: int = typer.Option(128, "--height"),
    style: Optional[str] = typer.Option(None, "--style"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Generate HUD elements (health bars, minimaps, meters)."""
    submit_job("visual.ui.icon", {
        "mode": "hud",
        "prompt": prompt,
        "width": width,
        "height": height,
        "style": style,
        "output": output,
    }, wait=wait)


@app.command("overlay")
def ui_overlay(
    prompt: str = typer.Argument(..., help="Overlay description"),
    width: int = typer.Option(1920, "--width"),
    height: int = typer.Option(1080, "--height"),
    transparent: bool = typer.Option(True, "--transparent/--opaque"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Generate a 2D overlay for a 3D game canvas."""
    submit_job("visual.ui.icon", {
        "mode": "overlay",
        "prompt": prompt,
        "width": width,
        "height": height,
        "transparent": transparent,
        "output": output,
    }, wait=wait)
