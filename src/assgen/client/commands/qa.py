"""assgen qa — asset validation and performance testing.

  assgen qa validate   check mesh / texture errors
  assgen qa perf       test VRAM usage and polygon budget
  assgen qa style      consistency check against art guide
  assgen qa report     generate a QA issues report
"""
from __future__ import annotations

import typer

from assgen.client.commands.submit import submit_job

app = typer.Typer(help="Asset validation, performance testing, and QA reporting.", no_args_is_help=True)

_WAIT_OPT = typer.Option(None, "--wait/--no-wait", help="Block until the job completes and stream live progress")
_OUT_OPT  = typer.Option(None, "--output", "-o", help="Output file or directory path")


@app.command("validate")
def qa_validate(
    asset: str = typer.Argument(..., help="Asset file or directory to validate"),
    checks: str = typer.Option(
        "normals,uvs,manifold,scale,naming",
        "--checks",
        help="Comma-separated checks: normals uvs manifold scale naming textures",
    ),
    strict: bool = typer.Option(False, "--strict", help="Fail on warnings as well as errors"),
    output: str | None = _OUT_OPT,
    wait: bool | None = _WAIT_OPT,
) -> None:
    """Run automated validation checks on an asset (normals, UVs, manifold, etc.)."""
    submit_job("qa.validate", {
        "input": asset,
        "checks": [c.strip() for c in checks.split(",")],
        "strict": strict,
        "output": output,
    }, wait=wait)


@app.command("perf")
def qa_perf(
    asset: str = typer.Argument(..., help="Asset to performance-test"),
    poly_budget: int | None = typer.Option(None, "--poly-budget", help="Max polygon count"),
    vram_budget_mb: int | None = typer.Option(None, "--vram-budget", help="VRAM budget in MB"),
    lod_preview: bool = typer.Option(False, "--lod-preview", help="Preview all LOD levels"),
    output: str | None = _OUT_OPT,
    wait: bool | None = _WAIT_OPT,
) -> None:
    """Analyse performance characteristics: poly count, VRAM, draw calls."""
    submit_job("qa.perf", {
        "input": asset,
        "poly_budget": poly_budget,
        "vram_budget_mb": vram_budget_mb,
        "lod_preview": lod_preview,
        "output": output,
    }, wait=wait)


@app.command("style")
def qa_style(
    asset: str = typer.Argument(..., help="Asset or directory to style-check"),
    style_guide: str | None = typer.Option(None, "--guide",
                                              help="Path to style guide image or YAML"),
    threshold: float = typer.Option(0.8, "--threshold", help="Similarity threshold 0.0-1.0"),
    output: str | None = _OUT_OPT,
    wait: bool | None = _WAIT_OPT,
) -> None:
    """Check assets for visual consistency with the project art style guide."""
    submit_job("qa.style", {
        "input": asset,
        "style_guide": style_guide,
        "threshold": threshold,
        "output": output,
    }, wait=wait)


@app.command("report")
def qa_report(
    asset_dir: str = typer.Argument(".", help="Directory of assets to include in the report"),
    format: str = typer.Option("markdown", "--format", help="markdown | json | html"),
    output: str | None = _OUT_OPT,
    wait: bool | None = _WAIT_OPT,
) -> None:
    """Generate a full QA issues report for a set of assets."""
    submit_job("qa.report", {
        "input": asset_dir,
        "format": format,
        "output": output,
    }, wait=wait)
