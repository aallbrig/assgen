"""Handler for audio.sfx.generate — text-to-SFX via AudioLDM2.

AudioLDM2 (cvssp/audioldm2) is trained on general audio / sound effects
and is the correct model for game SFX prompts.

Note: facebook/audiogen-medium (Meta AudioGen) was removed from
transformers 5.x and audiocraft no longer installs cleanly on
Python 3.13 + modern torchvision. AudioLDM2 is the replacement.

  pip install diffusers transformers accelerate scipy torch
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

try:
    from diffusers import AudioLDM2Pipeline  # type: ignore[import]
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


ProgressCallback = Callable[[float, str], None]

_SAMPLE_RATE = 16_000  # AudioLDM2 outputs at 16 kHz
_NEGATIVE_PROMPT = "Low quality, average quality, noise, hum."


def run(
    job_type: str,
    params: dict[str, Any],
    model_id: str | None,
    model_path: str | None,
    device: str,
    progress_cb: ProgressCallback,
    output_dir: Path,
) -> dict[str, Any]:
    """Generate WAV sound effects from a text prompt using AudioLDM2."""
    if not _AVAILABLE:
        raise RuntimeError(
            "diffusers is not installed. "
            "Run: pip install diffusers transformers accelerate"
        )

    import torch
    import scipy.io.wavfile

    prompt: str = params.get("prompt") or params.get("description") or "sound effect"
    duration: float = float(params.get("duration", 4.0))
    variations: int = max(1, int(params.get("variations", 1)))
    steps: int = int(params.get("num_inference_steps", 100))
    resolved_model = model_path or model_id or "cvssp/audioldm2"

    progress_cb(0.1, f"Loading AudioLDM2 ({resolved_model})…")
    dtype = torch.float16 if device != "cpu" else torch.float32
    pipe = AudioLDM2Pipeline.from_pretrained(resolved_model, torch_dtype=dtype)
    pipe.to(device)

    progress_cb(0.3, f"Generating {variations} SFX clip(s)…")
    output = pipe(
        prompt,
        negative_prompt=_NEGATIVE_PROMPT,
        num_inference_steps=steps,
        audio_length_in_s=duration,
        num_waveforms_per_prompt=variations,
    )

    progress_cb(0.85, "Writing WAV files…")
    saved: list[str] = []
    for idx, audio in enumerate(output.audios):
        stem = f"sfx_{idx:02d}" if variations > 1 else "sfx"
        filename = f"{stem}.wav"
        out_path = Path(output_dir) / filename
        scipy.io.wavfile.write(str(out_path), _SAMPLE_RATE, audio.squeeze().astype("float32"))
        saved.append(filename)

    progress_cb(1.0, "SFX generation complete")
    return {
        "files": saved,
        "metadata": {
            "model_id": resolved_model,
            "prompt": prompt,
            "duration_seconds": duration,
            "variations": variations,
            "sample_rate": _SAMPLE_RATE,
        },
    }
