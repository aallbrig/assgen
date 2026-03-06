"""assgen jobs — job lifecycle management.

  assgen jobs list     [--status QUEUED|RUNNING|COMPLETED|FAILED|CANCELLED] [--limit N]
  assgen jobs status   <job-id>
  assgen jobs wait     <job-id> [--timeout N]
  assgen jobs cancel   <job-id>
  assgen jobs clean    [--status COMPLETED|FAILED|CANCELLED] [--days N]
"""
from __future__ import annotations

from typing import Optional

import typer

from assgen.client.api import APIError, get_client
from assgen.client.output import (
    abort_with_error,
    console,
    print_job,
    print_jobs_table,
    wait_for_job,
)
from assgen.db import JobStatus

app = typer.Typer(help="Manage asset generation jobs.", no_args_is_help=True)


@app.command("list")
def jobs_list(
    status: Optional[list[str]] = typer.Option(
        None, "--status", "-s",
        help="Filter by status (repeatable): QUEUED RUNNING COMPLETED FAILED CANCELLED",
    ),
    limit: int = typer.Option(50, "--limit", "-n", help="Max number of jobs to show"),
) -> None:
    """List enqueued and recent jobs."""
    with get_client() as client:
        try:
            jobs = client.list_jobs(statuses=status, limit=limit)
        except APIError as e:
            abort_with_error(str(e))
    if not jobs:
        console.print("[dim]No jobs found.[/dim]")
        return
    print_jobs_table(jobs)


@app.command("status")
def jobs_status(job_id: str = typer.Argument(..., help="Job ID or prefix")) -> None:
    """Show the status of a single job."""
    with get_client() as client:
        try:
            job = client.get_job(job_id)
        except APIError as e:
            abort_with_error(str(e))
    print_job(job)


@app.command("wait")
def jobs_wait(
    job_id: str = typer.Argument(..., help="Job ID to wait for"),
    timeout: Optional[float] = typer.Option(None, "--timeout", "-t", help="Max wait seconds"),
) -> None:
    """Wait for a job to reach a terminal state, showing a live progress bar."""
    with get_client() as client:
        try:
            # Fast-path: already terminal?
            job = client.get_job(job_id)
            if job["status"] in JobStatus.TERMINAL:
                print_job(job)
                raise typer.Exit(0 if job["status"] == JobStatus.COMPLETED else 1)

            job = wait_for_job(client, job_id, timeout=timeout)
        except TimeoutError as e:
            abort_with_error(str(e))
        except APIError as e:
            abort_with_error(str(e))

    print_job(job)
    raise typer.Exit(0 if job["status"] == JobStatus.COMPLETED else 1)


@app.command("cancel")
def jobs_cancel(
    job_id: str = typer.Argument(..., help="Job ID to cancel"),
    confirm: bool = typer.Option(True, "--confirm/--no-confirm", help="Ask for confirmation"),
) -> None:
    """Cancel a queued or running job."""
    if confirm:
        typer.confirm(f"Cancel job {job_id[:8]}?", abort=True)
    with get_client() as client:
        try:
            client.cancel_job(job_id)
        except APIError as e:
            abort_with_error(str(e))
    console.print(f"[yellow]Cancelled[/yellow] job {job_id[:8]}")


@app.command("clean")
def jobs_clean(
    statuses: Optional[list[str]] = typer.Option(
        ["COMPLETED", "FAILED", "CANCELLED"],
        "--status", "-s",
        help="Which statuses to delete",
    ),
    days: Optional[int] = typer.Option(
        None, "--days", "-d",
        help="Only delete jobs older than N days",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be deleted"),
) -> None:
    """Remove old terminal jobs from the local database.

    Note: this operates directly on the local SQLite DB (config dir),
    not via the server API.
    """
    from assgen.db import init_db

    conn = init_db()
    clauses = [f"status IN ({','.join('?' * len(statuses))})"]
    params: list = list(statuses or [])

    if days is not None:
        clauses.append("created_at < datetime('now', ?)")
        params.append(f"-{days} days")

    where = " AND ".join(clauses)
    rows = conn.execute(f"SELECT id, job_type, status FROM jobs WHERE {where}", params).fetchall()

    if not rows:
        console.print("[dim]No matching jobs found.[/dim]")
        return

    console.print(f"{'Would remove' if dry_run else 'Removing'} {len(rows)} job(s):")
    for r in rows:
        console.print(f"  [dim]{r['id'][:8]}[/dim]  {r['job_type']}  [{r['status']}]")

    if not dry_run:
        conn.execute(f"DELETE FROM jobs WHERE {where}", params)
        conn.commit()
        console.print(f"[green]Cleaned {len(rows)} job(s).[/green]")
