"""assgen jobs — job lifecycle management.

  assgen jobs list     [--status QUEUED|RUNNING|COMPLETED|FAILED|CANCELLED] [--limit N]
  assgen jobs status   <job-id>
  assgen jobs wait     <job-id> [--timeout N]
  assgen jobs cancel   <job-id>
  assgen jobs download <job-id> [--output DIR]
  assgen jobs clean    [--status COMPLETED|FAILED|CANCELLED] [--days N]
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from assgen.client.api import APIError, get_client
from assgen.client.commands.submit import submit_job
from assgen.client.output import _user_params
from assgen.client.output import (
    abort_with_error,
    console,
    download_job_output,
    print_job,
    print_job_summary,
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

    from assgen.client.context import is_json_mode, is_yaml_mode
    if is_json_mode():
        import json
        items = [
            {"job_id": j["id"], "status": j["status"], "job_type": j["job_type"],
             "created_at": j.get("created_at")}
            for j in jobs
        ]
        print(json.dumps({"jobs": items}), flush=True)
        return
    if is_yaml_mode():
        import yaml
        items = [
            {"job_id": j["id"], "status": j["status"], "job_type": j["job_type"],
             "created_at": j.get("created_at")}
            for j in jobs
        ]
        print(yaml.dump({"jobs": items}, default_flow_style=False, sort_keys=False), end="", flush=True)
        return

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

    from assgen.client.context import is_json_mode, is_yaml_mode
    if is_yaml_mode():
        from assgen.client.output import print_job_yaml
        print_job_yaml(job)
    elif is_json_mode():
        from assgen.client.output import print_job_json
        print_job_json(job)
    else:
        print_job(job)


@app.command("wait")
def jobs_wait(
    job_id: str = typer.Argument(..., help="Job ID to wait for"),
    timeout: Optional[float] = typer.Option(None, "--timeout", "-t", help="Max wait seconds"),
) -> None:
    """Wait for a job to reach a terminal state, showing a live progress bar."""
    with get_client() as client:
        try:
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


@app.command("download")
def jobs_download(
    job_id: str = typer.Argument(..., help="Job ID to download files from"),
    output: Optional[str] = typer.Option(
        None, "--output", "-o",
        help="Directory to save downloaded files (default: current directory)",
    ),
) -> None:
    """Download the output files produced by a completed job."""
    dest_dir = Path(output) if output else None
    with get_client() as client:
        try:
            job = client.get_job(job_id)
        except APIError as e:
            abort_with_error(str(e))

    if job["status"] != "COMPLETED":
        abort_with_error(
            f"Job {job_id[:8]} is {job['status']}, not COMPLETED. "
            "Use `assgen jobs wait <id>` first."
        )

    with get_client() as client:
        saved = download_job_output(client, job, dest_dir=dest_dir)

    if saved:
        print_job_summary(job, saved_files=saved)
    else:
        console.print(f"[yellow]No output files found for job {job_id[:8]}.[/yellow]")


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


@app.command("rerun")
def jobs_rerun(
    job_id: str = typer.Argument(..., help="Job ID or prefix to re-submit"),
    wait: Optional[bool] = typer.Option(
        None, "--wait/--no-wait",
        help="Wait for the new job to complete (overrides client default)",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run",
        help="Print what would be re-submitted without actually enqueuing",
    ),
) -> None:
    """Re-submit a previous job with the same type and parameters.

    Fetches the original job's job_type and user-supplied params, then
    enqueues a fresh job.  Internal/pipeline params (upstream_files, _quality,
    upstream_job_id, context_map) are stripped — use --from-job / --quality
    on the new run if you need them again.

    Examples:
        assgen jobs rerun a1b2c3d4
        assgen jobs rerun a1b2c3d4 --wait
        assgen jobs rerun a1b2c3d4 --dry-run
    """
    with get_client() as client:
        try:
            original = client.get_job(job_id)
        except APIError as e:
            abort_with_error(str(e))

    job_type: str = original.get("job_type", "")
    if not job_type:
        abort_with_error(f"Job {job_id[:8]} has no job_type — cannot rerun.")

    # Strip internal/pipeline params; keep only user-supplied values
    raw_params: dict = original.get("params") or {}
    rerun_params = _user_params(raw_params)
    # Also strip chaining keys that don't survive re-submission
    for key in ("upstream_job_id", "context_map"):
        rerun_params.pop(key, None)

    if dry_run:
        import json
        console.print("[bold]Would re-submit:[/bold]")
        console.print(f"  job_type  [cyan]{job_type}[/cyan]")
        for k, v in rerun_params.items():
            v_str = json.dumps(v) if not isinstance(v, str) else v
            console.print(f"  {k:<14}{v_str}")
        return

    submit_job(job_type=job_type, params=rerun_params, wait=wait)


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
