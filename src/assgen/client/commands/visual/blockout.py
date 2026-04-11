"""assgen visual blockout — rapid greybox prototyping.

  assgen visual blockout create    text/image → low-fi blockout
  assgen visual blockout assemble  compose scene from blockout pieces
  assgen visual blockout iterate   quick variant from existing blockout
"""
from __future__ import annotations

import typer

from assgen.client.commands.submit import submit_job

app = typer.Typer(help="Rapid blockout / greybox prototyping.", no_args_is_help=True)

_WAIT_OPT = typer.Option(None, "--wait/--no-wait", help="Block until the job completes and stream live progress")
_OUT_OPT  = typer.Option(None, "--output", "-o", help="Output file or directory path")


@app.command("create")
def blockout_create(
    prompt: str = typer.Argument(..., help="What to blockout, e.g. 'dungeon room with pillars'"),
    scale: str | None = typer.Option(None, "--scale", help="Approx scale, e.g. '10x10x3m'"),
    input_image: str | None = typer.Option(None, "--input-image", "-i", help="Reference image"),
    output: str | None = _OUT_OPT,
    wait: bool | None = _WAIT_OPT,
) -> None:
    """Generate a 2D blockout layout sketch for scene planning (SDXL).

    NOTE: Output is a 2D image reference (top-down or perspective sketch),
    NOT a 3D mesh.  Use the output as a visual guide when building blockout
    geometry manually in your game engine or in Blender.
    """
    submit_job("visual.blockout.create", {
        "prompt": prompt,
        "scale": scale,
        "input_image": input_image,
        "output": output,
    }, wait=wait)


@app.command("assemble")
def blockout_assemble(
    inputs: list[str] = typer.Argument(..., help="Paths to blockout pieces to combine"),
    layout: str | None = typer.Option(None, "--layout", help="Layout description"),
    output: str | None = _OUT_OPT,
    wait: bool | None = _WAIT_OPT,
) -> None:
    """Assemble multiple blockout pieces into a scene."""
    submit_job("visual.blockout.create", {
        "mode": "assemble",
        "inputs": list(inputs),
        "layout": layout,
        "output": output,
    }, wait=wait)


@app.command("iterate")
def blockout_iterate(
    input_mesh: str = typer.Argument(..., help="Existing blockout .glb/.obj to vary"),
    prompt: str | None = typer.Option(None, "--prompt", help="Variation guidance"),
    output: str | None = _OUT_OPT,
    wait: bool | None = _WAIT_OPT,
) -> None:
    """Generate a quick variation of an existing blockout."""
    submit_job("visual.blockout.create", {
        "mode": "iterate",
        "input": input_mesh,
        "prompt": prompt,
        "output": output,
    }, wait=wait)
