"""assgen scene lighting — HDRI, probes, volumetrics, and lightmaps.

  assgen scene lighting hdri        text → equirectangular HDRI sky
  assgen scene lighting probes      generate reflection / light probes
  assgen scene lighting volumetrics create volumetric fog / cloud assets
  assgen scene lighting bake        bake GI lightmaps for a scene
"""
from __future__ import annotations
from typing import Optional
import typer
from assgen.client.commands.submit import submit_job

app = typer.Typer(help="HDRI skies, light probes, volumetrics, and lightmap baking.", no_args_is_help=True)

_WAIT_OPT = typer.Option(None, "--wait/--no-wait")
_OUT_OPT  = typer.Option(None, "--output", "-o")


@app.command("hdri")
def lighting_hdri(
    prompt: str = typer.Argument(..., help="Sky / environment description, e.g. 'sunset desert sky'"),
    resolution: int = typer.Option(4096, "--resolution", "-r",
                                   help="Output resolution (width of equirectangular image)"),
    hdr_format: str = typer.Option("exr", "--format", help="exr | hdr"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Generate an HDR environment / sky map from a text description."""
    submit_job("scene.lighting.hdri", {
        "prompt": prompt,
        "resolution": resolution,
        "format": hdr_format,
        "output": output,
    }, wait=wait)


@app.command("probes")
def lighting_probes(
    scene: str = typer.Argument(..., help="Scene file to generate probes for"),
    probe_type: str = typer.Option("reflection", "--type",
                                   help="reflection | light | irradiance"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Generate reflection or irradiance probes for a scene."""
    submit_job("scene.lighting.hdri", {
        "mode": "probes",
        "input": scene,
        "probe_type": probe_type,
        "output": output,
    }, wait=wait)


@app.command("volumetrics")
def lighting_volumetrics(
    prompt: str = typer.Argument(..., help="Volume description, e.g. 'thick morning fog'"),
    vol_type: str = typer.Option("fog", "--type", help="fog | clouds | smoke | dust"),
    density: float = typer.Option(0.5, "--density", help="Volume density 0.0-1.0"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Generate volumetric fog, cloud, or atmosphere assets."""
    submit_job("scene.lighting.hdri", {
        "mode": "volumetrics",
        "prompt": prompt,
        "vol_type": vol_type,
        "density": density,
        "output": output,
    }, wait=wait)


@app.command("bake")
def lighting_bake(
    scene: str = typer.Argument(..., help="Scene file to bake lighting for"),
    quality: str = typer.Option("medium", "--quality", help="low | medium | high"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Bake global illumination lightmaps for a scene."""
    submit_job("scene.lighting.hdri", {
        "mode": "bake",
        "input": scene,
        "quality": quality,
        "output": output,
    }, wait=wait)
