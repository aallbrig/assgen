"""Handler for audio.music.compose — MusicGen single-stem track generation.

Requires the ``audiocraft`` package (Meta):
    pip install audiocraft

Falls back to the stub handler if audiocraft is not installed.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

try:
    from audiocraft.models import MusicGen
    from audiocraft.data.audio import audio_write
    _AUDIOCRAFT_AVAILABLE = True
except ImportError:
    _AUDIOCRAFT_AVAILABLE = False


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
    """Generate a music track from a text prompt."""
    if not _AUDIOCRAFT_AVAILABLE:
        raise RuntimeError(
            "audiocraft is not installed.  "
            "Run: pip install audiocraft"
        )

    prompt: str = params.get("prompt") or params.get("description") or "game soundtrack"
    duration: float = float(params.get("duration", 30.0))
    variations: int = max(1, int(params.get("variations", 1)))

    progress_cb(0.25, "Loading MusicGen model…")
    load_from = model_path or model_id or "facebook/musicgen-large"
    model = MusicGen.get_pretrained(load_from)
    model.set_generation_params(duration=duration)

    progress_cb(0.40, f"Composing {variations} track(s) — this may take a minute…")
    prompts = [prompt] * variations
    wavs = model.generate(prompts)

    progress_cb(0.85, "Writing WAV files…")
    saved: list[str] = []
    for idx, wav in enumerate(wavs):
        stem = f"track_{idx:02d}" if variations > 1 else "track"
        out_path = output_dir / stem
        audio_write(
            str(out_path),
            wav[0].cpu(),
            model.sample_rate,
            strategy="loudness",
        )
        saved.append(out_path.with_suffix(".wav").name)

    progress_cb(1.0, "Music generation complete")
    return {
        "files": saved,
        "metadata": {
            "model_id": model_id or "facebook/musicgen-large",
            "prompt": prompt,
            "duration_seconds": duration,
            "variations": variations,
            "sample_rate": model.sample_rate,
        },
    }
