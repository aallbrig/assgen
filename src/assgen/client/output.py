"""Shared CLI utilities: wait-with-progress, job result rendering, file download."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from assgen.client.api import APIClient, APIError
from assgen.config import load_client_config
from assgen.db import JobStatus

console = Console()
err_console = Console(stderr=True)


# ---------------------------------------------------------------------------
# Progress / wait helper
# ---------------------------------------------------------------------------

def wait_for_job(client: APIClient, job_id: str, timeout: float | None = None) -> dict[str, Any]:
    """Poll the server until the job reaches a terminal state.  Show a progress bar."""
    cfg = load_client_config()
    poll = float(cfg.get("poll_interval", 2.0))
    deadline = time.monotonic() + (timeout or float(cfg.get("default_timeout", 300)))

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task(f"[cyan]Job {job_id[:8]}…", total=100)

        while time.monotonic() < deadline:
            try:
                job = client.get_job(job_id)
            except APIError as e:
                err_console.print(f"[red]Error polling job: {e}")
                raise typer.Exit(1)

            pct = int((job.get("progress") or 0) * 100)
            msg = job.get("progress_message") or job["status"]
            progress.update(task, completed=pct, description=f"[cyan]{msg}")

            if job["status"] in JobStatus.TERMINAL:
                progress.update(task, completed=100)
                return job

            time.sleep(poll)

    raise TimeoutError(f"Timed out waiting for job {job_id} after {timeout}s")


# ---------------------------------------------------------------------------
# Output file download
# ---------------------------------------------------------------------------

def download_job_output(
    client: APIClient,
    job: dict[str, Any],
    dest_dir: Path | None = None,
) -> list[Path]:
    """Download output files for a completed job.

    For a local server (same host), skips download and returns the server-side
    path directly when it is accessible.  For remote servers, always downloads.

    Args:
        client: Connected API client.
        job: Completed job dict (must have status == COMPLETED).
        dest_dir: Directory to save downloaded files.  Defaults to cwd.

    Returns:
        List of local Paths for each saved file.
    """
    job_id: str = job["id"]
    try:
        filenames = client.list_job_files(job_id)
    except APIError:
        return []

    if not filenames:
        return []

    save_dir = dest_dir or Path.cwd()
    save_dir.mkdir(parents=True, exist_ok=True)

    saved: list[Path] = []
    for filename in filenames:
        dest = save_dir / filename
        # Avoid overwriting: add a suffix if needed
        if dest.exists():
            stem = dest.stem
            suffix = dest.suffix
            counter = 1
            while dest.exists():
                dest = save_dir / f"{stem}_{counter}{suffix}"
                counter += 1
        try:
            data = client.download_job_file(job_id, filename)
            dest.write_bytes(data)
            saved.append(dest)
        except APIError as e:
            err_console.print(f"[yellow]Warning: could not download {filename}: {e}[/yellow]")

    return saved


# ---------------------------------------------------------------------------
# Clean rendering helpers
# ---------------------------------------------------------------------------

def print_job_summary(
    job: dict[str, Any],
    saved_files: list[Path] | None = None,
) -> None:
    """Render a concise completion summary after --wait."""
    status = job["status"]
    status_color = {
        "COMPLETED": "green",
        "FAILED":    "red",
        "CANCELLED": "yellow",
    }.get(status, "white")

    job_id = job["id"]
    short_id = job_id[:8]

    # Timing
    duration_str = ""
    if job.get("started_at") and job.get("completed_at"):
        from datetime import datetime
        try:
            started  = datetime.fromisoformat(job["started_at"].replace("Z", "+00:00"))
            finished = datetime.fromisoformat(job["completed_at"].replace("Z", "+00:00"))
            secs = int((finished - started).total_seconds())
            if secs >= 60:
                duration_str = f"{secs // 60}m {secs % 60}s"
            else:
                duration_str = f"{secs}s"
        except Exception:
            pass

    console.print()
    if status == "COMPLETED":
        console.print(
            f"[bold {status_color}]✓  Job {short_id} completed"
            + (f" in {duration_str}" if duration_str else "")
            + "[/bold green]"
        )
    elif status == "FAILED":
        console.print(f"[bold red]✗  Job {short_id} failed[/bold red]")
    else:
        console.print(f"[bold yellow]  Job {short_id} {status.lower()}[/bold yellow]")

    console.print(f"   [dim]type:[/dim] {job['job_type']}")
    if job.get("model_id"):
        console.print(f"   [dim]model:[/dim] {job['model_id']}")

    if saved_files:
        console.print()
        console.print("[bold]Output files:[/bold]")
        for f in saved_files:
            size_str = _fmt_size(f.stat().st_size) if f.exists() else ""
            console.print(f"   [green]→[/green] {f}  [dim]{size_str}[/dim]")
    elif status == "COMPLETED":
        output = job.get("output") or {}
        files = output.get("files", []) if isinstance(output, dict) else []
        if files and not saved_files:
            console.print()
            console.print("[bold]Output files (server-side):[/bold]")
            for fname in files:
                console.print(f"   [dim]{fname}[/dim]")
            console.print(
                f"   [dim]Download: assgen jobs download {short_id}[/dim]"
            )

    if job.get("error"):
        console.print()
        console.print(Panel(job["error"], title="[red]Error[/red]", expand=False))

    console.print()


def print_job(job: dict[str, Any]) -> None:
    """Pretty-print a single job (used by assgen jobs status)."""
    status = job["status"]
    status_color = {
        "QUEUED":    "yellow",
        "RUNNING":   "blue",
        "COMPLETED": "green",
        "FAILED":    "red",
        "CANCELLED": "dim",
    }.get(status, "white")

    console.print(f"\n[bold]Job:[/bold]      {job['id'][:8]}  [dim]({job['id']})[/dim]")
    console.print(f"[bold]Type:[/bold]     {job['job_type']}")
    console.print(f"[bold]Status:[/bold]   [{status_color}]{status}[/{status_color}]")
    pct = int((job.get("progress") or 0) * 100)
    msg = job.get("progress_message") or ""
    console.print(f"[bold]Progress:[/bold] {pct}%" + (f"  {msg}" if msg else ""))
    console.print(f"[bold]Created:[/bold]  {job['created_at'][:19].replace('T', ' ')}")
    if job.get("started_at"):
        console.print(f"[bold]Started:[/bold]  {job['started_at'][:19].replace('T', ' ')}")
    if job.get("completed_at"):
        console.print(f"[bold]Done:[/bold]     {job['completed_at'][:19].replace('T', ' ')}")

    output = job.get("output")
    if output and isinstance(output, dict):
        files = output.get("files", [])
        if files:
            console.print("[bold]Files:[/bold]    " + ", ".join(files))
            console.print(f"   [dim]Download: assgen jobs download {job['id'][:8]}[/dim]")
        if output.get("stub"):
            console.print(f"   [dim yellow]⚠  {output.get('note', 'stub result')}[/dim yellow]")

    if job.get("error"):
        console.print()
        console.print(Panel(job["error"], title="[red]Error[/red]", expand=False))


def print_jobs_table(jobs: list[dict[str, Any]]) -> None:
    """Print a rich table of jobs."""
    table = Table(title="Jobs", show_lines=False, header_style="bold cyan")
    table.add_column("ID",        style="dim",    width=10)
    table.add_column("Type",                      min_width=20)
    table.add_column("Status",                    width=10)
    table.add_column("Progress",                  width=8)
    table.add_column("Created",                   width=20)
    table.add_column("Message",   no_wrap=False,  min_width=20)

    status_colors = {
        "QUEUED": "yellow", "RUNNING": "blue",
        "COMPLETED": "green", "FAILED": "red", "CANCELLED": "dim",
    }
    for j in jobs:
        status = j["status"]
        color  = status_colors.get(status, "white")
        pct    = f"{int((j.get('progress') or 0) * 100)}%"
        table.add_row(
            j["id"][:8],
            j["job_type"],
            f"[{color}]{status}[/{color}]",
            pct,
            j["created_at"][:19].replace("T", " "),
            j.get("progress_message") or "",
        )
    console.print(table)


def abort_with_error(msg: str, code: int = 1) -> None:
    err_console.print(f"[bold red]Error:[/bold red] {msg}")
    raise typer.Exit(code)


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _fmt_size(nbytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024:
            return f"{nbytes:.0f} {unit}"
        nbytes //= 1024
    return f"{nbytes:.0f} TB"
