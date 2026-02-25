"""assgen visual model — 3D mesh generation and editing.

  assgen visual model create    text/image → 3D mesh (TripoSR / InstantMesh)
  assgen visual model highpoly  refine mesh to high-poly
  assgen visual model retopo    auto-retopology for game-ready topology
  assgen visual model splat     Gaussian Splatting / 3DGS generation
  assgen visual model edit      deform, boolean, or combine meshes
  assgen visual model optimize  LOD generation and poly reduction
  assgen visual model export    convert to engine-ready format
"""
from __future__ import annotations
from typing import Optional
import typer
from assgen.client.commands.submit import submit_job

app = typer.Typer(help="Generate and edit 3D meshes.", no_args_is_help=True)

_WAIT_OPT = typer.Option(None, "--wait/--no-wait")
_OUT_OPT  = typer.Option(None, "--output", "-o", help="Output file path (.glb/.obj/.fbx)")


@app.command("create")
def model_create(
    prompt: Optional[str] = typer.Option(None, "--prompt", "-p", help="Text description"),
    input_image: Optional[str] = typer.Option(None, "--input-image", "-i", help="Input image path or URL"),
    format: str = typer.Option("glb", "--format", "-f", help="Output format: glb obj fbx"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Generate a 3D mesh from text or an image (TripoSR / InstantMesh)."""
    if not prompt and not input_image:
        typer.echo("Provide at least --prompt or --input-image", err=True)
        raise typer.Exit(1)
    submit_job("visual.model.create", {
        "prompt": prompt,
        "input_image": input_image,
        "format": format,
        "output": output,
    }, wait=wait)


@app.command("highpoly")
def model_highpoly(
    input_mesh: str = typer.Argument(..., help="Input mesh path"),
    detail_level: int = typer.Option(3, "--detail", help="Detail level 1-5"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Refine a mesh to high-poly for normal map baking."""
    submit_job("visual.model.create", {
        "mode": "highpoly",
        "input": input_mesh,
        "detail_level": detail_level,
        "output": output,
    }, wait=wait)


@app.command("retopo")
def model_retopo(
    input_mesh: str = typer.Argument(..., help="High-poly or raw AI mesh to retopologise"),
    target_polys: Optional[int] = typer.Option(None, "--target-polys", help="Target polygon count"),
    quads: bool = typer.Option(True, "--quads/--tris", help="Prefer quads or triangles"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Auto-retopology: produce clean, game-ready mesh topology."""
    submit_job("visual.model.retopo", {
        "input": input_mesh,
        "target_polys": target_polys,
        "quads": quads,
        "output": output,
    }, wait=wait)


@app.command("splat")
def model_splat(
    images: list[str] = typer.Argument(..., help="Multi-view input images"),
    convert_mesh: bool = typer.Option(False, "--convert-mesh", help="Also export a triangle mesh"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Generate a Gaussian Splat (3DGS) from multi-view images."""
    submit_job("visual.model.splat", {
        "images": list(images),
        "convert_mesh": convert_mesh,
        "output": output,
    }, wait=wait)


@app.command("edit")
def model_edit(
    input_mesh: str = typer.Argument(..., help="Mesh to edit"),
    operation: str = typer.Option("deform", "--op", help="deform | boolean | combine"),
    prompt: Optional[str] = typer.Option(None, "--prompt", help="Edit guidance"),
    secondary: Optional[str] = typer.Option(None, "--secondary", help="Second mesh for boolean/combine"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Edit an existing mesh (deform, boolean, combine)."""
    submit_job("visual.model.create", {
        "mode": "edit",
        "input": input_mesh,
        "operation": operation,
        "prompt": prompt,
        "secondary": secondary,
        "output": output,
    }, wait=wait)


@app.command("optimize")
def model_optimize(
    input_mesh: str = typer.Argument(..., help="Mesh to optimise"),
    lods: int = typer.Option(3, "--lods", help="Number of LOD levels"),
    target_polys: Optional[int] = typer.Option(None, "--target-polys"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Generate LOD variants and reduce polygon count."""
    submit_job("visual.model.retopo", {
        "mode": "optimize",
        "input": input_mesh,
        "lods": lods,
        "target_polys": target_polys,
        "output": output,
    }, wait=wait)


@app.command("export")
def model_export(
    input_mesh: str = typer.Argument(..., help="Mesh to export"),
    format: str = typer.Option("glb", "--format", "-f", help="glb obj fbx uasset"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Convert and export a mesh to a specific engine format."""
    submit_job("pipeline.integrate.export", {
        "input": input_mesh,
        "format": format,
        "output": output,
    }, wait=wait)
