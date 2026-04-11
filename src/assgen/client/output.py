"""Shared CLI utilities: wait-with-progress, job result rendering, file download."""
from __future__ import annotations

import json
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
    """Poll (or stream via SSE) the server until the job reaches a terminal state.

    Tries the SSE endpoint first for real-time updates.  Falls back to polling
    on ``GET /jobs/{id}`` if the stream fails (e.g. network proxy, older server).

    When ``--json`` mode is active, all Rich output is suppressed; the function
    waits silently and returns the completed job dict.
    """
    from assgen.client.context import is_json_mode, is_yaml_mode

    cfg = load_client_config()
    poll = float(cfg.get("poll_interval", 2.0))
    deadline = time.monotonic() + (timeout or float(cfg.get("default_timeout", 300)))

    def _wait_silent() -> dict[str, Any]:
        """Polling loop with no Rich output — used in --json mode."""
        try:
            remaining = max(1.0, deadline - time.monotonic())
            for event in client.stream_job_events(job_id, remaining_timeout=remaining):
                if event.get("status") in JobStatus.TERMINAL:
                    return client.get_job(job_id)
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"Timed out waiting for job {job_id}")
            return client.get_job(job_id)
        except (APIError, Exception):
            pass

        while time.monotonic() < deadline:
            try:
                job = client.get_job(job_id)
            except APIError as e:
                raise APIError(str(e)) from e
            if job["status"] in JobStatus.TERMINAL:
                return job
            time.sleep(poll)

        raise TimeoutError(f"Timed out waiting for job {job_id}")

    if is_json_mode() or is_yaml_mode():
        return _wait_silent()

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

        # ---- Try SSE streaming (real-time progress) ----
        try:
            remaining = max(1.0, deadline - time.monotonic())
            for event in client.stream_job_events(job_id, remaining_timeout=remaining):
                pct = int((event.get("progress") or 0) * 100)
                msg = event.get("message") or event.get("status", "").lower()
                progress.update(task, completed=pct, description=msg)

                if event.get("status") in JobStatus.TERMINAL:
                    progress.update(task, completed=100)
                    return client.get_job(job_id)

                if time.monotonic() >= deadline:
                    raise TimeoutError(f"Timed out waiting for job {job_id} after {timeout}s")

            # Stream ended without a terminal event — fetch final state
            return client.get_job(job_id)

        except (APIError, Exception):
            # SSE unavailable or failed — fall back to polling
            pass

        # ---- Polling fallback ----
        while time.monotonic() < deadline:
            try:
                job = client.get_job(job_id)
            except APIError as e:
                err_console.print(f"[red]error polling job: {e}[/red]")
                raise typer.Exit(1) from e

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

    # Warn when the result came from a stub handler (no real inference)
    output = job.get("output") or {}
    if isinstance(output, dict) and output.get("stub"):
        console.print()
        console.print("  [bold yellow]stub result[/bold yellow] [yellow]— ML dependencies not installed on server.[/yellow]")
        console.print("  [dim]Install inference deps: pip install \"assgen[inference]\"[/dim]")
        console.print("  [dim]Check server capabilities: assgen server status[/dim]")

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

    param_pairs = _user_param_pairs(job.get("params") or {})
    if param_pairs:
        console.print()
        max_klen = max(len(k) for k, _ in param_pairs)
        for i, (k, v) in enumerate(param_pairs):
            label = "params  " if i == 0 else "        "
            console.print(f"{label} [dim]{k:<{max_klen}}[/dim]  {v}")

    output = job.get("output")
    if output and isinstance(output, dict):
        files = output.get("files", [])
        if files:
            console.print()
            for fname in files:
                console.print(f"  {fname}")
            console.print(f"  [dim]assgen jobs download {job['id'][:8]}[/dim]")
        if output.get("stub"):
            console.print()
            console.print("  [bold yellow]⚠  NOT IMPLEMENTED[/bold yellow] [yellow]— stub output returned.[/yellow]")
            console.print("  [yellow]This job type has no real handler installed yet.[/yellow]")
            console.print("  [dim]Install the required model/library or check docs: https://aallbrig.github.io/assgen/[/dim]")

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


# ---------------------------------------------------------------------------
# JSON output helpers
# ---------------------------------------------------------------------------

def job_to_dict(job: dict[str, Any], saved_files: list[Path] | None = None) -> dict[str, Any]:
    """Serialise a job + saved file list to a plain dict suitable for JSON output."""
    result: dict[str, Any] = {
        "job_id": job["id"],
        "status": job["status"],
        "job_type": job["job_type"],
    }
    if job.get("model_id"):
        result["model_id"] = job["model_id"]
    dur = _duration_seconds(job)
    if dur is not None:
        result["duration_s"] = dur
    user_params = _user_params(job.get("params") or {})
    if user_params:
        result["params"] = user_params
    if saved_files:
        result["output_files"] = [str(f) for f in saved_files]
    elif job.get("output") and isinstance(job["output"], dict):
        files = job["output"].get("files", [])
        if files:
            result["output_files"] = files
    if job.get("error"):
        result["error"] = job["error"]
    output = job.get("output")
    if isinstance(output, dict) and output.get("stub"):
        result["stub"] = True
    return result


def print_job_json(job: dict[str, Any], saved_files: list[Path] | None = None) -> None:
    """Emit a single job result as a JSON line on stdout."""
    print(json.dumps(job_to_dict(job, saved_files)), flush=True)


def print_job_yaml(job: dict[str, Any], saved_files: list[Path] | None = None) -> None:
    """Emit a single job result as YAML on stdout."""
    import yaml
    print(yaml.dump(job_to_dict(job, saved_files), default_flow_style=False, sort_keys=False), end="", flush=True)


def abort_with_error(msg: str, code: int = 1) -> None:
    err_console.print(f"[red]error:[/red] {msg}")
    raise typer.Exit(code)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Params that are injected by the CLI/server and not meaningful to display.
_INTERNAL_PARAM_KEYS = frozenset({
    "upstream_files",   # raw file-path list from --from-job; shown via job chain
})


def _user_params(params: Any) -> dict[str, Any]:
    """Return a copy of params with internal/private keys removed."""
    if isinstance(params, str):
        try:
            params = json.loads(params)
        except Exception:
            return {}
    if not isinstance(params, dict):
        return {}
    return {
        k: v for k, v in params.items()
        if not k.startswith("_") and k not in _INTERNAL_PARAM_KEYS
        and v not in (None, "", [], {})
    }


def _fmt_param_value(v: Any) -> str:
    """Format a single param value for terminal display."""
    if isinstance(v, list):
        items = [str(x) for x in v[:5]]
        suffix = f"  [dim](+{len(v) - 5} more)[/dim]" if len(v) > 5 else ""
        return ", ".join(items) + suffix
    if isinstance(v, dict):
        keys = list(v.keys())[:4]
        suffix = " …" if len(v) > 4 else ""
        return "{" + ", ".join(f"{k}: …" for k in keys) + suffix + "}"
    s = str(v)
    return s[:117] + "[dim]…[/dim]" if len(s) > 120 else s


def _user_param_pairs(params: Any) -> list[tuple[str, str]]:
    """Return (key, formatted_value) pairs for user-visible params."""
    return [(k, _fmt_param_value(v)) for k, v in _user_params(params).items()]


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


def _duration_seconds(job: dict[str, Any]) -> int | None:
    if not (job.get("started_at") and job.get("completed_at")):
        return None
    from datetime import datetime
    try:
        started  = datetime.fromisoformat(job["started_at"].replace("Z", "+00:00"))
        finished = datetime.fromisoformat(job["completed_at"].replace("Z", "+00:00"))
        return int((finished - started).total_seconds())
    except Exception:
        return None


def _fmt_size(nbytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024:
            return f"{nbytes:.0f} {unit}"
        nbytes //= 1024
    return f"{nbytes:.0f} TB"
