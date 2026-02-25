"""Shared CLI utilities: wait-with-progress, job result rendering, etc."""
from __future__ import annotations

import time
from typing import Any

import typer
from rich.console import Console
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
# Rendering helpers
# ---------------------------------------------------------------------------

def print_job(job: dict[str, Any]) -> None:
    """Pretty-print a single job."""
    status_color = {
        "QUEUED":    "yellow",
        "RUNNING":   "blue",
        "COMPLETED": "green",
        "FAILED":    "red",
        "CANCELLED": "dim",
    }.get(job["status"], "white")

    console.print(f"\n[bold]Job ID:[/bold] {job['id']}")
    console.print(f"[bold]Type:[/bold]   {job['job_type']}")
    console.print(f"[bold]Status:[/bold] [{status_color}]{job['status']}[/{status_color}]")
    console.print(f"[bold]Progress:[/bold] {int((job.get('progress') or 0) * 100)}%"
                  + (f"  {job['progress_message']}" if job.get('progress_message') else ""))
    console.print(f"[bold]Created:[/bold] {job['created_at']}")
    if job.get("started_at"):
        console.print(f"[bold]Started:[/bold] {job['started_at']}")
    if job.get("completed_at"):
        console.print(f"[bold]Completed:[/bold] {job['completed_at']}")
    if job.get("error"):
        console.print(f"[bold red]Error:[/bold red]\n{job['error']}")
    if job.get("output"):
        console.print(f"[bold]Output:[/bold] {job['output']}")


def print_jobs_table(jobs: list[dict[str, Any]]) -> None:
    """Print a rich table of jobs."""
    table = Table(title="Jobs", show_lines=False, header_style="bold cyan")
    table.add_column("ID",        style="dim",    width=10)
    table.add_column("Type",                      min_width=20)
    table.add_column("Status",                    width=10)
    table.add_column("Progress",                  width=8)
    table.add_column("Created",                   width=22)
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
