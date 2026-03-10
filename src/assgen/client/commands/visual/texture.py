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
    albedo: str = typer.Argument(..., help="Source albedo/diffuse image (PNG or JPEG)"),
    maps: str = typer.Option(
        "normal,roughness,metallic,ao,height",
        "--maps",
        help="Comma-separated PBR maps to derive: normal roughness metallic ao height",
    ),
    resolution: int = typer.Option(None, "--resolution", "-r",
                                    help="Resize albedo before processing (e.g. 1024)"),
    normal_strength: float = typer.Option(2.0, "--normal-strength",
                                           help="Strength multiplier for normal map gradient"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Derive a full PBR material set (normal, roughness, metallic, AO, height) from an albedo image."""
    submit_job("visual.texture.pbr", {
        "albedo": albedo,
        "maps": [m.strip() for m in maps.split(",")],
        "resolution": resolution,
        "normal_strength": normal_strength,
        "output": output,
    }, wait=wait)


@app.command("channel-pack")
def texture_channel_pack(
    r: str = typer.Option(..., "--r", help="Red channel image path"),
    g: str = typer.Option(..., "--g", help="Green channel image path"),
    b: str = typer.Option(..., "--b", help="Blue channel image path"),
    a: Optional[str] = typer.Option(None, "--a", help="Alpha channel image path (optional)"),
    output_name: str = typer.Option("packed.png", "--output-name", help="Output filename"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Pack separate R/G/B/A channel images into a single RGBA texture."""
    submit_job("visual.texture.channel_pack", {
        "r": r, "g": g, "b": b, "a": a,
        "output_name": output_name,
        "output": output,
    }, wait=wait)


@app.command("convert")
def texture_convert(
    input_file: str = typer.Argument(..., help="Source image file"),
    format: str = typer.Option("png", "--format", "-f",
                               help="Target format: png jpg tga webp exr"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Convert an image to a different format (PNG/TGA/JPG/EXR → WebP/PNG/TGA/JPG)."""
    submit_job("visual.texture.convert", {
        "input": input_file, "format": format, "output": output,
    }, wait=wait)


@app.command("atlas-pack")
def texture_atlas_pack(
    inputs: list[str] = typer.Argument(..., help="Image files to pack into atlas"),
    size: str = typer.Option("2048x2048", "--size", "-s", help="Atlas dimensions WxH"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Pack images into a texture atlas + UV manifest JSON."""
    submit_job("visual.texture.atlas_pack", {
        "inputs": list(inputs), "size": size, "output": output,
    }, wait=wait)


@app.command("mipmap")
def texture_mipmap(
    input_file: str = typer.Argument(..., help="Source image file"),
    min_size: int = typer.Option(1, "--min-size", help="Stop at this minimum dimension (px)"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Generate a full mipmap chain and save each level as a PNG."""
    submit_job("visual.texture.mipmap", {
        "input": input_file, "min_size": min_size, "output": output,
    }, wait=wait)


@app.command("normalmap-convert")
def texture_normalmap_convert(
    input_file: str = typer.Argument(..., help="Normal map image file"),
    from_format: str = typer.Option("dx", "--from-format",
                                     help="Source convention: dx | gl"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Flip G channel to convert a normal map between DirectX and OpenGL conventions."""
    submit_job("visual.texture.normalmap_convert", {
        "input": input_file, "from_format": from_format, "output": output,
    }, wait=wait)


@app.command("seamless")
def texture_seamless(
    input_file: str = typer.Argument(..., help="Source texture image"),
    blend_width: float = typer.Option(0.1, "--blend-width",
                                       help="Blend zone as fraction of image size (0.01–0.49)"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Fix tile seams via offset-blend to make a texture seamlessly tileable."""
    submit_job("visual.texture.seamless", {
        "input": input_file, "blend_width": blend_width, "output": output,
    }, wait=wait)


@app.command("resize")
def texture_resize(
    input_file: str = typer.Argument(..., help="Source texture image"),
    width: Optional[int] = typer.Option(None, "--width", "-W", help="Target width in pixels"),
    height: Optional[int] = typer.Option(None, "--height", "-H", help="Target height in pixels"),
    pow2: bool = typer.Option(False, "--pow2", help="Snap to next power-of-2"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Resize a texture image to specified dimensions."""
    submit_job("visual.texture.resize", {
        "input": input_file,
        "width": width,
        "height": height,
        "pow2": pow2,
        "output": output,
    }, wait=wait)


@app.command("report")
def texture_report(
    inputs: list[str] = typer.Argument(None, help="Image files to report on (or use --directory)"),
    directory: Optional[str] = typer.Option(None, "--directory", "-d",
                                              help="Directory to scan for textures"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Generate a texture report: format, dimensions, and estimated GPU memory."""
    submit_job("visual.texture.report", {
        "inputs": list(inputs) if inputs else [],
        "directory": directory,
        "output": output,
    }, wait=wait)
