"""assgen visual mesh — mesh processing and conversion tools.

  assgen gen visual mesh validate      check manifold-ness, non-manifold edges
  assgen gen visual mesh convert       format conversion glb↔obj↔ply↔stl
  assgen gen visual mesh merge         combine N meshes into one
  assgen gen visual mesh bounds        AABB, OBB, bounding sphere
  assgen gen visual mesh flip-normals  flip face winding order
  assgen gen visual mesh weld          merge near-duplicate vertices
  assgen gen visual mesh center        reposition mesh pivot
  assgen gen visual mesh scale         scale mesh by factor or units
"""
from __future__ import annotations
from typing import Optional
import typer
from assgen.client.commands.submit import submit_job

app = typer.Typer(help="Mesh processing: validate, convert, merge, and repair.", no_args_is_help=True)

_WAIT_OPT = typer.Option(None, "--wait/--no-wait", help="Block until the job completes")
_OUT_OPT  = typer.Option(None, "--output", "-o", help="Output file or directory path")


@app.command("validate")
def mesh_validate(
    input_file: str = typer.Argument(..., help="Mesh file to validate"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Check mesh integrity: manifold, holes, non-manifold edges, duplicate verts."""
    submit_job("visual.mesh.validate", {"input": input_file, "output": output}, wait=wait)


@app.command("convert")
def mesh_convert(
    input_file: str = typer.Argument(..., help="Source mesh file"),
    format: str = typer.Option("glb", "--format", "-f", help="Target format: glb obj ply stl"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Convert a mesh between formats (glb, obj, ply, stl)."""
    submit_job("visual.mesh.convert", {"input": input_file, "format": format, "output": output}, wait=wait)


@app.command("merge")
def mesh_merge(
    inputs: list[str] = typer.Argument(..., help="Mesh files to merge"),
    format: str = typer.Option("glb", "--format", "-f", help="Output format"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Merge multiple meshes into a single file."""
    submit_job("visual.mesh.merge", {"inputs": list(inputs), "format": format, "output": output}, wait=wait)


@app.command("bounds")
def mesh_bounds(
    input_file: str = typer.Argument(..., help="Mesh file"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Compute AABB, OBB, and bounding sphere for a mesh."""
    submit_job("visual.mesh.bounds", {"input": input_file, "output": output}, wait=wait)


@app.command("flip-normals")
def mesh_flipnormals(
    input_file: str = typer.Argument(..., help="Mesh file"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Flip the face winding order (normals) of a mesh."""
    submit_job("visual.mesh.flipnormals", {"input": input_file, "output": output}, wait=wait)


@app.command("weld")
def mesh_weld(
    input_file: str = typer.Argument(..., help="Mesh file"),
    threshold: float = typer.Option(1e-5, "--threshold", "-t",
                                    help="Distance threshold for merging vertices"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Merge near-duplicate vertices within a threshold distance."""
    submit_job("visual.mesh.weld", {"input": input_file, "threshold": threshold, "output": output}, wait=wait)


@app.command("center")
def mesh_center(
    input_file: str = typer.Argument(..., help="Mesh file"),
    mode: str = typer.Option("bbox", "--mode", "-m", help="Pivot mode: origin | bbox"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Reposition the mesh pivot to the origin or bounding-box centre."""
    submit_job("visual.mesh.center", {"input": input_file, "mode": mode, "output": output}, wait=wait)


@app.command("scale")
def mesh_scale(
    input_file: str = typer.Argument(..., help="Mesh file"),
    scale: Optional[float] = typer.Option(None, "--scale", "-s", help="Uniform scale factor"),
    units_from: Optional[str] = typer.Option(None, "--from", help="Source unit, e.g. 'cm'"),
    units_to: Optional[str] = typer.Option(None, "--to", help="Target unit, e.g. 'm'"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Scale a mesh by a factor or perform unit conversion."""
    submit_job("visual.mesh.scale", {
        "input": input_file,
        "scale": scale,
        "units_from": units_from,
        "units_to": units_to,
        "output": output,
    }, wait=wait)
