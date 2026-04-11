"""assgen visual concept — concept art and style references.

  assgen visual concept generate   text → 2D concept art (SDXL)
  assgen visual concept ref        generate a multi-view reference sheet
  assgen visual concept style      apply/define an art style guide
"""
from __future__ import annotations

import typer

from assgen.client.commands.submit import submit_job

app = typer.Typer(help="Generate concept art and style references.", no_args_is_help=True)

_WAIT_OPT = typer.Option(None, "--wait/--no-wait", help="Wait for completion and show result")
_OUT_OPT  = typer.Option(None, "--output", "-o", help="Output file path")


@app.command("generate")
def concept_generate(
    prompt: str = typer.Argument(..., help="Description of the concept art"),
    negative: str | None = typer.Option(None, "--negative", help="Negative prompt"),
    style: str | None = typer.Option(None, "--style", help="Art style hint, e.g. 'painterly'"),
    width: int = typer.Option(1024, help="Image width"),
    height: int = typer.Option(1024, help="Image height"),
    output: str | None = _OUT_OPT,
    wait: bool | None = _WAIT_OPT,
) -> None:
    """Generate concept art from a text prompt.

    Examples:
        assgen gen visual concept generate "medieval knight, full plate armour, front view"
        assgen gen visual concept generate "neon-lit cyberpunk alley" --style "digital painting" --wait
        assgen gen visual concept generate "cartoon mushroom character" --variants 4 --wait
        assgen gen visual concept generate "sci-fi spaceship cockpit interior" -q high --wait
    """
    submit_job("visual.concept.generate", {
        "prompt": prompt,
        "negative_prompt": negative,
        "style": style,
        "width": width,
        "height": height,
        "output": output,
    }, wait=wait)


@app.command("ref")
def concept_ref(
    subject: str = typer.Argument(..., help="Character or prop to create references for"),
    views: int = typer.Option(4, "--views", help="Number of reference views (turnaround)"),
    output: str | None = _OUT_OPT,
    wait: bool | None = _WAIT_OPT,
) -> None:
    """Generate a multi-view reference sheet (front/side/back/3/4)."""
    submit_job("visual.concept.generate", {
        "prompt": f"character design reference sheet, {subject}, multiple views, front back side",
        "views": views,
        "output": output,
    }, wait=wait)


@app.command("style")
def concept_style(
    prompt: str = typer.Argument(..., help="Art style description"),
    samples: int = typer.Option(4, "--samples", help="Number of style samples"),
    output: str | None = _OUT_OPT,
    wait: bool | None = _WAIT_OPT,
) -> None:
    """Generate art style exploration samples."""
    submit_job("visual.concept.style", {
        "prompt": prompt,
        "samples": samples,
        "output": output,
    }, wait=wait)
