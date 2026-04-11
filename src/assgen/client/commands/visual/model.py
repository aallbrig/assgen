"""assgen visual model — 3D mesh generation and editing.

  assgen visual model create    text/image → 3D mesh (InstantMesh)
  assgen visual model highpoly  refine mesh to high-poly
  assgen visual model retopo    auto-retopology for game-ready topology
  assgen visual model splat     Gaussian Splatting / 3DGS generation
  assgen visual model edit      deform, boolean, or combine meshes
  assgen visual model optimize  LOD generation and poly reduction
  assgen visual model export    convert to engine-ready format
"""
from __future__ import annotations

import typer

from assgen.client.commands.submit import submit_job

app = typer.Typer(help="Generate and edit 3D meshes.", no_args_is_help=True)

_WAIT_OPT = typer.Option(None, "--wait/--no-wait", help="Block until the job completes and stream live progress")
_OUT_OPT  = typer.Option(None, "--output", "-o", help="Output file path (.glb/.obj/.fbx)")


@app.command("create")
def model_create(
    prompt: str | None = typer.Option(None, "--prompt", "-p", help="Text description"),
    input_image: str | None = typer.Option(None, "--input-image", "-i", help="Input image path or URL"),
    format: str = typer.Option("glb", "--format", "-f", help="Output format: glb obj fbx"),
    target_faces: int | None = typer.Option(None, "--target-faces", help="Max triangles after decimation (default 10 000)"),
    output: str | None = _OUT_OPT,
    wait: bool | None = _WAIT_OPT,
    model_id: str | None = typer.Option(None, "--model-id", help="Override HF model (validated by server)"),
) -> None:
    """Generate a 3D mesh from text or an image using InstantMesh (multi-view diffusion).

    Examples:
        assgen gen visual model create "low-poly medieval sword" --wait
        assgen gen visual model create "cartoon treasure chest" --format glb --wait
        assgen gen visual model create "sci-fi pistol" --format obj --triangulate --wait
        assgen gen visual model create "wooden barrel" --from-job <concept-job-id> --wait
    """
    if not prompt and not input_image:
        typer.echo("Provide at least --prompt or --input-image", err=True)
        raise typer.Exit(1)
    submit_job("visual.model.create", {
        "prompt": prompt,
        "input_image": input_image,
        "format": format,
        "target_faces": target_faces,
        "output": output,
    }, wait=wait, model_id=model_id)


@app.command("highpoly")
def model_highpoly(
    input_mesh: str = typer.Argument(..., help="Input mesh path"),
    detail_level: int = typer.Option(3, "--detail", help="Detail level 1-5"),
    output: str | None = _OUT_OPT,
    wait: bool | None = _WAIT_OPT,
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
    target_polys: int | None = typer.Option(None, "--target-polys", help="Target polygon count"),
    quads: bool = typer.Option(True, "--quads/--tris", help="Prefer quads or triangles"),
    output: str | None = _OUT_OPT,
    wait: bool | None = _WAIT_OPT,
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
    convert_mesh: bool = typer.Option(False, "--convert-mesh", help="Also export a .ply alongside the .glb"),
    target_faces: int = typer.Option(10_000, "--target-faces", help="Max triangles after trimesh decimation"),
    output: str | None = _OUT_OPT,
    wait: bool | None = _WAIT_OPT,
) -> None:
    """Generate a triangle mesh from multi-view images (TripoSR).

    NOTE: Output is a triangle mesh (PLY/GLB), NOT a Gaussian Splat (3DGS).
    True 3DGS training requires a separate pipeline such as nerfstudio or the
    original gaussian-splatting trainer.  The mesh output can be fed into a
    downstream 3DGS trainer as a point-cloud initialisation.
    """
    submit_job("visual.model.splat", {
        "images": list(images),
        "convert_mesh": convert_mesh,
        "target_faces": target_faces,
        "output": output,
    }, wait=wait)


@app.command("edit")
def model_edit(
    input_mesh: str = typer.Argument(..., help="Mesh to edit"),
    operation: str = typer.Option("deform", "--op", help="deform | boolean | combine"),
    prompt: str | None = typer.Option(None, "--prompt", help="Edit guidance"),
    secondary: str | None = typer.Option(None, "--secondary", help="Second mesh for boolean/combine"),
    output: str | None = _OUT_OPT,
    wait: bool | None = _WAIT_OPT,
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
    target_polys: int | None = typer.Option(None, "--target-polys"),
    output: str | None = _OUT_OPT,
    wait: bool | None = _WAIT_OPT,
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
    output: str | None = _OUT_OPT,
    wait: bool | None = _WAIT_OPT,
) -> None:
    """Convert and export a mesh to a specific engine format."""
    submit_job("pipeline.integrate.export", {
        "input": input_mesh,
        "format": format,
        "output": output,
    }, wait=wait)
