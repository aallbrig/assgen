"""assgen visual vfx — particles, decals, and simulation effects.

  assgen visual vfx particle   generate a particle system texture sheet
  assgen visual vfx decal      create / apply a dynamic decal
  assgen visual vfx sim        bake a physics-based VFX simulation
"""
from __future__ import annotations

import typer

from assgen.client.commands.submit import submit_job

app = typer.Typer(help="Particle systems, decals, and VFX.", no_args_is_help=True)

_WAIT_OPT = typer.Option(None, "--wait/--no-wait", help="Block until the job completes and stream live progress")
_OUT_OPT  = typer.Option(None, "--output", "-o", help="Output file or directory path")


@app.command("particle")
def vfx_particle(
    prompt: str = typer.Argument(..., help="Effect description, e.g. 'magical sparkle burst'"),
    frames: int = typer.Option(16, "--frames", help="Sprite sheet frame count"),
    resolution: int = typer.Option(512, "--resolution", "-r"),
    output: str | None = _OUT_OPT,
    wait: bool | None = _WAIT_OPT,
) -> None:
    """Generate a particle texture / sprite sheet."""
    submit_job("visual.vfx.particle", {
        "prompt": prompt,
        "frames": frames,
        "resolution": resolution,
        "output": output,
    }, wait=wait)


@app.command("decal")
def vfx_decal(
    prompt: str = typer.Argument(..., help="Decal description, e.g. 'bullet hole in metal'"),
    resolution: int = typer.Option(512, "--resolution", "-r"),
    alpha: bool = typer.Option(True, "--alpha/--no-alpha", help="Include alpha channel"),
    output: str | None = _OUT_OPT,
    wait: bool | None = _WAIT_OPT,
) -> None:
    """Generate a decal texture (with alpha channel)."""
    submit_job("visual.vfx.particle", {
        "mode": "decal",
        "prompt": prompt,
        "resolution": resolution,
        "alpha": alpha,
        "output": output,
    }, wait=wait)


@app.command("sim")
def vfx_sim(
    sim_type: str = typer.Argument(..., help="Simulation type: fire smoke cloth destruction fluid"),
    duration: float = typer.Option(2.0, "--duration", help="Simulation duration in seconds"),
    output: str | None = _OUT_OPT,
    wait: bool | None = _WAIT_OPT,
) -> None:
    """Run and bake a physics-based VFX simulation."""
    submit_job("visual.vfx.particle", {
        "mode": "sim",
        "sim_type": sim_type,
        "duration": duration,
        "output": output,
    }, wait=wait)
