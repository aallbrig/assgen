"""assgen visual rig — character rigging and skinning.

  assgen visual rig auto      AI auto-rig a character / creature mesh
  assgen visual rig skin      Generate / refine skin weight maps
  assgen visual rig retarget  Transfer a rig to a different mesh
"""
from __future__ import annotations
from typing import Optional
import typer
from assgen.client.commands.submit import submit_job

app = typer.Typer(help="Rigging, skinning, and rig retargeting.", no_args_is_help=True)

_WAIT_OPT = typer.Option(None, "--wait/--no-wait")
_OUT_OPT  = typer.Option(None, "--output", "-o")


@app.command("auto")
def rig_auto(
    mesh: str = typer.Argument(..., help="Character / creature mesh to rig"),
    rig_type: str = typer.Option("biped", "--type", help="biped | quadruped | wing | custom"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Auto-rig a mesh with a skeleton (UniRig-style)."""
    submit_job("visual.rig.auto", {
        "input": mesh,
        "rig_type": rig_type,
        "output": output,
    }, wait=wait)


@app.command("skin")
def rig_skin(
    mesh: str = typer.Argument(..., help="Mesh with an existing skeleton"),
    method: str = typer.Option("heat", "--method", help="Skinning method: heat | geodesic | ai"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Generate or refine skin weight maps for a rigged mesh."""
    submit_job("visual.rig.auto", {
        "mode": "skin",
        "input": mesh,
        "method": method,
        "output": output,
    }, wait=wait)


@app.command("retarget")
def rig_retarget(
    source_rig: str = typer.Argument(..., help="Source rigged mesh"),
    target_mesh: str = typer.Argument(..., help="Target mesh to retarget the rig onto"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Retarget an existing rig to a different mesh."""
    submit_job("visual.rig.auto", {
        "mode": "retarget",
        "source_rig": source_rig,
        "target_mesh": target_mesh,
        "output": output,
    }, wait=wait)
