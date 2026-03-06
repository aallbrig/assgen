"""assgen visual texture — texturing, PBR maps, and baking.

  assgen visual texture generate   text / mesh → albedo + PBR maps
  assgen visual texture apply      project generated textures onto a mesh
  assgen visual texture bake       high-to-low poly normal / AO bake
  assgen visual texture pbr        create / edit a full PBR material set
"""
from __future__ import annotations
from typing import Optional
import typer
from assgen.client.commands.submit import submit_job

app = typer.Typer(help="Texture generation, PBR maps, and baking.", no_args_is_help=True)

_WAIT_OPT = typer.Option(None, "--wait/--no-wait", help="Block until the job completes and stream live progress")
_OUT_OPT  = typer.Option(None, "--output", "-o", help="Output file or directory path")


@app.command("generate")
def texture_generate(
    prompt: Optional[str] = typer.Option(None, "--prompt", "-p", help="Texture description"),
    input_mesh: Optional[str] = typer.Option(None, "--mesh", "-m", help="Mesh to texture"),
    resolution: int = typer.Option(1024, "--resolution", "-r", help="Texture resolution (px)"),
    maps: str = typer.Option("albedo,normal,roughness,metallic", "--maps",
                             help="Comma-separated PBR maps to generate"),
    style: Optional[str] = typer.Option(None, "--style", help="Material style, e.g. 'worn stone'"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Generate albedo and PBR maps from a text prompt or mesh reference."""
    submit_job("visual.texture.generate", {
        "prompt": prompt,
        "input_mesh": input_mesh,
        "resolution": resolution,
        "maps": [m.strip() for m in maps.split(",")],
        "style": style,
        "output": output,
    }, wait=wait)


@app.command("apply")
def texture_apply(
    mesh: str = typer.Argument(..., help="Mesh to apply textures to"),
    texture_dir: str = typer.Argument(..., help="Directory containing PBR texture maps"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Apply a PBR texture set to a mesh (UV-based projection)."""
    submit_job("visual.texture.generate", {
        "mode": "apply",
        "input_mesh": mesh,
        "texture_dir": texture_dir,
        "output": output,
    }, wait=wait)


@app.command("bake")
def texture_bake(
    highpoly: str = typer.Argument(..., help="High-poly source mesh"),
    lowpoly: str = typer.Argument(..., help="Low-poly target mesh"),
    maps: str = typer.Option("normal,ao,curvature", "--maps",
                             help="Maps to bake: normal ao curvature height"),
    resolution: int = typer.Option(2048, "--resolution", "-r"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Bake normal, AO, and curvature from a high-poly to low-poly mesh."""
    submit_job("visual.texture.bake", {
        "highpoly": highpoly,
        "lowpoly": lowpoly,
        "maps": [m.strip() for m in maps.split(",")],
        "resolution": resolution,
        "output": output,
    }, wait=wait)


@app.command("pbr")
def texture_pbr(
    prompt: str = typer.Argument(..., help="Material description, e.g. 'aged bronze'"),
    resolution: int = typer.Option(1024, "--resolution", "-r"),
    seamless: bool = typer.Option(True, "--seamless/--non-seamless"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Create a full seamless PBR material set from a text description."""
    submit_job("visual.texture.generate", {
        "mode": "pbr",
        "prompt": prompt,
        "resolution": resolution,
        "seamless": seamless,
        "maps": ["albedo", "normal", "roughness", "metallic", "height", "ao"],
        "output": output,
    }, wait=wait)
