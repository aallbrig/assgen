"""assgen visual lod — LOD mesh generation.

  assgen gen visual lod generate   generate N LOD meshes via QEM decimation
"""
from __future__ import annotations
from typing import Optional
import typer
from assgen.client.commands.submit import submit_job

app = typer.Typer(help="LOD (Level of Detail) mesh generation.", no_args_is_help=True)

_WAIT_OPT = typer.Option(None, "--wait/--no-wait", help="Block until the job completes")
_OUT_OPT  = typer.Option(None, "--output", "-o", help="Output directory path")


@app.command("generate")
def lod_generate(
    input_file: str = typer.Argument(..., help="Source mesh file (glb, obj, ply, ...)"),
    num_lods: int = typer.Option(3, "--num-lods", "-n", help="Number of LOD levels to generate"),
    min_poly_count: int = typer.Option(100, "--min-poly-count",
                                        help="Minimum face count for the coarsest LOD"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Generate N LOD meshes via QEM decimation (pyfqmr or trimesh fallback)."""
    submit_job("visual.lod.generate", {
        "input": input_file,
        "num_lods": num_lods,
        "min_poly_count": min_poly_count,
        "output": output,
    }, wait=wait)
