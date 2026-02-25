"""assgen audio sfx — sound effects generation.

  assgen audio sfx generate   text → WAV sound effect (AudioGen)
  assgen audio sfx edit       edit / layer sound effects
  assgen audio sfx library    search and list local SFX library
"""
from __future__ import annotations
from typing import Optional
import typer
from assgen.client.commands.submit import submit_job

app = typer.Typer(help="Sound effects generation and management.", no_args_is_help=True)

_WAIT_OPT = typer.Option(None, "--wait/--no-wait")
_OUT_OPT  = typer.Option(None, "--output", "-o")


@app.command("generate")
def sfx_generate(
    prompt: str = typer.Argument(..., help="Sound description, e.g. 'laser gun firing'"),
    duration: float = typer.Option(2.0, "--duration", "-d", help="Target duration in seconds"),
    variations: int = typer.Option(1, "--variations", "-n", help="Number of variants to generate"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Generate a sound effect from a text description (AudioGen)."""
    submit_job("audio.sfx.generate", {
        "prompt": prompt,
        "duration": duration,
        "variations": variations,
        "output": output,
    }, wait=wait)


@app.command("edit")
def sfx_edit(
    input_file: str = typer.Argument(..., help="Input audio file to edit"),
    operation: str = typer.Option("pitch", "--op",
                                  help="pitch | reverb | speed | layer | normalize"),
    value: Optional[str] = typer.Option(None, "--value", help="Operation parameter"),
    secondary: Optional[str] = typer.Option(None, "--secondary", help="Second audio for layer op"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Edit or process an existing sound effect."""
    submit_job("audio.sfx.generate", {
        "mode": "edit",
        "input": input_file,
        "operation": operation,
        "value": value,
        "secondary": secondary,
        "output": output,
    }, wait=wait)


@app.command("library")
def sfx_library(
    query: Optional[str] = typer.Argument(None, help="Search query for local SFX library"),
) -> None:
    """Browse the local generated SFX library."""
    from assgen.config import get_outputs_dir
    from rich.table import Table
    from assgen.client.output import console
    import pathlib

    sfx_dir = get_outputs_dir() / "sfx"
    if not sfx_dir.exists():
        console.print("[dim]No SFX library yet — generate some sounds first.[/dim]")
        return

    files = sorted(sfx_dir.glob("*.wav")) + sorted(sfx_dir.glob("*.mp3"))
    if query:
        files = [f for f in files if query.lower() in f.name.lower()]

    if not files:
        console.print("[dim]No matching files.[/dim]")
        return

    table = Table(title="SFX Library", header_style="bold cyan")
    table.add_column("File", min_width=30)
    table.add_column("Size", width=10)
    for f in files:
        size = f"{f.stat().st_size / 1024:.1f} KB"
        table.add_row(f.name, size)
    console.print(table)
