"""Shared helper: submit_job.

All game-asset commands call submit_job(job_type, params, ...)
which enqueues the job and either waits or prints the job ID.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import typer

from assgen.client.api import APIError, get_client
from assgen.client.output import (
    abort_with_error,
    console,
    download_job_output,
    print_job_summary,
    wait_for_job,
)
from assgen.config import load_client_config


def submit_job(
    job_type: str,
    params: dict[str, Any],
    wait: Optional[bool] = None,
    priority: int = 0,
    tags: list[str] | None = None,
    model_id: str | None = None,
    output_path: str | None = None,
) -> None:
    """Enqueue a job and either wait for completion or print the job ID."""
    cfg = load_client_config()
    should_wait = wait if wait is not None else cfg.get("default_wait", False)

    with get_client() as client:
        try:
            job = client.enqueue_job(
                job_type, params,
                priority=priority, tags=tags or [],
                model_id=model_id,
            )
        except APIError as e:
            abort_with_error(str(e))

    job_id = job["id"]

    if not should_wait:
        console.print(f"[green]✓ Job enqueued[/green]  [dim]{job_id[:8]}[/dim]  [italic]{job_type}[/italic]")
        console.print(f"[dim]  Track:    assgen jobs status {job_id[:8]}[/dim]")
        console.print(f"[dim]  Wait:     assgen jobs wait {job_id[:8]}[/dim]")
        console.print(f"[dim]  Download: assgen jobs download {job_id[:8]}[/dim]")
        return

    # Wait with a progress bar
    with get_client() as client:
        try:
            completed = wait_for_job(client, job_id)
        except TimeoutError as e:
            abort_with_error(str(e))
        except APIError as e:
            abort_with_error(str(e))

    # Determine output destination
    dest_dir: Path | None = None
    if output_path:
        dest_dir = Path(output_path)
    elif cfg.get("output_dir"):
        dest_dir = Path(cfg["output_dir"])
    # else: download to cwd

    if completed["status"] == "COMPLETED":
        with get_client() as client:
            saved = download_job_output(client, completed, dest_dir=dest_dir)
        print_job_summary(completed, saved_files=saved)
        raise typer.Exit(0)
    else:
        print_job_summary(completed, saved_files=[])
        raise typer.Exit(1)
