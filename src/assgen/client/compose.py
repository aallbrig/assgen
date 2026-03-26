"""assgen.client.compose — sequential pipeline execution engine.

Executes multi-step asset pipelines where each step waits for the previous
to complete and receives its output files as `upstream_files`.

Usage::

    from assgen.client.compose import run_pipeline

    results = run_pipeline(
        steps=[
            {"id": "concept", "job_type": "visual.concept.generate",
             "params": {"prompt": "pig shopkeeper"}},
            {"id": "mesh",    "job_type": "visual.model.splat",
             "from_step": "concept"},
        ],
        global_params={"_quality": "standard"},
        on_step=lambda step_id, status, msg: print(f"[{step_id}] {status}: {msg}"),
    )
"""
from __future__ import annotations

from typing import Any, Callable

from assgen.client.api import APIError, get_client
from assgen.client.output import wait_for_job


StepResult = dict[str, Any]
OnStepCallback = Callable[[str, str, str], None]  # (step_id, status, message)


def _noop_cb(step_id: str, status: str, msg: str) -> None:
    pass


def run_pipeline(
    steps: list[dict[str, Any]],
    global_params: dict[str, Any] | None = None,
    on_step: OnStepCallback = _noop_cb,
    timeout_per_step: float = 3600.0,
) -> dict[str, StepResult]:
    """Execute a list of pipeline steps sequentially, chaining outputs into inputs.

    Each step dict supports:
        id          (str, required): unique step identifier
        job_type    (str, required): catalog job type
        params      (dict):         step-specific params (merged over global_params)
        from_step   (str|list):     step id(s) whose output files to pass as upstream_files

    Returns a dict mapping step_id → completed job dict.
    """
    global_params = global_params or {}
    completed: dict[str, StepResult] = {}

    for step in steps:
        step_id   = step["id"]
        job_type  = step["job_type"]
        step_params = {**global_params, **step.get("params", {})}

        # Resolve upstream files from named prior steps
        from_step = step.get("from_step")
        if from_step:
            sources = [from_step] if isinstance(from_step, str) else list(from_step)
            upstream: list[str] = []
            for src in sources:
                if src not in completed:
                    raise RuntimeError(
                        f"Pipeline step {step_id!r} depends on {src!r} "
                        f"which has not completed. Check step ordering."
                    )
                result = completed[src].get("output") or completed[src].get("result") or {}
                upstream.extend(result.get("files", []))
            if upstream:
                step_params["upstream_files"] = upstream

        on_step(step_id, "SUBMITTING", f"→ {job_type}")

        with get_client() as client:
            try:
                job = client.enqueue_job(job_type, step_params)
            except APIError as exc:
                raise RuntimeError(
                    f"Pipeline step {step_id!r} failed to enqueue: {exc}"
                ) from exc

        job_id = job["id"]
        on_step(step_id, "RUNNING", f"job {job_id[:8]}")

        with get_client() as client:
            try:
                finished = wait_for_job(client, job_id, timeout=timeout_per_step)
            except (TimeoutError, APIError) as exc:
                raise RuntimeError(
                    f"Pipeline step {step_id!r} (job {job_id[:8]}) failed: {exc}"
                ) from exc

        status = finished.get("status", "UNKNOWN")
        if status != "COMPLETED":
            raise RuntimeError(
                f"Pipeline step {step_id!r} finished with status {status!r}. "
                "Pipeline halted."
            )

        completed[step_id] = finished
        on_step(step_id, "DONE", f"✓ {job_type}")

    return completed
