"""assgen models — model catalog and installation management.

  assgen models list          list all configured models with install status
  assgen models status <id>   show detail for a specific model
  assgen models install        install all models from the catalog
  assgen models install <id>  install a specific model
"""
from __future__ import annotations

from typing import Optional

import typer
from rich.table import Table

from assgen.client.api import APIError, get_client
from assgen.client.output import abort_with_error, console

app = typer.Typer(help="Manage HuggingFace models used by assgen.", no_args_is_help=True)


@app.command("list")
def models_list(
    installed_only: bool = typer.Option(False, "--installed", help="Show only installed models"),
) -> None:
    """List all models in the catalog with their installation status."""
    with get_client() as client:
        try:
            models = client.list_models()
        except APIError as e:
            abort_with_error(str(e))

    if installed_only:
        models = [m for m in models if m["installed"]]

    table = Table(title="Model Catalog", show_lines=True, header_style="bold cyan")
    table.add_column("Model ID",     min_width=30)
    table.add_column("Name",         min_width=20)
    table.add_column("Installed",    width=10)
    table.add_column("Last Used",    width=20)
    table.add_column("Size",         width=10)
    table.add_column("Job Types",    min_width=30)

    for m in models:
        installed_str = "[green]✓[/green]" if m["installed"] else "[dim]–[/dim]"
        last_used = (m.get("last_used_at") or "")[:16].replace("T", " ")
        size = _fmt_bytes(m.get("size_bytes")) if m.get("size_bytes") else "–"
        job_types = "\n".join(m.get("job_types") or [])
        table.add_row(
            m["model_id"],
            m["name"],
            installed_str,
            last_used or "–",
            size,
            job_types,
        )

    console.print(table)


@app.command("status")
def models_status(model_id: str = typer.Argument(..., help="HuggingFace model ID")) -> None:
    """Show installation status and usage history for a specific model."""
    with get_client() as client:
        try:
            m = client.get_model(model_id)
        except APIError as e:
            abort_with_error(str(e))

    installed = "[green]Installed[/green]" if m["installed"] else "[yellow]Not installed[/yellow]"
    console.print(f"\n[bold]Model ID:[/bold] {m['model_id']}")
    console.print(f"[bold]Name:[/bold]     {m['name']}")
    console.print(f"[bold]Status:[/bold]   {installed}")
    if m.get("local_path"):
        console.print(f"[bold]Path:[/bold]     {m['local_path']}")
    if m.get("installed_at"):
        console.print(f"[bold]Installed:[/bold] {m['installed_at'][:19].replace('T', ' ')}")
    if m.get("last_used_at"):
        console.print(f"[bold]Last used:[/bold] {m['last_used_at'][:19].replace('T', ' ')}")
    if m.get("size_bytes"):
        console.print(f"[bold]Size:[/bold]     {_fmt_bytes(m['size_bytes'])}")
    if m.get("job_types"):
        console.print("[bold]Job types:[/bold]")
        for jt in m["job_types"]:
            console.print(f"  • {jt}")


@app.command("install")
def models_install(
    model_ids: Optional[list[str]] = typer.Argument(
        None,
        help="Model IDs to install. Omit to install all catalog models.",
    ),
    all_models: bool = typer.Option(
        False, "--all", "-a",
        help="Install every model in the catalog",
    ),
) -> None:
    """Download and cache models from HuggingFace Hub.

    Without arguments, installs all models configured in the catalog.
    """
    ids: list[str] | None = None
    if model_ids:
        ids = list(model_ids)
    elif not all_models:
        # If no specific IDs and no --all, still install everything
        typer.confirm("Install all catalog models? This may download several GB.", abort=True)

    with get_client() as client:
        try:
            result = client.install_models(model_ids=ids)
        except APIError as e:
            abort_with_error(str(e))

    queued = result.get("queued", [])
    if queued == "all":
        console.print("[green]Queued download of all catalog models.[/green]")
    else:
        for mid in queued:
            console.print(f"[green]Queued:[/green] {mid}")
    console.print("[dim]Monitor progress with: assgen models list[/dim]")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_bytes(n: int | None) -> str:
    if n is None:
        return "–"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024  # type: ignore[assignment]
    return f"{n:.1f} PB"
