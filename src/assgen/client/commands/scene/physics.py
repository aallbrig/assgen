"""assgen scene physics — collision meshes and simulation data.

  assgen scene physics collider  generate optimised collision geometry
  assgen scene physics rigid     configure rigid body properties
  assgen scene physics cloth     simulate and bake cloth / hair
  assgen scene physics export    bake physics data for engine import
"""
from __future__ import annotations
from typing import Optional
import typer
from assgen.client.commands.submit import submit_job

app = typer.Typer(help="Collision meshes, rigid bodies, and simulation.", no_args_is_help=True)

_WAIT_OPT = typer.Option(None, "--wait/--no-wait", help="Block until the job completes and stream live progress")
_OUT_OPT  = typer.Option(None, "--output", "-o", help="Output file or directory path")


@app.command("collider")
def physics_collider(
    mesh: str = typer.Argument(..., help="Visual mesh to generate a collider for"),
    shape: str = typer.Option("convex", "--shape",
                              help="Collider type: convex hull box sphere capsule mesh"),
    simplify: bool = typer.Option(True, "--simplify/--exact"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Generate an optimised collision mesh from a visual mesh."""
    submit_job("scene.physics.collider", {
        "input": mesh,
        "shape": shape,
        "simplify": simplify,
        "output": output,
    }, wait=wait)


@app.command("rigid")
def physics_rigid(
    mesh: str = typer.Argument(..., help="Mesh to configure as a rigid body"),
    mass: Optional[float] = typer.Option(None, "--mass", help="Mass in kg"),
    material: Optional[str] = typer.Option(None, "--material",
                                           help="Physics material: wood metal stone rubber"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Set up rigid body physics properties for a mesh."""
    submit_job("scene.physics.collider", {
        "mode": "rigid",
        "input": mesh,
        "mass": mass,
        "material": material,
        "output": output,
    }, wait=wait)


@app.command("cloth")
def physics_cloth(
    mesh: str = typer.Argument(..., help="Cloth or hair mesh to simulate"),
    sim_type: str = typer.Option("cloth", "--type", help="cloth | hair | softbody"),
    duration: float = typer.Option(3.0, "--duration", help="Simulation duration in seconds"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Simulate and bake cloth or hair physics."""
    submit_job("scene.physics.collider", {
        "mode": "cloth",
        "input": mesh,
        "sim_type": sim_type,
        "duration": duration,
        "output": output,
    }, wait=wait)


@app.command("export")
def physics_export(
    mesh: str = typer.Argument(..., help="Physics setup to export"),
    engine: str = typer.Option("unity", "--engine", help="Target engine: unity unreal godot"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Export baked physics data for a target game engine."""
    submit_job("scene.physics.collider", {
        "mode": "export",
        "input": mesh,
        "engine": engine,
        "output": output,
    }, wait=wait)
