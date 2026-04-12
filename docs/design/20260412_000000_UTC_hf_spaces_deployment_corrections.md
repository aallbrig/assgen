# HuggingFace Spaces — Deployment Corrections (supersedes earlier specs)

_Generated: 2026-04-12 00:00:00 UTC_
_Status: Tier 1 all RUNNING as of 2026-04-12_

This document records everything that broke during the first Tier 1 deployment and the exact fixes
applied. It **supersedes** conflicting guidance in the earlier spec documents. Read this first.

---

## Root Cause Summary

Three independent issues caused all 10 Tier 1 Spaces to fail after the first deployment:

| Issue | Spaces affected | Root cause |
|-------|----------------|------------|
| `HfFolder` removed from huggingface_hub | All 10 (Gradio import chain) | Gradio 4.44.0 `oauth.py` imports `HfFolder` which was removed in a recent huggingface_hub version pulled in by transformers |
| `audiocraft` git install fails | sfx.generate, music.compose | audiocraft git install has Python 3.13 / torchvision conflicts |
| `basicsr`/`realesrgan` install fails | texture.upscale | `basicsr` imports `torchvision.transforms.functional_tensor` removed in torchvision ≥ 0.16 |

---

## Correction 1: sdk_version must be 5.23.0, not 4.44.0

**Spec said:** `sdk_version: "4.44.0"` in all Space card README files.

**What happened:** Gradio 4.44.0's `oauth.py` imports `HfFolder` from `huggingface_hub`.
Recent `huggingface_hub` (pulled in by `transformers>=4.40`) removed `HfFolder`.
All 10 Spaces hit `ImportError: cannot import name 'HfFolder'` before the Gradio UI could start.

We also tried `python_version: "3.11"` to pin an older Python — this switched the runtime to
Python 3.11 (which has audioop), but the HfFolder error persisted since it is not Python-version-dependent.

**Fix:** Upgrade to Gradio 5.x. Gradio 5.23.0 uses the current huggingface_hub API and does not
import pydub at startup.

**All Space README files now use:**
```yaml
sdk: gradio
sdk_version: "5.23.0"
app_file: app.py
```

**Do NOT add `python_version`** — it caused a different Gradio 4.44.0 startup error and is not
needed with Gradio 5.x.

---

## Correction 2: Drop audiocraft entirely — use transformers pipeline

**Spec said:** `assgen.audio.sfx.generate`, `assgen.audio.music.compose`, `assgen.audio.music.loop`,
and `assgen.audio.ambient.generate` need:
```
audiocraft @ git+https://github.com/facebookresearch/audiocraft.git
```

**What happened:** The audiocraft git install fails during Docker build on HF Spaces (Python 3.13
environment, conflicting torch/torchvision constraints). `AUDIOCRAFT_SPACES` in `sync_spaces.py`
was the source of the broken requirements.

Additionally, `AudiogenForConditionalGeneration` is no longer exported at the top level of
transformers in the version installed by HF Spaces. Importing it by class name fails.

**Fix:** All four audio generation Spaces now use `transformers.pipeline("text-to-audio")` which:
1. Resolves the model class internally (version-stable)
2. Does not need audiocraft
3. Works with both AudioGen and MusicGen models

**`AUDIOCRAFT_SPACES` in `sync_spaces.py` is now an empty set.**

**Pattern used in all audio generation Spaces:**
```python
from transformers import pipeline
import scipy.io.wavfile, numpy as np, tempfile, torch

MODEL_ID = "facebook/audiogen-medium"   # or musicgen-medium, musicgen-stereo-large
FRAME_RATE = 50  # tokens/second for both AudioGen and MusicGen EnCodec

_pipe = None

def _load():
    global _pipe
    if _pipe is None:
        device = 0 if torch.cuda.is_available() else -1
        _pipe = pipeline("text-to-audio", model=MODEL_ID, device=device)
    return _pipe

@spaces.GPU
def generate(description: str, duration: float) -> str:
    result = _load()(description, forward_params={"max_new_tokens": int(duration * FRAME_RATE)})
    audio = np.array(result["audio"]).squeeze()
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    scipy.io.wavfile.write(tmp.name, result["sampling_rate"], audio.astype(np.float32))
    return tmp.name
```

For stereo models (musicgen-stereo-large), transpose the output before writing:
```python
audio = np.array(result["audio"]).squeeze().T  # (samples, 2) for stereo WAV
```

---

## Correction 3: texture.upscale uses diffusers, not basicsr/realesrgan

**Spec said:** `texture.upscale` requires `opencv-python-headless>=4.9`, `basicsr>=1.4.2`,
`realesrgan>=0.3.0`.

**What happened:** `basicsr` imports `torchvision.transforms.functional_tensor` which was removed
in torchvision ≥ 0.16. The pip install fails during Docker build. This was already a known issue
(moved to EXTRA_PIP to isolate the failure), but the underlying package is broken with current deps.

**Fix:** Rewrote `assgen.texture.upscale/app.py` to use `diffusers.StableDiffusionUpscalePipeline`
with `stabilityai/stable-diffusion-x4-upscaler`. `diffusers` is already in `assgen[spaces]`.
No extra pip packages needed for this Space.

The tradeoff: SD x4 upscaler takes a text style-hint and is slower than ESRGAN, but it is a real
AI upscaler that produces good results for texture work.

**`assgen.texture.upscale` no longer appears in EXTRA_PIP.**

---

## Correction 4: audio.voice.tts does NOT need Coqui TTS

**Spec said:** `assgen.audio.voice.tts` requires `TTS>=0.22` (Coqui TTS) in EXTRA_PIP.

**What happened:** The `audio_voice_tts.py` handler already uses `transformers.BarkModel`
(suno/bark) — not Coqui TTS. The `TTS>=0.22` in EXTRA_PIP was a mistake.
Coqui TTS is a large and partially abandoned package (~1.5 GB) that would cause the build to fail.

**Fix:** Removed `assgen.audio.voice.tts` from EXTRA_PIP. `transformers` (already in
`assgen[spaces]`) provides everything the handler needs.

**`assgen.audio.voice.clone` still needs `TTS>=0.22`** — that handler genuinely uses XTTS-v2.
It is a Tier 2 Space, not yet deployed.

---

## Correction 5: CI spaces-sync auth — use HF_TOKEN env var

**Spec said:**
```yaml
- name: Install HF CLI
  run: pip install "huggingface_hub[cli]>=0.23"
- name: Authenticate HF CLI
  env:
    HF_TOKEN: ${{ secrets.HF_TOKEN }}
  run: hf login --token "$HF_TOKEN"
```

**What happened:** The `hf` CLI restructured its auth commands — `hf login` was moved to
`hf auth login`. The step failed with `No such command 'login'`.

**Fix:** Drop the CLI entirely. `HfApi()` reads `HF_TOKEN` from the environment automatically.

```yaml
- name: Install huggingface_hub
  run: pip install "huggingface_hub>=0.23"
- name: Sync all Spaces
  env:
    HF_TOKEN: ${{ secrets.HF_TOKEN }}
    VERSION: ${{ github.ref_name }}
  run: python scripts/sync_spaces.py --version "$VERSION"
```

---

## Correction 6: docs.yml must NOT trigger on tags

**Spec said:** docs workflow triggered on `branches: [main]` and `tags: ["v*"]`.

**What happened:** GitHub Pages environment protection rules block deployments from tag refs.
Every release tag push failed the docs job with "Tag 'vX.Y.Z' is not allowed to deploy to
github-pages due to environment protection rules."

**Fix:** Remove `tags: ["v*"]` from `docs.yml`. Docs deploy only on `push: branches: [main]`.
The release workflow's zip-and-attach step covers offline docs on tagged releases.

---

## Correction 7: Chocolatey nuspec schema

**Spec said:** nuspec xmlns = `http://schemas.chocolatey.org/2010/07/nuspec`

**What happened:** Chocolatey 2.7.1 rejected the schema as incompatible — `choco pack`
silently produced no `.nupkg`, causing the subsequent push to fail with file-not-found.

**Fix:** Update xmlns to `http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd`

**Also note:** First-time Chocolatey Community Repository packages require manual moderation
review before the API key push is accepted. The CI `chocolatey` job has `continue-on-error: true`
while moderation is pending.

---

## Current EXTRA_PIP in sync_spaces.py (corrected)

```python
EXTRA_PIP: dict[str, list[str]] = {
    # voice.clone uses XTTS-v2 via Coqui TTS (Tier 2 Space, not yet deployed)
    "assgen.audio.voice.clone": ["TTS>=0.22"],
    # LOD generation — pyfqmr is a C extension, build may fail on some platforms
    "assgen.lod.generate": ["pyfqmr>=0.2"],
    # UV unwrapping — xatlas Python bindings
    "assgen.uv.auto": ["xatlas>=0.0.9"],
    # TripoSR — image-to-3D (git install, not on PyPI)
    "assgen.model.splat": [
        "tsr @ git+https://github.com/VAST-AI-Research/TripoSR.git",
        "rembg>=2.0.57",
    ],
    # AnimateDiff needs imageio for GIF/MP4 export
    "assgen.animate.keyframe": [
        "imageio>=2.34.0",
        "imageio-ffmpeg>=0.4.9",
    ],
    # UI mockup uses ControlNet auxiliary preprocessors
    "assgen.ui.mockup": ["controlnet-aux>=0.0.7"],
}
```

Packages removed from EXTRA_PIP vs original spec:
- `assgen.texture.upscale`: `opencv-python-headless`, `basicsr`, `realesrgan` — removed (broken, replaced with diffusers)
- `assgen.audio.voice.tts`: `TTS>=0.22` — removed (handler doesn't use Coqui TTS)

---

## AUDIOCRAFT_SPACES (corrected)

```python
# All four audio generation Spaces (sfx, music.compose, music.loop, ambient.generate)
# now use transformers pipeline("text-to-audio") directly.
# audiocraft git install is not needed and not used.
AUDIOCRAFT_SPACES: set[str] = set()
```

---

## Tier 1 Status After All Fixes (2026-04-12)

All 10 Tier 1 Spaces are RUNNING on HF Hub (v0.3.3):

| Space | Model | Status |
|-------|-------|--------|
| assgen.concept.generate | stabilityai/stable-diffusion-xl-base-1.0 | ✓ RUNNING |
| assgen.audio.sfx.generate | facebook/audiogen-medium (via pipeline) | ✓ RUNNING |
| assgen.audio.music.compose | facebook/musicgen-medium (via pipeline) | ✓ RUNNING |
| assgen.audio.voice.tts | suno/bark (via transformers BarkModel) | ✓ RUNNING |
| assgen.texture.upscale | stabilityai/stable-diffusion-x4-upscaler | ✓ RUNNING |
| assgen.model.create | tencent/Hunyuan3D-2 | ✓ RUNNING |
| assgen.narrative.dialogue.npc | microsoft/Phi-3.5-mini-instruct | ✓ RUNNING |
| assgen.procedural.terrain.heightmap | (CPU, fractal Perlin noise) | ✓ RUNNING |
| assgen.scene.depth.estimate | Intel/dpt-large | ✓ RUNNING |
| assgen.texture.generate | stabilityai/stable-diffusion-xl-base-1.0 | ✓ RUNNING |

---

## Guidelines for All Future Spaces

1. **sdk_version must be `"5.23.0"`** (or the then-current Gradio 5.x). Never use 4.x.
2. **Do NOT add `python_version`** to Space card YAML.
3. **Do NOT use `audiocraft` git install** — use `pipeline("text-to-audio")` instead.
4. **Do NOT use `basicsr` or `realesrgan`** — they break with torchvision ≥ 0.16.
5. **Import model classes via `pipeline()`** not by class name — class names change between
   transformers versions; the pipeline task string is stable.
6. **Prefer `assgen.sdk.run()` for spaces that map 1:1 to a handler** — it's DRY and testable.
   **Use standalone transformers code** when the handler requires a broken pip package.
7. **Test EXTRA_PIP packages on HF before adding** — run a scratch Space with just the pip
   package in requirements.txt to confirm it installs in the HF Docker environment.
