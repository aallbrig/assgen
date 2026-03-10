"""Handler for audio.ambient.generate — MusicGen ambient soundscape generation.

Thin wrapper around :mod:`audio_music_compose` — ambient generation uses the
same MusicGen model but with distinct default prompting conventions (long,
atmospheric, no melody, looping).

Requires the ``audiocraft`` package (Meta):
    pip install audiocraft
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from assgen.server.handlers.audio_music_compose import run as _compose_run

ProgressCallback = Callable[[float, str], None]


def run(
    job_type: str,
    params: dict[str, Any],
    model_id: str | None,
    model_path: str | None,
    device: str,
    progress_cb: ProgressCallback,
    output_dir: Path,
) -> dict[str, Any]:
    """Generate an ambient soundscape — delegates to the MusicGen compose handler."""
    # Default to a longer duration for ambient loops; callers can override
    params = dict(params)
    params.setdefault("duration", 60.0)
    # Nudge the prompt toward atmospheric/ambient if caller didn't already
    if params.get("prompt") and "ambient" not in params["prompt"].lower():
        params["prompt"] = params["prompt"] + ", atmospheric ambient, no melody, looping"
    result = _compose_run(
        job_type=job_type,
        params=params,
        model_id=model_id,
        model_path=model_path,
        device=device,
        progress_cb=progress_cb,
        output_dir=output_dir,
    )
    # Rename output files to reflect ambient naming convention
    renamed: list[str] = []
    for name in result.get("files", []):
        if name.startswith("track"):
            new_name = name.replace("track", "ambient", 1)
            src = output_dir / name
            if src.exists():
                src.rename(output_dir / new_name)
            renamed.append(new_name)
        else:
            renamed.append(name)
    result["files"] = renamed
    return result
