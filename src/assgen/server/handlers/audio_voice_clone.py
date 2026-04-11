"""audio.voice.clone — zero-shot voice cloning via XTTS-v2.

Generates speech from text in a cloned target voice using Coqui TTS XTTS-v2.

  pip install TTS torch soundfile

Params:
    prompt          (str):  text to speak
    speaker_wav     (str):  path to reference audio clip (6–30 s WAV/MP3)
    language        (str):  BCP-47 language code, e.g. "en", "fr", "de" (default: en)
    speed           (float):speech rate multiplier (default: 1.0)
    output          (str):  output filename (default: voice_clone.wav)
"""
from __future__ import annotations

try:
    from TTS.api import TTS  # noqa: F401
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Clone a voice and synthesise speech with XTTS-v2."""
    if not _AVAILABLE:
        raise RuntimeError(
            "Coqui TTS is required. Run: pip install TTS torch soundfile"
        )

    from pathlib import Path

    from TTS.api import TTS

    prompt = params.get("prompt", "")
    if not prompt:
        raise ValueError("'prompt' (text to speak) is required")

    speaker_wav = params.get("speaker_wav", "")
    if not speaker_wav or not Path(speaker_wav).exists():
        raise ValueError(f"'speaker_wav' reference audio not found: {speaker_wav!r}")

    language = params.get("language", "en")
    speed = float(params.get("speed", 1.0))
    out_name = params.get("output") or "voice_clone.wav"
    out_path = Path(output_dir) / out_name

    progress_cb(0.05, "Loading XTTS-v2 model…")
    tts_model = model_path or "tts_models/multilingual/multi-dataset/xtts_v2"
    tts = TTS(model_name=tts_model, progress_bar=False).to(device)

    progress_cb(0.4, f"Synthesising speech ({language})…")
    tts.tts_to_file(
        text=prompt,
        speaker_wav=str(speaker_wav),
        language=language,
        speed=speed,
        file_path=str(out_path),
    )

    progress_cb(1.0, "Done")
    return {
        "files": [out_name],
        "metadata": {"language": language, "speed": speed, "chars": len(prompt)},
    }
