"""assgen audio voice — voice synthesis and dialog.

  assgen audio voice tts      text → speech with emotion (Bark)
  assgen audio voice clone    clone a voice from a sample recording
  assgen audio voice dialog   generate a batch of NPC dialog lines
"""
from __future__ import annotations

import typer

from assgen.client.commands.submit import submit_job

app = typer.Typer(help="Voice synthesis, cloning, and dialog generation.", no_args_is_help=True)

_WAIT_OPT = typer.Option(None, "--wait/--no-wait", help="Block until the job completes and stream live progress")
_OUT_OPT  = typer.Option(None, "--output", "-o", help="Output file or directory path")


@app.command("tts")
def voice_tts(
    text: str = typer.Argument(..., help="Text to synthesise"),
    emotion: str | None = typer.Option(None, "--emotion",
                                          help="Emotion tag: neutral angry happy sad fearful"),
    speaker: str | None = typer.Option(None, "--speaker",
                                          help="Speaker preset, e.g. 'v2/en_speaker_6'"),
    output: str | None = _OUT_OPT,
    wait: bool | None = _WAIT_OPT,
) -> None:
    """Convert text to speech with optional emotion (Bark).

    Examples:
        assgen gen audio voice tts "Hello adventurer, welcome to my shop!" --wait
        assgen gen audio voice tts "I will have my revenge!" --preset v2/en_speaker_6 --wait
        assgen gen audio voice tts "The ancient tome speaks of dark prophecy..." --preset v2/en_speaker_9 --wait
    """
    submit_job("audio.voice.tts", {
        "text": text,
        "emotion": emotion,
        "speaker": speaker,
        "output": output,
    }, wait=wait)


@app.command("clone")
def voice_clone(
    sample: str = typer.Argument(..., help="Path to reference audio sample (≥5 seconds)"),
    text: str = typer.Argument(..., help="Text for the cloned voice to speak"),
    output: str | None = _OUT_OPT,
    wait: bool | None = _WAIT_OPT,
) -> None:
    """Clone a voice from an audio sample and synthesise new speech."""
    submit_job("audio.voice.clone", {
        "sample": sample,
        "text": text,
        "output": output,
    }, wait=wait)


@app.command("dialog")
def voice_dialog(
    script_file: str = typer.Argument(..., help="JSON or plain-text file with dialog lines"),
    speaker: str | None = typer.Option(None, "--speaker", help="Speaker preset or voice sample"),
    emotion: str | None = typer.Option(None, "--emotion"),
    output_dir: str | None = typer.Option(None, "--output-dir", "-o",
                                             help="Directory for output files"),
    wait: bool | None = _WAIT_OPT,
) -> None:
    """Generate a batch of voiced NPC dialog lines from a script file."""
    submit_job("audio.voice.tts", {
        "mode": "batch",
        "script_file": script_file,
        "speaker": speaker,
        "emotion": emotion,
        "output_dir": output_dir,
    }, wait=wait)
