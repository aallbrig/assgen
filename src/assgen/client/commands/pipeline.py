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
    steps: list[str] = typer.Argument(..., help="Ordered job types, e.g. visual.model.create visual.texture.generate"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Save workflow YAML to path"),
) -> None:
    """Define a new multi-step workflow (sequence of job types)."""
    from assgen.config import get_config_dir
    import yaml as _yaml
    wf = {"name": name, "steps": list(steps)}
    out_path = Path(output) if output else (get_config_dir() / "workflows" / f"{name}.yaml")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        _yaml.safe_dump(wf, f)
    console.print(f"[green]Workflow saved:[/green] {out_path}")


@workflow_app.command("run")
def workflow_run(
    name: str = typer.Argument(..., help="Workflow name or path to YAML"),
    inputs: Optional[str] = typer.Option(None, "--inputs", help="JSON string of input params"),
    wait: Optional[bool] = typer.Option(None, "--wait/--no-wait"),
) -> None:
    """Execute a saved workflow with a set of inputs."""
    from assgen.config import get_config_dir
    import yaml as _yaml

    wf_path = Path(name) if Path(name).exists() else (get_config_dir() / "workflows" / f"{name}.yaml")
    if not wf_path.exists():
        typer.echo(f"Workflow not found: {name}", err=True)
        raise typer.Exit(1)

    with wf_path.open() as f:
        wf = _yaml.safe_load(f)

    params = json.loads(inputs) if inputs else {}
    console.print(f"Running workflow [bold]{wf['name']}[/bold] ({len(wf['steps'])} steps)")
    for step in wf["steps"]:
        console.print(f"  → [cyan]{step}[/cyan]")
        submit_job(step, params, wait=wait)


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
