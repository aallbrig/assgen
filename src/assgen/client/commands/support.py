"""assgen support — narrative, lore, and procedural data assets.

  assgen support narrative dialog   generate NPC dialog trees (LLM)
  assgen support narrative lore     generate world-building text
  assgen support data lightmap      AI-accelerated lightmap baking
  assgen support data proc          procedural asset generation scripts
"""
from __future__ import annotations
from typing import Optional
import typer
from assgen.client.commands.submit import submit_job

app = typer.Typer(help="Narrative content, lore, and procedural support data.", no_args_is_help=True)

narrative_app = typer.Typer(help="NPC dialog and world-building lore generation.")
app.add_typer(narrative_app, name="narrative")

data_app = typer.Typer(help="Lightmap baking and procedural data generation.")
app.add_typer(data_app, name="data")

_WAIT_OPT = typer.Option(None, "--wait/--no-wait", help="Block until the job completes and stream live progress")
_OUT_OPT  = typer.Option(None, "--output", "-o", help="Output file or directory path")


# ---------------------------------------------------------------------------
# narrative
# ---------------------------------------------------------------------------

@narrative_app.command("dialog")
def narrative_dialog(
    character: str = typer.Argument(..., help="NPC name / description"),
    context: Optional[str] = typer.Option(None, "--context", help="Scene / quest context"),
    lines: int = typer.Option(10, "--lines", "-n", help="Number of dialog lines to generate"),
    branching: bool = typer.Option(False, "--branching", help="Generate a branching dialog tree"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Generate NPC dialog lines or a branching dialog tree."""
    submit_job("narrative.dialogue.npc", {
        "character": character,
        "context": context,
        "lines": lines,
        "branching": branching,
        "output": output,
    }, wait=wait)


@narrative_app.command("lore")
def narrative_lore(
    topic: str = typer.Argument(..., help="Lore topic, e.g. 'history of the fallen empire'"),
    length: int = typer.Option(500, "--length", help="Approximate word count"),
    format: str = typer.Option("prose", "--format", help="prose | codex | item-description | quest"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Generate world-building lore text (codex entries, item descriptions, quest text)."""
    submit_job("narrative.lore.generate", {
        "topic": topic,
        "length": length,
        "format": format,
        "output": output,
    }, wait=wait)


# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------

@data_app.command("lightmap")
def data_lightmap(
    scene: str = typer.Argument(..., help="Scene file to bake"),
    quality: str = typer.Option("medium", "--quality", help="low | medium | high"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Bake GI lightmaps for a scene using AI-accelerated methods."""
    submit_job("scene.lighting.hdri", {
        "mode": "lightmap",
        "input": scene,
        "quality": quality,
        "output": output,
    }, wait=wait)


@data_app.command("proc")
def data_proc(
    description: str = typer.Argument(..., help="Describe the procedural asset to generate code for"),
    language: str = typer.Option("python", "--language",
                                 help="python | gdscript | csharp | hlsl"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Generate a procedural asset generation script from a description."""
    submit_job("narrative.quest.design", {
        "mode": "proc-gen",
        "description": description,
        "language": language,
        "output": output,
    }, wait=wait)
