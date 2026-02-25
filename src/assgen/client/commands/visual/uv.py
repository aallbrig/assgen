"""assgen visual uv — UV unwrapping and layout.

  assgen visual uv auto    AI-powered smart unwrap
  assgen visual uv manual  Interactive seam edit guidance
  assgen visual uv optimize Texel density and stretch optimisation
"""
from __future__ import annotations
from typing import Optional
import typer
from assgen.client.commands.submit import submit_job

app = typer.Typer(help="UV unwrapping and layout.", no_args_is_help=True)

_WAIT_OPT = typer.Option(None, "--wait/--no-wait")
_OUT_OPT  = typer.Option(None, "--output", "-o")


@app.command("auto")
def uv_auto(
    input_mesh: str = typer.Argument(..., help="Mesh to unwrap"),
    padding: int = typer.Option(4, "--padding", help="UV island padding in pixels"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Run AI smart-unwrap on a mesh."""
    submit_job("visual.uv.auto", {
        "input": input_mesh,
        "padding": padding,
        "output": output,
    }, wait=wait)


@app.command("manual")
def uv_manual(
    input_mesh: str = typer.Argument(..., help="Mesh to provide seam guidance for"),
    style: Optional[str] = typer.Option(None, "--style", help="Unwrap style: organic | hard-surface"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Generate AI seam suggestions for a mesh."""
    submit_job("visual.uv.auto", {
        "mode": "seam-suggest",
        "input": input_mesh,
        "style": style,
        "output": output,
    }, wait=wait)


@app.command("optimize")
def uv_optimize(
    input_mesh: str = typer.Argument(..., help="Mesh with existing UVs to optimize"),
    texel_density: Optional[float] = typer.Option(None, "--texel-density", help="Target texels/metre"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Optimise UV island packing and texel density."""
    submit_job("visual.uv.auto", {
        "mode": "optimize",
        "input": input_mesh,
        "texel_density": texel_density,
        "output": output,
    }, wait=wait)
