"""assgen audio process — algorithmic audio processing tools.

  assgen gen audio process normalize      LUFS or peak normalization
  assgen gen audio process trim-silence   strip leading/trailing silence
  assgen gen audio process loop-optimize  find zero-crossing loop points
  assgen gen audio process convert        WAV↔OGG↔MP3↔FLAC
  assgen gen audio process downmix        stereo→mono (or upmix)
  assgen gen audio process resample       change sample rate
  assgen gen audio process waveform       generate waveform PNG preview
"""
from __future__ import annotations
from typing import Optional
import typer
from assgen.client.commands.submit import submit_job

app = typer.Typer(
    help="Algorithmic audio processing: normalize, trim, loop, convert, etc.",
    no_args_is_help=True,
)

_WAIT_OPT = typer.Option(None, "--wait/--no-wait", help="Block until the job completes")
_OUT_OPT  = typer.Option(None, "--output", "-o", help="Output file or directory path")


@app.command("normalize")
def audio_normalize(
    input_file: str = typer.Argument(..., help="Audio file to normalize"),
    lufs: float = typer.Option(-14.0, "--lufs", help="Target LUFS level"),
    mode: str = typer.Option("lufs", "--mode", "-m", help="Normalization mode: lufs | peak"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Normalize audio to a target LUFS level or peak 0 dBFS."""
    submit_job("audio.process.normalize", {
        "input": input_file, "lufs": lufs, "mode": mode, "output": output,
    }, wait=wait)


@app.command("trim-silence")
def audio_trim_silence(
    input_file: str = typer.Argument(..., help="Audio file to trim"),
    threshold_db: float = typer.Option(-50.0, "--threshold-db",
                                        help="Silence threshold in dBFS (default -50)"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Strip leading and trailing silence from an audio file."""
    submit_job("audio.process.trim_silence", {
        "input": input_file, "threshold_db": threshold_db, "output": output,
    }, wait=wait)


@app.command("loop-optimize")
def audio_loop_optimize(
    input_file: str = typer.Argument(..., help="Audio file to optimize for looping"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Find zero-crossing loop points for seamless audio looping."""
    submit_job("audio.process.loop_optimize", {
        "input": input_file, "output": output,
    }, wait=wait)


@app.command("convert")
def audio_convert(
    input_file: str = typer.Argument(..., help="Audio file to convert"),
    format: str = typer.Option("ogg", "--format", "-f",
                               help="Target format: wav ogg mp3 flac"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Convert audio between formats (WAV/OGG/MP3/FLAC)."""
    submit_job("audio.process.convert", {
        "input": input_file, "format": format, "output": output,
    }, wait=wait)


@app.command("downmix")
def audio_downmix(
    input_file: str = typer.Argument(..., help="Audio file to downmix"),
    channels: int = typer.Option(1, "--channels", "-c", help="Target channel count: 1 (mono) or 2 (stereo)"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Downmix stereo to mono (or upmix mono to stereo)."""
    submit_job("audio.process.downmix", {
        "input": input_file, "channels": channels, "output": output,
    }, wait=wait)


@app.command("resample")
def audio_resample(
    input_file: str = typer.Argument(..., help="Audio file to resample"),
    rate: int = typer.Option(48000, "--rate", "-r", help="Target sample rate in Hz"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Change the sample rate of an audio file."""
    submit_job("audio.process.resample", {
        "input": input_file, "rate": rate, "output": output,
    }, wait=wait)


@app.command("waveform")
def audio_waveform(
    input_file: str = typer.Argument(..., help="Audio file to visualize"),
    width: int = typer.Option(1200, "--width", "-W", help="Output image width in pixels"),
    height: int = typer.Option(200, "--height", "-H", help="Output image height in pixels"),
    color: str = typer.Option("#00ff88", "--color", help="Waveform colour (hex, e.g. '#00ff88')"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Generate a waveform PNG preview of an audio file."""
    submit_job("audio.process.waveform", {
        "input": input_file,
        "width": width,
        "height": height,
        "color": color,
        "output": output,
    }, wait=wait)
