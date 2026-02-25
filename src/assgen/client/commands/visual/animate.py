"""assgen visual animate — animation generation.

  assgen visual animate keyframe   text / video → animation keyframes
  assgen visual animate mocap      video → motion-capture animation
  assgen visual animate blend      blend or loop two animations
  assgen visual animate retarget   apply animation to a different rig
"""
from __future__ import annotations
from typing import Optional
import typer
from assgen.client.commands.submit import submit_job

app = typer.Typer(help="Animation generation and retargeting.", no_args_is_help=True)

_WAIT_OPT = typer.Option(None, "--wait/--no-wait")
_OUT_OPT  = typer.Option(None, "--output", "-o")


@app.command("keyframe")
def animate_keyframe(
    prompt: str = typer.Argument(..., help="Animation description, e.g. 'walking cycle'"),
    rig: Optional[str] = typer.Option(None, "--rig", "-r", help="Rigged mesh to animate"),
    fps: int = typer.Option(30, "--fps"),
    duration: float = typer.Option(2.0, "--duration", help="Duration in seconds"),
    looping: bool = typer.Option(False, "--loop", help="Generate as a looping animation"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Generate animation keyframes from a text prompt."""
    submit_job("visual.animate.keyframe", {
        "prompt": prompt,
        "rig": rig,
        "fps": fps,
        "duration": duration,
        "looping": looping,
        "output": output,
    }, wait=wait)


@app.command("mocap")
def animate_mocap(
    video: str = typer.Argument(..., help="Input video file for motion capture"),
    target_rig: Optional[str] = typer.Option(None, "--rig", help="Rig to retarget captured motion onto"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Extract motion from a video and convert to skeleton animation."""
    submit_job("visual.animate.mocap", {
        "video": video,
        "target_rig": target_rig,
        "output": output,
    }, wait=wait)


@app.command("blend")
def animate_blend(
    anim_a: str = typer.Argument(..., help="First animation file"),
    anim_b: str = typer.Argument(..., help="Second animation file"),
    blend_weight: float = typer.Option(0.5, "--weight", help="Blend weight (0=A, 1=B)"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Blend two animations together."""
    submit_job("visual.animate.keyframe", {
        "mode": "blend",
        "anim_a": anim_a,
        "anim_b": anim_b,
        "blend_weight": blend_weight,
        "output": output,
    }, wait=wait)


@app.command("retarget")
def animate_retarget(
    animation: str = typer.Argument(..., help="Animation file to retarget"),
    source_rig: str = typer.Argument(..., help="Source skeleton"),
    target_rig: str = typer.Argument(..., help="Target skeleton"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Retarget an animation from one rig to another."""
    submit_job("visual.animate.keyframe", {
        "mode": "retarget",
        "animation": animation,
        "source_rig": source_rig,
        "target_rig": target_rig,
        "output": output,
    }, wait=wait)
