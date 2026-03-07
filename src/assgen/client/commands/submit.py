"""Shared helper: submit_job.

All game-asset commands call submit_job(job_type, params, ...)
which enqueues the job and either waits or prints the job ID.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import typer

from assgen.client.api import APIError, get_client
from assgen.client.context import get_variants, is_json_mode
from assgen.client.output import (
    abort_with_error,
    console,
    download_job_output,
    job_to_dict,
    print_job_json,
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
    """Enqueue one (or N via ``--variants``) job(s) and wait or print job ID(s)."""
    cfg = load_client_config()
    should_wait = wait if wait is not None else cfg.get("default_wait", False)
    n_variants = get_variants()
    json_mode = is_json_mode()

    # --- Enqueue N jobs ---
    job_ids: list[str] = []
    with get_client() as client:
        for _ in range(n_variants):
            try:
                job = client.enqueue_job(
                    job_type, params,
                    priority=priority, tags=tags or [],
                    model_id=model_id,
                )
                job_ids.append(job["id"])
            except APIError as e:
                abort_with_error(str(e))

    if not should_wait:
        if json_mode:
            results = [
                {"job_id": jid, "status": "QUEUED", "job_type": job_type}
                for jid in job_ids
            ]
            out = results[0] if n_variants == 1 else {"jobs": results}
            print(json.dumps(out), flush=True)
        else:
            for jid in job_ids:
                console.print(
                    f"[green]✓ Job enqueued[/green]  [dim]{jid[:8]}[/dim]  [italic]{job_type}[/italic]"
                )
                console.print(f"[dim]  Track:    assgen jobs status {jid[:8]}[/dim]")
                console.print(f"[dim]  Wait:     assgen jobs wait {jid[:8]}[/dim]")
                console.print(f"[dim]  Download: assgen jobs download {jid[:8]}[/dim]")
        return

    # --- Wait for all N jobs ---
    dest_dir: Path | None = None
    if output_path:
        dest_dir = Path(output_path)
    elif cfg.get("output_dir"):
        dest_dir = Path(cfg["output_dir"])

    completed_results: list[tuple[dict[str, Any], list[Path]]] = []
    any_failed = False
    for jid in job_ids:
        with get_client() as client:
            try:
                completed = wait_for_job(client, jid)
            except TimeoutError as e:
                abort_with_error(str(e))
            except APIError as e:
                abort_with_error(str(e))

        saved: list[Path] = []
        if completed["status"] == "COMPLETED":
            with get_client() as client:
                saved = download_job_output(client, completed, dest_dir=dest_dir)
        else:
            any_failed = True
        completed_results.append((completed, saved))

    # --- Render output ---
    if json_mode:
        if n_variants == 1:
            job, saved = completed_results[0]
            print_job_json(job, saved)
        else:
            items = [job_to_dict(j, s) for j, s in completed_results]
            print(json.dumps({"jobs": items}), flush=True)
    else:
        for job, saved in completed_results:
            print_job_summary(job, saved_files=saved)

    raise typer.Exit(1 if any_failed else 0)
