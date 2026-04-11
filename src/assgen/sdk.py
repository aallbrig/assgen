"""
assgen.sdk — public Python API for running assgen generation without the server.

Intended for HuggingFace Spaces, notebooks, and any programmatic consumer that
wants inference without the client-server HTTP stack.

Example::

    from assgen.sdk import run
    result = run("audio.sfx.generate", {"prompt": "sword clash", "duration": 2.0})
    print(result["files"])   # ['/tmp/abc123/sfx.wav']
"""
from __future__ import annotations

import importlib
import tempfile
from pathlib import Path
from typing import Any


def run(
    job_type: str,
    params: dict[str, Any],
    device: str = "auto",
    output_dir: Path | str | None = None,
    model_id: str | None = None,
) -> dict[str, Any]:
    """Run any assgen generation task as a pure Python call.

    No server process, no SQLite, no HTTP. Loads models on demand via HuggingFace Hub.

    Parameters
    ----------
    job_type:
        Dot-separated task identifier, e.g. ``"audio.sfx.generate"``,
        ``"visual.texture.generate"``, ``"narrative.dialogue.npc"``.
        Must match a key in ``catalog.yaml`` and a handler module in
        ``assgen.server.handlers``.
    params:
        Task-specific parameter dict. Keys match what the CLI passes internally.
        See the handler module's docstring for the full parameter spec.
    device:
        ``"auto"`` (default) resolves to ``"cuda"`` if a GPU is available, else ``"cpu"``.
        Pass ``"cuda"`` or ``"cpu"`` to override.
    output_dir:
        Directory to write output files into.  A temporary directory is created if not
        provided.  The directory persists after the call — the caller is responsible for
        cleanup (or use ``tempfile.TemporaryDirectory`` as a context manager).
    model_id:
        Override the catalog-default model ID. ``None`` = use catalog default.

    Returns
    -------
    dict
        ``"files"``: list of absolute path strings for every output file written.
        ``"metadata"``: handler-specific metadata dict.
        Additional keys may be present depending on the handler.

    Raises
    ------
    NotImplementedError
        If no handler module exists for *job_type*.
    RuntimeError
        If the handler raises (e.g. missing inference dependency).
    """
    # Resolve device
    if device == "auto":
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            device = "cpu"

    # Prepare output directory
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp())
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    # Resolve model_id from catalog if not overridden
    if model_id is None:
        try:
            from assgen.catalog import get_model_for_job
            entry = get_model_for_job(job_type) or {}
            model_id = entry.get("model_id")
        except Exception:
            model_id = None

    # Dispatch to handler
    handler = _load_handler(job_type)
    result = handler(
        job_type=job_type,
        params=params,
        model_id=model_id,
        model_path=None,  # handlers download from HF Hub cache themselves
        device=device,
        progress_cb=lambda p, msg: None,  # no-op; Spaces use gr.Progress instead
        output_dir=output_dir,
    )

    # Normalise relative filenames to absolute paths
    result["files"] = [
        str((output_dir / f).resolve()) if not Path(str(f)).is_absolute() else str(f)
        for f in result.get("files", [])
    ]
    return result


def _load_handler(job_type: str):
    """Import and return the run() callable for *job_type*.

    Unlike the server's ``_load_handler``, this raises ``NotImplementedError``
    rather than silently returning a stub — callers should know if a handler is missing.
    """
    module_name = "assgen.server.handlers." + job_type.replace(".", "_")
    try:
        mod = importlib.import_module(module_name)
        return mod.run  # type: ignore[attr-defined]
    except ModuleNotFoundError:
        raise NotImplementedError(
            f"No handler found for job_type '{job_type}'. "
            f"Expected module: {module_name}"
        ) from None
