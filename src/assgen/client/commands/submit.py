"""Shared helper: submit_job.

All game-asset commands call submit_job(job_type, params, ...)
which enqueues the job and either waits or prints the job ID.
"""
from __future__ import annotations

from typing import Any, Optional

import typer

from assgen.client.api import APIError, get_client
from assgen.client.output import (
    abort_with_error,
    console,
    print_job,
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
        console.print(f"[green]Job enqueued[/green]  id={job_id}  type={job_type}")
        console.print(f"[dim]Track with: assgen jobs status {job_id[:8]}[/dim]")
        console.print(f"[dim]Or wait  with: assgen jobs wait {job_id[:8]}[/dim]")
        return

    # Wait with a progress bar
    with get_client() as client:
        try:
            completed = wait_for_job(client, job_id)
        except TimeoutError as e:
            abort_with_error(str(e))
        except APIError as e:
            abort_with_error(str(e))

    print_job(completed)
    raise typer.Exit(0 if completed["status"] == "COMPLETED" else 1)
