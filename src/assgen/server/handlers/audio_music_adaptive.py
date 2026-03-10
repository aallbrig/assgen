"""Handler for audio.music.adaptive — adaptive/stinger MusicGen generation.

Thin wrapper around :mod:`audio_music_loop` (MusicGen Stereo) — adaptive
music uses the same crossfade loop machinery but is prompted and sized for
short stingers and transition layers.

Requires the ``audiocraft`` package (Meta):
    pip install audiocraft
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from assgen.server.handlers.audio_music_loop import run as _loop_run

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
    """Generate adaptive/stinger music — delegates to the MusicGen loop handler."""
    params = dict(params)
    # Stingers are short; default 8s unless caller specifies otherwise
    params.setdefault("duration", 8.0)
    result = _loop_run(
        job_type=job_type,
        params=params,
        model_id=model_id,
        model_path=model_path,
        device=device,
        progress_cb=progress_cb,
        output_dir=output_dir,
    )
    # Rename loop.wav → stinger.wav for clarity
    renamed: list[str] = []
    for name in result.get("files", []):
        if name == "loop.wav":
            src = output_dir / "loop.wav"
            if src.exists():
                src.rename(output_dir / "stinger.wav")
            renamed.append("stinger.wav")
        else:
            renamed.append(name)
    result["files"] = renamed
    return result
