"""assgen visual sprite — sprite sheet packing.

  assgen gen visual sprite pack   pack animation frames into a sprite sheet
"""
from __future__ import annotations

import typer

from assgen.client.commands.submit import submit_job

app = typer.Typer(help="Sprite sheet packing and animation tools.", no_args_is_help=True)

_WAIT_OPT = typer.Option(None, "--wait/--no-wait", help="Block until the job completes")
_OUT_OPT  = typer.Option(None, "--output", "-o", help="Output directory path")


@app.command("pack")
def sprite_pack(
    inputs: list[str] = typer.Argument(..., help="Ordered list of frame image files"),
    cols: int = typer.Option(4, "--cols", "-c", help="Number of columns in the sprite sheet"),
    output: str | None = _OUT_OPT,
    wait: bool | None = _WAIT_OPT,
) -> None:
    """Pack animation frames into a sprite sheet PNG + manifest JSON."""
    submit_job("visual.sprite.pack", {
        "inputs": list(inputs),
        "cols": cols,
        "output": output,
    }, wait=wait)
