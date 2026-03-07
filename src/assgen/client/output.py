"""Shared CLI utilities: wait-with-progress, job result rendering, file download."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from assgen.client.api import APIClient, APIError
from assgen.config import load_client_config
from assgen.db import JobStatus

console = Console(highlight=False)
err_console = Console(stderr=True, highlight=False)


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
        TextColumn("{task.description}"),
        BarColumn(bar_width=30),
        TextColumn("{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task(f"job {job_id[:8]}…", total=100)

        while time.monotonic() < deadline:
            try:
                job = client.get_job(job_id)
            except APIError as e:
                err_console.print(f"[red]error polling job: {e}[/red]")
                raise typer.Exit(1)

            pct = int((job.get("progress") or 0) * 100)
            msg = job.get("progress_message") or job["status"].lower()
            progress.update(task, completed=pct, description=msg)

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
        if dest.exists():
            stem, suffix, counter = dest.stem, dest.suffix, 1
            while dest.exists():
                dest = save_dir / f"{stem}_{counter}{suffix}"
                counter += 1
        try:
            data = client.download_job_file(job_id, filename)
            dest.write_bytes(data)
            saved.append(dest)
        except APIError as e:
            err_console.print(f"[yellow]warn: could not download {filename}: {e}[/yellow]")

    return saved


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

def print_job_summary(
    job: dict[str, Any],
    saved_files: list[Path] | None = None,
) -> None:
    """Render a concise completion summary after --wait."""
    status = job["status"]
    short_id = job["id"][:8]

    duration_str = _duration(job)

    console.print()
    if status == "COMPLETED":
        line = f"[green]✓[/green] job [bold]{short_id}[/bold] completed"
        if duration_str:
            line += f" [dim]({duration_str})[/dim]"
        console.print(line)
    elif status == "FAILED":
        console.print(f"[red]✗[/red] job [bold]{short_id}[/bold] failed")
    else:
        console.print(f"[yellow]·[/yellow] job [bold]{short_id}[/bold] {status.lower()}")

    console.print(f"  type  {job['job_type']}")
    if job.get("model_id"):
        console.print(f"  model {job['model_id']}")

    if saved_files:
        console.print()
        for f in saved_files:
            size_str = _fmt_size(f.stat().st_size) if f.exists() else ""
            console.print(f"  [green]→[/green] {f}  [dim]{size_str}[/dim]")
    elif status == "COMPLETED":
        output = job.get("output") or {}
        files = output.get("files", []) if isinstance(output, dict) else []
        if files:
            console.print()
            for fname in files:
                console.print(f"  {fname}  [dim](server-side)[/dim]")
            console.print(f"  [dim]assgen jobs download {short_id}[/dim]")

    if job.get("error"):
        console.print()
        _print_error_block(job["error"])

    console.print()


def print_job(job: dict[str, Any]) -> None:
    """Pretty-print a single job (used by assgen jobs status)."""
    status = job["status"]
    status_color = {
        "QUEUED": "yellow", "RUNNING": "blue", "COMPLETED": "green",
        "FAILED": "red", "CANCELLED": "dim",
    }.get(status, "white")

    console.print()
    console.print(f"job      [bold]{job['id'][:8]}[/bold]  [dim]{job['id']}[/dim]")
    console.print(f"type     {job['job_type']}")
    console.print(f"status   [{status_color}]{status}[/{status_color}]")
    pct = int((job.get("progress") or 0) * 100)
    msg = job.get("progress_message") or ""
    console.print(f"progress {pct}%" + (f"  [dim]{msg}[/dim]" if msg else ""))
    console.print(f"created  [dim]{job['created_at'][:19].replace('T', ' ')}[/dim]")
    if job.get("started_at"):
        console.print(f"started  [dim]{job['started_at'][:19].replace('T', ' ')}[/dim]")
    if job.get("completed_at"):
        dur = _duration(job)
        console.print(f"done     [dim]{job['completed_at'][:19].replace('T', ' ')}[/dim]"
                      + (f"  [dim]({dur})[/dim]" if dur else ""))

    output = job.get("output")
    if output and isinstance(output, dict):
        files = output.get("files", [])
        if files:
            console.print()
            for fname in files:
                console.print(f"  {fname}")
            console.print(f"  [dim]assgen jobs download {job['id'][:8]}[/dim]")
        if output.get("stub"):
            console.print(f"  [dim yellow]⚠  {output.get('note', 'stub result')}[/dim yellow]")

    if job.get("error"):
        console.print()
        _print_error_block(job["error"])


def print_jobs_table(jobs: list[dict[str, Any]]) -> None:
    """Print a plain-text list of jobs — no box-drawing characters."""
    status_colors = {
        "QUEUED": "yellow", "RUNNING": "blue",
        "COMPLETED": "green", "FAILED": "red", "CANCELLED": "dim",
    }
    # Header
    console.print(f"\n[dim]{'ID':<10}  {'TYPE':<30}  {'STATUS':<12}  {'CREATED':<19}  MSG[/dim]")
    console.print(f"[dim]{'─' * 10}  {'─' * 30}  {'─' * 12}  {'─' * 19}  {'─' * 20}[/dim]")
    for j in jobs:
        status = j["status"]
        color  = status_colors.get(status, "white")
        created = j["created_at"][:19].replace("T", " ")
        msg = j.get("progress_message") or ""
        console.print(
            f"{j['id'][:8]:<10}  {j['job_type']:<30}  "
            f"[{color}]{status:<12}[/{color}]  "
            f"[dim]{created}[/dim]  {msg}"
        )
    console.print()


def abort_with_error(msg: str, code: int = 1) -> None:
    err_console.print(f"[red]error:[/red] {msg}")
    raise typer.Exit(code)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _print_error_block(error: str) -> None:
    """Print a plain error block — no box, just indented red lines."""
    err_console.print("[red]error[/red]")
    for line in error.splitlines():
        err_console.print(f"  [dim]{line}[/dim]")


def _duration(job: dict[str, Any]) -> str:
    if not (job.get("started_at") and job.get("completed_at")):
        return ""
    from datetime import datetime
    try:
        started  = datetime.fromisoformat(job["started_at"].replace("Z", "+00:00"))
        finished = datetime.fromisoformat(job["completed_at"].replace("Z", "+00:00"))
        secs = int((finished - started).total_seconds())
        return f"{secs // 60}m {secs % 60}s" if secs >= 60 else f"{secs}s"
    except Exception:
        return ""


def _fmt_size(nbytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024:
            return f"{nbytes:.0f} {unit}"
        nbytes //= 1024
    return f"{nbytes:.0f} TB"


# ---------------------------------------------------------------------------
# Progress / wait helper
# ---------------------------------------------------------------------------
