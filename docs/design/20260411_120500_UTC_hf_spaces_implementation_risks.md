# HuggingFace Spaces — Implementation Risks, Bugs, and Verified Handler Contracts

_Generated: 2026-04-11 12:05:00 UTC_

This document must be read alongside the Tier 1 spec before any implementation begins.
It records bugs found in the Tier 1 spec by reading the actual handler source, corrections
to the SDK module design, missing dependencies, and local testing instructions.

---

## 1. Bugs in the Tier 1 Spec (Will Cause Silent Failures)

### 1a. Wrong `params` keys — concept.generate

**Tier 1 spec passes:** `"num_inference_steps"`
**Handler (`visual_concept_generate.py`) reads:** `params.get("steps")`

The handler will silently use its internal default (30 steps) regardless of the UI slider value.

**Fix:** In `spaces/assgen.concept.generate/app.py`, change:
```python
# WRONG
{"prompt": prompt, "negative_prompt": negative, "num_inference_steps": steps, ...}

# CORRECT
{"prompt": prompt, "negative_prompt": negative, "steps": steps, ...}
```

Same fix applies to `assgen.texture.generate` — same handler pattern.

---

### 1b. Wrong `params` key — texture.upscale

**Tier 1 spec passes:** `{"input_path": tmp.name, "scale": ...}`
**Handler (`visual_texture_upscale.py`) reads:** `params.get("input")`

The handler will raise `ValueError: Input file not found: ''` every time.

**Fix:** Change the key from `"input_path"` to `"input"`.

Also: the upscale handler uses `cv2` (OpenCV) which is **not in the `[spaces]` extra**.
Add to `pyproject.toml` spaces extra: `"opencv-python-headless>=4.9"`.

---

### 1c. Wrong `params` key — scene.depth.estimate

**Tier 1 spec passes:** `{"input_path": tmp.name, "colormap": colormap_name}`
**Handler (`scene_depth_estimate.py`) reads:** `params.get("input")` for the file path.

Two issues:
1. Key is `"input"`, not `"input_path"` — will raise ValueError
2. The `colormap` param is treated by the handler as a **boolean flag** (`"true"`/`"false"`) controlling whether to save a false-colour overlay at all — not which matplotlib colormap to use. The handler uses its own hardcoded colormap internally.

**Fix for the app.py:**
```python
# WRONG
result = run("scene.depth.estimate",
             {"input_path": tmp.name, "colormap": colormap},   # colormap = "Inferno" etc.
             device="cuda")

# CORRECT
result = run("scene.depth.estimate",
             {"input": tmp.name, "colormap": "true"},          # always generate colormap
             device="cuda")
```

**Fix for the UI:** Remove the colormap dropdown entirely. The handler does not expose colormap
selection. Replace with a simple "Show colorized overlay" checkbox if desired.

---

### 1d. Complete params mismatch — narrative.dialogue.npc

**Tier 1 spec passes:** `{"persona": ..., "player_text": ..., "tone": ..., "max_lines": ...}`
**Handler (`narrative_dialogue_npc.py`) reads:**
```python
character = params.get("character") or "Generic NPC"   # NOT "persona"
context   = params.get("context") or ""                # NOT "player_text"
lines     = int(params.get("lines", 10))               # NOT "max_lines"
branching = bool(params.get("branching", False))       # not in spec UI at all
```

Every param key is wrong. The Space will use handler defaults (Generic NPC, no context,
10 lines) silently regardless of what the user enters.

**Fix for the app.py:**
```python
# WRONG
result = run("narrative.dialogue.npc",
             {"persona": persona, "player_text": player_text,
              "tone": tone, "max_lines": max_lines},
             device="cuda")

# CORRECT
result = run("narrative.dialogue.npc",
             {"character": persona,   # "persona" label in UI, "character" key for handler
              "context": player_text, # "player_text" label in UI, "context" key for handler
              "lines": max_lines,     # "max_lines" label in UI, "lines" key for handler
              # "branching": False   # optional — add checkbox to UI if desired
             },
             device="cuda")
```

Also note: the handler returns a JSON object in `result["metadata"]` (parsed from the model's
JSON output), not a file. Update the output handling:
```python
# The dialogue text is in metadata, not files
dialogue_json = result.get("metadata", {})
return dialogue_json.get("lines", [{"text": "(no output)"}])
```
Check the full handler return contract before finalising the output component.

---

### 1e. Wrong `params` key — model.create

**Tier 1 spec passes:** `{"image_path": ..., "prompt": ...}`
**Handler (`visual_model_create.py`) reads:** `params.get("image") or params.get("input")`

**Fix:** Change `"image_path"` to `"image"`.

---

## 2. Bug in `assgen.sdk` Module Spec

The SDK spec in `20260411_120400_UTC_hf_spaces_packaging_and_sdk.md` contains:
```python
# WRONG — function does not exist
from assgen.catalog import get_catalog
entry = get_catalog().get(job_type, {})
model_id = entry.get("model_id")
```

**The actual catalog API is:**
```python
# CORRECT
from assgen.catalog import get_model_for_job
entry = get_model_for_job(job_type) or {}
model_id = entry.get("model_id")
```

`assgen.catalog` exposes: `load_catalog()`, `get_model_for_job(job_type)`,
`get_model_for_job_quality(job_type, quality)`, `all_job_types()`, `all_model_ids()`.
There is no `get_catalog()`. The corrected `sdk.py` block:

```python
if model_id is None:
    try:
        from assgen.catalog import get_model_for_job
        entry = get_model_for_job(job_type) or {}
        model_id = entry.get("model_id")
    except Exception:
        model_id = None
```

---

## 3. Missing Dependency: `opencv-python-headless`

The `visual.texture.upscale` handler imports `cv2`. This is not covered by `assgen[spaces]`.

**Fix:** Add to `pyproject.toml` in the `spaces` extra:
```toml
"opencv-python-headless>=4.9",
```

Use `opencv-python-headless` (not `opencv-python`) because HF Spaces have no display server.

---

## 4. Verified Handler `params` Contract (Tier 1 Spaces)

Use this table when writing or reviewing app.py files. "Handler key" is what `params.get()` uses.

| Space | UI label | Handler key | Type | Notes |
|-------|----------|-------------|------|-------|
| **audio.sfx.generate** | Description | `prompt` | str | Also accepts `description` |
| | Duration (s) | `duration` | float | Default: 4.0 |
| | Variations | `variations` | int | Default: 1 |
| **audio.music.compose** | Description | `prompt` | str | |
| | Duration (s) | `duration` | float | |
| **audio.voice.tts** | Text | `text` | str | Also accepts `prompt` |
| | Voice preset | `voice_preset` | str | e.g. `"v2/en_speaker_6"` |
| | Format | `output_format` | str | `"wav"` default |
| **concept.generate** | Prompt | `prompt` | str | Also accepts `text` |
| | Negative prompt | `negative_prompt` | str | Has sensible default |
| | Steps | `steps` | int | ⚠️ NOT `num_inference_steps` |
| | Guidance scale | `guidance_scale` | float | |
| | Seed | `seed` | int | None = random |
| | Width | `width` | int | Default 1024 |
| | Height | `height` | int | Default 1024 |
| **texture.generate** | Description | `prompt` | str | Handler adds texture suffix |
| | Steps | `steps` | int | ⚠️ NOT `num_inference_steps` |
| | Guidance | `guidance_scale` | float | |
| | Seed | `seed` | int | |
| **texture.upscale** | Input image | `input` | str (file path) | ⚠️ NOT `input_path` |
| | Scale | `scale` | int | 2 or 4 |
| | Tile | `tile` | int | Default 0 (auto) |
| | Output name | `output` | str | Optional override |
| **model.create** | Image | `image` | str (file path) | Also accepts `input` |
| | Prompt | `prompt` | str | Optional |
| | Steps | `num_inference_steps` | int | 50 default |
| | Guidance | `guidance_scale` | float | |
| **scene.depth.estimate** | Input image | `input` | str (file path) | ⚠️ NOT `input_path` |
| | Colormap output | `colormap` | str bool | `"true"`/`"false"` — not a colormap name |
| | Normalize | `normalise` | str bool | `"true"`/`"false"` |
| **narrative.dialogue.npc** | NPC name/persona | `character` | str | ⚠️ NOT `persona` |
| | Context/situation | `context` | str | ⚠️ NOT `player_text` |
| | Line count | `lines` | int | ⚠️ NOT `max_lines` |
| | Branching | `branching` | bool | Optional, default False |
| | Context map | `context_map` | dict | For chained jobs; omit in Space |
| **procedural.terrain.heightmap** | Width | `width` | int | |
| | Height | `height` | int | |
| | Scale | `scale` | float | |
| | Octaves | `octaves` | int | |
| | Seed | `seed` | int | |
| | Colormap name | `colormap` | str | Check handler for supported names |

**For Tier 2/3 Spaces:** Read the first 20 lines of the handler file (they document params in the
module docstring) and run `grep -n "params.get" handler_file.py` before writing any app.py.

---

## 5. File-Path Handlers vs PIL-Image Handlers

Several handlers expect a **file path string** in params, not an in-memory image object.
For these, the Space must save the PIL image to a temporary file before calling `run()`.

Handlers that expect a file path in params (confirmed or inferred from handler source):
- `visual.texture.upscale` → `params["input"]` = path
- `visual.texture.generate` → uses PIL internally, likely accepts path or prompt only
- `scene.depth.estimate` → `params["input"]` = path
- `visual.model.create` → `params["image"]` = path
- All audio process handlers → `params["input"]` = path

**Standard pattern for image-path handlers:**
```python
@spaces.GPU
def run_space(image: Image.Image, ...) -> str:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        image.save(tmp.name)
        input_path = tmp.name                    # <-- pass this, not the PIL object
    result = run("job.type.here", {"input": input_path, ...}, device="cuda")
    # Clean up temp input after run completes
    import os; os.unlink(input_path)
    return result["files"][0]
```

---

## 6. `import spaces` Fails Outside HF Environment

`spaces` is a package that is **pre-installed in HF Spaces** but is **not on PyPI** for
standard pip install. Running `app.py` locally will fail with `ModuleNotFoundError: spaces`.

**Fix:** Add a shim at the top of every `app.py` that uses `@spaces.GPU`:

```python
try:
    import spaces
except ImportError:
    # Running locally — create a no-op shim so the decorator is harmless
    import types
    spaces = types.SimpleNamespace(GPU=lambda fn: fn)
```

With this shim, `@spaces.GPU` is a no-op locally and the app runs on the local GPU (or CPU)
without any HF infrastructure. This enables the full local test cycle:

```bash
# Local testing workflow
cd spaces/assgen.audio.sfx.generate
pip install -e "../../.[spaces]"
python app.py
# Opens Gradio dev server at http://127.0.0.1:7860
```

---

## 7. Fix `sync_spaces.py` — Use Python API, Not Subprocess

The sync script spec uses `subprocess.run(["hf", "upload", ...])` which depends on the
exact HF CLI version's argument format and fails silently if the command syntax changes.

**Replace with the stable Python API:**
```python
from huggingface_hub import HfApi

def sync_space(space_name: str, version: str) -> None:
    space_dir = SPACES_DIR / space_name
    if not space_dir.exists():
        print(f"  SKIP  {space_name}")
        return

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        shutil.copy(space_dir / "app.py", tmp_path / "app.py")
        shutil.copy(space_dir / "README.md", tmp_path / "README.md")
        (tmp_path / "requirements.txt").write_text(make_requirements(space_name, version))
        pkgs = make_packages_txt(space_name)
        if pkgs:
            (tmp_path / "packages.txt").write_text(pkgs)

        api = HfApi()
        try:
            api.upload_folder(
                folder_path=str(tmp_path),
                repo_id=space_name,
                repo_type="space",
                commit_message=f"assgen {version}",
            )
            print(f"  OK    {space_name}")
        except Exception as exc:
            print(f"  ERROR {space_name}: {exc}")
```

`HfApi` uses the token set by `hf login` (or `HF_TOKEN` env var) automatically.

---

## 8. The Space Name ≠ Job Type String

The HF Space naming convention drops the `visual.` and `support.` prefixes.
The `assgen.sdk.run()` job_type string does NOT follow the same convention —
it matches the handler module name and catalog key exactly.

| Space repo name | `run()` job_type argument |
|----------------|--------------------------|
| `assgen.concept.generate` | `"visual.concept.generate"` |
| `assgen.texture.generate` | `"visual.texture.generate"` |
| `assgen.rig.auto` | `"visual.rig.auto"` |
| `assgen.model.create` | `"visual.model.create"` |
| `assgen.narrative.dialogue.npc` | `"narrative.dialogue.npc"` |
| `assgen.audio.sfx.generate` | `"audio.sfx.generate"` |
| `assgen.scene.depth.estimate` | `"scene.depth.estimate"` |
| `assgen.procedural.terrain.heightmap` | `"procedural.terrain.heightmap"` |

**Verify any new job_type string before using it:**
```python
python -c "from assgen.catalog import all_job_types; print('\n'.join(all_job_types()))"
```
If a job_type is not in this list it will still dispatch (to a handler file if one exists)
but will have no catalog model_id, so `model_id=None` is passed to the handler. Most handlers
have hardcoded fallback model IDs in that case — but verify the specific handler.

---

## 9. Pre-Implementation Verification Checklist

Before writing a single Space `app.py`, run this locally:

```bash
# 1. Confirm catalog contains the job_type
python -c "
from assgen.catalog import get_model_for_job
jt = 'audio.sfx.generate'  # ← change per Space
entry = get_model_for_job(jt)
print(entry)
"

# 2. Confirm handler module exists
python -c "
from assgen.server.worker import _load_handler
h = _load_handler('audio.sfx.generate')  # ← change per Space
print(h)
"

# 3. Smoke-test the handler with correct params (CPU, no model download)
python -c "
from assgen.sdk import run
import tempfile, json
with tempfile.TemporaryDirectory() as d:
    # This will try to load the model — only use with [inference] installed
    # For a no-model smoke test, patch: result = run.__wrapped__(...)
    pass
print('SDK import OK')
from assgen.sdk import run; print('run() callable:', run)
"

# 4. Confirm spaces shim works
python -c "
try:
    import spaces
except ImportError:
    import types; spaces = types.SimpleNamespace(GPU=lambda fn: fn)
@spaces.GPU
def test(): return 'ok'
print(test())
"
```

---

## 10. First Deployment Ordering (Do Not Skip Steps)

```
1. Merge: add [spaces] extra + opencv-headless to pyproject.toml
2. Merge: create src/assgen/sdk.py (corrected catalog import)
3. Verify: python -c "from assgen.sdk import run; print('ok')"
4. Merge: add PyPI publish step to release.yml
5. One-time: configure PyPI Trusted Publisher on pypi.org
6. Tag: git tag v0.X.Y && git push --tags
7. Watch: release.yml → PyPI publish job passes
8. Verify: pip install "assgen[spaces]==0.X.Y" succeeds
9. Create HF Space repos (batch script from Tier 1 spec)
10. Implement + test 1 Space locally (assgen.audio.sfx.generate — simplest)
11. Manual sync: python scripts/sync_spaces.py --version 0.X.Y --space assgen.audio.sfx.generate
12. Verify Space builds green on HF Hub
13. Implement remaining Tier 1 Spaces
14. Full sync: python scripts/sync_spaces.py --version 0.X.Y
15. Merge: add spaces-sync job to release.yml (automates future releases)
```

Do not create all 10 Space repos at once before verifying step 12. Fail fast on one Space,
fix the issue, then proceed.
