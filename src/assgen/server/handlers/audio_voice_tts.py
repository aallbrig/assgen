"""audio.voice.tts — expressive TTS via Bark (suno/bark).

Bark generates highly natural speech including non-verbal sounds like
laughter, sighs, and hesitations — ideal for game NPC voices.

  pip install transformers accelerate scipy

Voice presets: v2/en_speaker_0 through v2/en_speaker_9
               v2/zh_speaker_*, v2/de_speaker_*, etc.
See: https://suno-ai.notion.site/8b8e8749ed514b0cbf3f699013548683
"""

try:
    from transformers import AutoProcessor, BarkModel  # type: ignore[import]
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def _stub_silent_wav(params: dict, output_dir, progress_cb) -> dict:
    """Return a short silent WAV when Bark model is unavailable."""
    import struct, wave
    from pathlib import Path
    progress_cb(0.2, "Bark model not available — generating silent placeholder audio…")
    sample_rate = 24000
    duration_s = 2
    num_samples = sample_rate * duration_s
    out_path = Path(output_dir) / "speech.wav"
    with wave.open(str(out_path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack("<" + "h" * num_samples, *([0] * num_samples)))
    progress_cb(1.0, "Stub audio saved")
    return {
        "files": ["speech.wav"],
        "metadata": {
            "stub": True,
            "reason": "Bark model not available",
            "sample_rate": sample_rate,
            "duration_seconds": duration_s,
        },
    }


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Generate speech audio from text using Bark."""
    if not _AVAILABLE:
        return _stub_silent_wav(params, output_dir, progress_cb)

    try:
        return _run_real_tts(params, model_id, model_path, device, progress_cb, output_dir)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Bark TTS failed (%s) — using stub", exc)
        return _stub_silent_wav(params, output_dir, progress_cb)


def _run_real_tts(params, model_id, model_path, device, progress_cb, output_dir):
    import numpy as np
    import scipy.io.wavfile as wav
    from pathlib import Path

    text = params.get("text") or params.get("prompt")
    if not text:
        raise ValueError("'text' param is required")

    voice_preset = params.get("voice_preset", "v2/en_speaker_6")
    output_format = params.get("output_format", "wav")
    resolved_model = model_id or "suno/bark"

    progress_cb(0.05, f"Loading Bark model ({resolved_model})…")

    import torch
    dtype = torch.float16 if device != "cpu" else torch.float32

    processor = AutoProcessor.from_pretrained(resolved_model)
    model = BarkModel.from_pretrained(resolved_model, torch_dtype=dtype)
    model = model.to(device)

    progress_cb(0.4, "Generating speech…")

    inputs = processor(text, voice_preset=voice_preset)
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        audio_array = model.generate(**inputs)

    audio_array = audio_array.cpu().numpy().squeeze()
    sample_rate = model.generation_config.sample_rate

    progress_cb(0.85, "Writing audio file…")

    out_path = Path(output_dir) / f"speech.{output_format}"
    if output_format == "wav":
        # Normalise to int16
        audio_int16 = (audio_array / np.max(np.abs(audio_array) + 1e-8) * 32767).astype(np.int16)
        wav.write(str(out_path), sample_rate, audio_int16)
    else:
        # Save raw float32 WAV, let caller convert
        wav.write(str(out_path), sample_rate, audio_array.astype(np.float32))

    return {
        "files": [str(out_path)],
        "metadata": {
            "model": resolved_model,
            "voice_preset": voice_preset,
            "sample_rate": sample_rate,
            "duration_seconds": round(len(audio_array) / sample_rate, 2),
            "text_length": len(text),
        },
    }
