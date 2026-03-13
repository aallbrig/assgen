"""assgen pipeline — workflow orchestration, batch processing, and engine integration.

  assgen pipeline workflow create   define a multi-step asset workflow
  assgen pipeline workflow run      execute a saved workflow with inputs
  assgen pipeline workflow list     list available workflows
  assgen pipeline batch queue       enqueue a batch of jobs from a manifest
  assgen pipeline batch variant     generate style / damage variants of an asset
  assgen pipeline batch status      show batch job status
  assgen pipeline integrate export  convert and export to engine format
  assgen pipeline integrate prefab  bundle assets into an engine prefab
  assgen pipeline integrate script  generate attach-point / behavior stubs
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from assgen.client.commands.submit import submit_job
from assgen.client.output import console

app = typer.Typer(help="Workflow orchestration, batching, and engine integration.", no_args_is_help=True)

# ---------------------------------------------------------------------------
# workflow sub-app
# ---------------------------------------------------------------------------
workflow_app = typer.Typer(help="Define and run multi-step asset workflows.")
app.add_typer(workflow_app, name="workflow")


@workflow_app.command("create")
def workflow_create(
    name: str = typer.Argument(..., help="Workflow name"),
    steps: list[str] = typer.Argument(
        ...,
        help="Ordered job types, e.g. visual.concept.generate visual.model.splat",
    ),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Save workflow YAML to path"),
    chain: bool = typer.Option(
        True, "--chain/--no-chain",
        help="Auto-chain each step's output into the next step's upstream_files (default: on)",
    ),
) -> None:
    """Define a new multi-step workflow (sequence of job types).

    By default, each step's output is automatically chained into the next step
    as upstream_files. Use --no-chain to submit all steps independently.
    """
    from assgen.config import get_config_dir
    import yaml as _yaml

    step_defs: list[dict] = []
    for i, jt in enumerate(steps):
        entry: dict = {"id": f"step_{i + 1}", "job_type": jt}
        if chain and i > 0:
            entry["from_step"] = f"step_{i}"
        step_defs.append(entry)

    wf = {"name": name, "chain": chain, "steps": step_defs}
    out_path = Path(output) if output else (get_config_dir() / "workflows" / f"{name}.yaml")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        _yaml.safe_dump(wf, f, sort_keys=False)
    console.print(f"[green]Workflow saved:[/green] {out_path}")


@workflow_app.command("run")
def workflow_run(
    name: str = typer.Argument(..., help="Workflow name or path to YAML"),
    inputs: Optional[str] = typer.Option(None, "--inputs", help="JSON string of input params"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print steps without executing"),
) -> None:
    """Execute a saved workflow, chaining each step's output into the next.

    Unlike a simple batch submit, each step waits for the previous to complete
    and receives its output files as upstream_files — enabling real multi-step
    pipelines where later steps depend on earlier outputs.
    """
    from assgen.config import get_config_dir
    import yaml as _yaml
    from assgen.client.output import console

    wf_path = Path(name) if Path(name).exists() else (get_config_dir() / "workflows" / f"{name}.yaml")
    if not wf_path.exists():
        typer.echo(f"Workflow not found: {name}", err=True)
        raise typer.Exit(1)

    with wf_path.open() as f:
        wf = _yaml.safe_load(f)

    steps = wf.get("steps", [])
    # Support legacy format where steps is a plain list of job_type strings
    if steps and isinstance(steps[0], str):
        steps = [{"id": f"step_{i+1}", "job_type": s} for i, s in enumerate(steps)]

    global_params = json.loads(inputs) if inputs else {}
    wf_name = wf.get("name", name)

    if dry_run:
        console.print(f"[bold]Workflow:[/bold] {wf_name}  [dim]({len(steps)} steps, dry-run)[/dim]")
        for step in steps:
            src = f"  ← from {step['from_step']!r}" if step.get("from_step") else ""
            console.print(f"  [cyan]{step['id']}[/cyan]  {step['job_type']}{src}")
        return

    console.print(f"[bold]Running workflow:[/bold] {wf_name}  ({len(steps)} steps)")

    from assgen.client.compose import run_pipeline

    def _on_step(step_id: str, status: str, msg: str) -> None:
        icons = {"SUBMITTING": "⏳", "RUNNING": "🔄", "DONE": "✅"}
        icon = icons.get(status, "·")
        console.print(f"  {icon} [{step_id}] {msg}")

    try:
        results = run_pipeline(steps, global_params=global_params, on_step=_on_step)
        console.print(f"\n[green]✓ Workflow complete[/green]  ({len(results)} steps)")
    except RuntimeError as exc:
        console.print(f"[red]✗ Workflow failed:[/red] {exc}")
        raise typer.Exit(1)


@workflow_app.command("list")
def workflow_list() -> None:
    """List all saved workflows."""
    from assgen.config import get_config_dir
    wf_dir = get_config_dir() / "workflows"
    if not wf_dir.exists() or not list(wf_dir.glob("*.yaml")):
        console.print("[dim]No workflows defined yet. Use: assgen pipeline workflow create[/dim]")
        return
    for f in sorted(wf_dir.glob("*.yaml")):
        console.print(f"  {f.stem}  [dim]({f})[/dim]")


# ---------------------------------------------------------------------------
# batch sub-app
# ---------------------------------------------------------------------------
batch_app = typer.Typer(help="Batch job queuing and variant generation.")
app.add_typer(batch_app, name="batch")


@batch_app.command("queue")
def batch_queue(
    manifest: str = typer.Argument(..., help="Path to JSON manifest file"),
    wait: Optional[bool] = typer.Option(None, "--wait/--no-wait"),
) -> None:
    """Enqueue a batch of jobs from a JSON manifest file.

    Manifest format:
      [{"job_type": "visual.model.create", "params": {"prompt": "..."}, "priority": 0}, ...]
    """
    items = json.loads(Path(manifest).read_text())
    console.print(f"Queuing {len(items)} jobs from {manifest}")
    for item in items:
        submit_job(item["job_type"], item.get("params", {}),
                   priority=item.get("priority", 0), wait=wait)


@batch_app.command("variant")
def batch_variant(
    input_asset: str = typer.Argument(..., help="Base asset path"),
    variants: int = typer.Option(4, "--count", "-n", help="Number of variants"),
    style: Optional[str] = typer.Option(None, "--style", help="Style description for variants"),
    damage: bool = typer.Option(False, "--damage", help="Generate damage-state variants"),
    wait: Optional[bool] = typer.Option(None, "--wait/--no-wait"),
) -> None:
    """Generate style or damage-state variants of an existing asset."""
    for i in range(variants):
        submit_job("visual.texture.generate", {
            "mode": "variant",
            "input": input_asset,
            "variant_index": i,
            "style": style,
            "damage": damage,
        }, wait=wait)


@batch_app.command("status")
def batch_status(limit: int = typer.Option(20, "--limit", "-n")) -> None:
    """Show recent batch / queue status (active + recently completed jobs)."""
    from assgen.client.api import get_client, APIError
    from assgen.client.output import print_jobs_table, abort_with_error
    with get_client() as client:
        try:
            jobs = client.list_jobs(statuses=["QUEUED", "RUNNING"], limit=limit)
        except APIError as e:
            abort_with_error(str(e))
    print_jobs_table(jobs)


# ---------------------------------------------------------------------------
# integrate sub-app
# ---------------------------------------------------------------------------
integrate_app = typer.Typer(help="Engine export, prefab bundling, and script generation.")
app.add_typer(integrate_app, name="integrate")


@integrate_app.command("export")
def integrate_export(
    input_asset: str = typer.Argument(..., help="Asset to export"),
    engine: str = typer.Option("unity", "--engine", help="unity | unreal | godot"),
    format: Optional[str] = typer.Option(None, "--format", help="Override output format"),
    wait: Optional[bool] = typer.Option(None, "--wait/--no-wait"),
) -> None:
    """Export an asset to a specific game engine format."""
    fmt = format or {"unity": "prefab", "unreal": "uasset", "godot": "tres"}.get(engine, "glb")
    submit_job("pipeline.integrate.export", {
        "input": input_asset,
        "engine": engine,
        "format": fmt,
    }, wait=wait)


@integrate_app.command("prefab")
def integrate_prefab(
    assets: list[str] = typer.Argument(..., help="Asset files to bundle into a prefab"),
    name: Optional[str] = typer.Option(None, "--name", help="Prefab name"),
    engine: str = typer.Option("unity", "--engine"),
    wait: Optional[bool] = typer.Option(None, "--wait/--no-wait"),
) -> None:
    """Bundle multiple assets into an engine prefab or scene package."""
    submit_job("pipeline.integrate.export", {
        "mode": "prefab",
        "assets": list(assets),
        "name": name,
        "engine": engine,
    }, wait=wait)


@integrate_app.command("script")
def integrate_script(
    mesh: str = typer.Argument(..., help="Mesh to generate behavior stubs for"),
    behaviors: str = typer.Option("interact,damage,loot", "--behaviors",
                                  help="Comma-separated behavior types to stub"),
    language: str = typer.Option("csharp", "--language", help="csharp | gdscript | blueprint"),
    wait: Optional[bool] = typer.Option(None, "--wait/--no-wait"),
) -> None:
    """Generate behavior script stubs and attach-point metadata for a mesh."""
    submit_job("pipeline.integrate.export", {
        "mode": "script",
        "input": mesh,
        "behaviors": [b.strip() for b in behaviors.split(",")],
        "language": language,
    }, wait=wait)


# ---------------------------------------------------------------------------
# asset sub-app
# ---------------------------------------------------------------------------
asset_app = typer.Typer(help="Asset manifest, validation, rename, and budget report.")
app.add_typer(asset_app, name="asset")


@asset_app.command("manifest")
def asset_manifest(
    directory: str = typer.Argument(..., help="Directory to scan"),
    wait: Optional[bool] = typer.Option(None, "--wait/--no-wait"),
) -> None:
    """Walk a directory and produce a manifest.json with file metadata."""
    submit_job("pipeline.asset.manifest", {"directory": directory}, wait=wait)


@asset_app.command("validate")
def asset_validate(
    directory: str = typer.Argument(..., help="Directory to validate"),
    max_texture_mb: float = typer.Option(16.0, "--max-texture-mb",
                                          help="Max texture file size in MB"),
    max_mesh_verts: int = typer.Option(100_000, "--max-mesh-verts",
                                        help="Max vertex count per mesh"),
    wait: Optional[bool] = typer.Option(None, "--wait/--no-wait"),
) -> None:
    """Check for oversized textures, non-pow2 textures, and high-poly meshes."""
    submit_job("pipeline.asset.validate", {
        "directory": directory,
        "max_texture_mb": max_texture_mb,
        "max_mesh_verts": max_mesh_verts,
    }, wait=wait)


@asset_app.command("rename")
def asset_rename(
    directory: str = typer.Argument(..., help="Directory containing files to rename"),
    convention: str = typer.Option("snake_case", "--convention", "-c",
                                    help="snake_case | PascalCase | kebab-case"),
    prefix: Optional[str] = typer.Option(None, "--prefix", help="Optional name prefix"),
    suffix: Optional[str] = typer.Option(None, "--suffix", help="Optional name suffix"),
    dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run",
                                  help="Plan only (default) or execute renames"),
    wait: Optional[bool] = typer.Option(None, "--wait/--no-wait"),
) -> None:
    """Batch rename assets to a naming convention (dry-run by default)."""
    submit_job("pipeline.asset.rename", {
        "directory": directory,
        "convention": convention,
        "prefix": prefix,
        "suffix": suffix,
        "dry_run": dry_run,
    }, wait=wait)


@asset_app.command("report")
def asset_report(
    directory: str = typer.Argument(..., help="Directory to report on"),
    wait: Optional[bool] = typer.Option(None, "--wait/--no-wait"),
) -> None:
    """Generate a size-budget report grouped by asset type."""
    submit_job("pipeline.asset.report", {"directory": directory}, wait=wait)


# ---------------------------------------------------------------------------
# git sub-app
# ---------------------------------------------------------------------------
git_app = typer.Typer(help="Git and VCS helpers for game asset repos.")
app.add_typer(git_app, name="git")


@git_app.command("lfs-rules")
def git_lfs_rules(
    directory: str = typer.Argument(..., help="Directory to scan for asset types"),
    wait: Optional[bool] = typer.Option(None, "--wait/--no-wait"),
) -> None:
    """Scan asset extensions and generate .gitattributes LFS rules."""
    submit_job("pipeline.git.lfs_rules", {"directory": directory}, wait=wait)
