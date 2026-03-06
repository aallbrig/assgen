"""assgen audio music — music and ambient track generation.

  assgen audio music compose    text → music track (MusicGen)
  assgen audio music loop       generate a seamless loop
  assgen audio music adaptive   generate mood-based adaptive stems
"""
from __future__ import annotations
from typing import Optional
import typer
from assgen.client.commands.submit import submit_job

app = typer.Typer(help="Music and ambient track generation.", no_args_is_help=True)

_WAIT_OPT = typer.Option(None, "--wait/--no-wait", help="Block until the job completes and stream live progress")
_OUT_OPT  = typer.Option(None, "--output", "-o", help="Output file or directory path")


@app.command("compose")
def music_compose(
    prompt: str = typer.Argument(..., help="Music description, e.g. 'epic orchestral battle theme'"),
    duration: float = typer.Option(15.0, "--duration", "-d", help="Track length in seconds"),
    bpm: Optional[int] = typer.Option(None, "--bpm", help="Beats per minute"),
    key: Optional[str] = typer.Option(None, "--key", help="Musical key, e.g. 'C minor'"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Compose a music track from a text prompt (MusicGen)."""
    submit_job("audio.music.compose", {
        "prompt": prompt,
        "duration": duration,
        "bpm": bpm,
        "key": key,
        "output": output,
    }, wait=wait)


@app.command("loop")
def music_loop(
    prompt: str = typer.Argument(..., help="Loop description, e.g. 'calm forest ambient loop'"),
    duration: float = typer.Option(30.0, "--duration", "-d", help="Loop duration in seconds"),
    variations: int = typer.Option(1, "--variations", "-n", help="Number of loop variants"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Generate a seamlessly looping music track."""
    submit_job("audio.music.loop", {
        "prompt": prompt + ", seamless loop",
        "duration": duration,
        "variations": variations,
        "looping": True,
        "output": output,
    }, wait=wait)


@app.command("adaptive")
def music_adaptive(
    theme: str = typer.Argument(..., help="Base theme description"),
    moods: str = typer.Option("calm,tense,combat,victory", "--moods",
                              help="Comma-separated mood states to generate stems for"),
    duration: float = typer.Option(30.0, "--duration", "-d"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Generate adaptive music stems for different gameplay moods."""
    mood_list = [m.strip() for m in moods.split(",")]
    submit_job("audio.music.adaptive", {
        "theme": theme,
        "moods": mood_list,
        "duration": duration,
        "output": output,
    }, wait=wait)
