"""assgen audio sfx — sound effects generation.

  assgen audio sfx generate   text → WAV sound effect (AudioGen)
  assgen audio sfx edit       edit / layer sound effects
  assgen audio sfx library    search and list local SFX library
"""
from __future__ import annotations

import typer

from assgen.client.commands.submit import submit_job

app = typer.Typer(help="Sound effects generation and management.", no_args_is_help=True)

_WAIT_OPT = typer.Option(None, "--wait/--no-wait", help="Block until the job completes and stream live progress")
_OUT_OPT  = typer.Option(None, "--output", "-o", help="Output file or directory path")


@app.command("generate")
def sfx_generate(
    prompt: str = typer.Argument(..., help="Sound description, e.g. 'laser gun firing'"),
    duration: float = typer.Option(2.0, "--duration", "-d", help="Target duration in seconds"),
    variations: int = typer.Option(1, "--variations", "-n", help="Number of variants to generate"),
    output: str | None = _OUT_OPT,
    wait: bool | None = _WAIT_OPT,
    model_id: str | None = typer.Option(None, "--model-id", help="Override HF model (validated by server)"),
) -> None:
    """Generate a sound effect from a text description (AudioGen).

    Examples:
        assgen gen audio sfx generate "laser gun firing, futuristic" --wait
        assgen gen audio sfx generate "heavy footsteps on gravel" -d 3.0 --wait
        assgen gen audio sfx generate "explosion, distant, muffled" -n 3 --wait
        assgen gen audio sfx generate "UI button click, satisfying" -d 0.5 --wait
    """
    submit_job("audio.sfx.generate", {
        "prompt": prompt,
        "duration": duration,
        "variations": variations,
        "output": output,
    }, wait=wait, model_id=model_id)


@app.command("edit")
def sfx_edit(
    input_file: str = typer.Argument(..., help="Input audio file to edit"),
    operation: str = typer.Option("pitch", "--op",
                                  help="pitch | reverb | speed | layer | normalize"),
    value: str | None = typer.Option(None, "--value", help="Operation parameter"),
    secondary: str | None = typer.Option(None, "--secondary", help="Second audio for layer op"),
    output: str | None = _OUT_OPT,
    wait: bool | None = _WAIT_OPT,
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
    query: str | None = typer.Argument(None, help="Search query for local SFX library"),
) -> None:
    """Browse the local generated SFX library."""
    from rich.table import Table

    from assgen.client.output import console
    from assgen.config import get_outputs_dir

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
