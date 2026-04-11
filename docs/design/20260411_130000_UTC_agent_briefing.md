# HuggingFace Spaces — Agent Implementation Briefing

_Generated: 2026-04-11 13:00:00 UTC_
_Start here. This is the authoritative entry point for any agent implementing the HF Spaces work._

---

## 1. Document Reading Order (Required)

Read these documents in this exact order before writing any code:

| # | Document | Why |
|---|----------|-----|
| 1 | This file | Entry point, conflict resolution, current state |
| 2 | `20260411_120000_UTC_hf_spaces_feasibility.md` | Namespace convention, feasibility matrix, tier assignments |
| 3 | `20260411_120400_UTC_hf_spaces_packaging_and_sdk.md` | SDK module spec, pyproject extras, CI/CD, sync script |
| 4 | `20260411_120500_UTC_hf_spaces_implementation_risks.md` | Verified handler params table, bugs, local test workflow |
| 5 | `20260411_120100_UTC_hf_spaces_spec_tier1.md` | Complete app.py + README.md for 10 Tier 1 Spaces |
| 6 | `20260411_120200_UTC_hf_spaces_spec_tier2_tier3.md` | Abbreviated specs for 47 Tier 2/3 Spaces |
| 7 | `20260411_120300_UTC_repo_health_improvements.md` | Repo health checklist (do P0 items first, alongside Phase 0) |

---

## 2. Conflict Resolution

When two documents give different instructions for the same thing, the later document in the
reading order above wins. Specifically:

| Conflict | Authoritative source |
|----------|---------------------|
| `sdk.py` catalog import (`get_catalog` vs `get_model_for_job`) | `_implementation_risks` (Section 2) — `get_model_for_job` is correct |
| `sync_spaces.py` upload method (subprocess vs `HfApi`) | `_implementation_risks` (Section 7) — `HfApi.upload_folder` is correct |
| Handler param key names for Tier 1 Spaces | `_implementation_risks` (Section 4 verified table) wins over `_spec_tier1` code examples |
| `requirements.txt` per Space directory (yes vs no) | `_packaging_and_sdk` (Section 4) — do NOT create `requirements.txt` in repo |
| `scene.depth.estimate` colormap UI (dropdown vs no dropdown) | `_implementation_risks` (Section 1c) — remove the dropdown, hardcode `"colormap": "true"` |

---

## 3. Current Repo State (as of 2026-04-11)

What **already exists:**
- All handler modules at `src/assgen/server/handlers/*.py` (80 handlers, stubs or real)
- `src/assgen/catalog.py` with `get_model_for_job()`, `get_model_for_job_quality()`, `all_job_types()`, `all_model_ids()`
- `src/assgen/server/worker.py` with `_load_handler(job_type)` (returns stub if handler has no inference dep)
- `.github/workflows/release.yml` — builds wheel/sdist and attaches to GitHub Release, but **no PyPI publish step yet**
- `scripts/` directory exists (`smoke_test_inference.py`, `export_openapi.py`, etc.)
- `pyproject.toml` with `[inference]` and `[dev]` extras, but **no `[spaces]` extra yet**
- `.venv/` with editable install of assgen

What **does not yet exist:**
- `src/assgen/sdk.py` (must be created — see packaging doc Section 2)
- `spaces/` directory (must be created — each Space gets a subdirectory)
- `scripts/sync_spaces.py` (must be created — see packaging doc Section 5)
- PyPI publish step in `release.yml` (must be added — see packaging doc Section 1)
- `[spaces]` optional-dependency group in `pyproject.toml` (must be added — see repo health doc P0.2)
- HuggingFace Space repos on HF Hub (must be created with `hf repo create ...` commands)

---

## 4. Handler Module Naming Convention

Handler module names use underscores; `job_type` strings use dots. The SDK and worker derive
module paths via `job_type.replace(".", "_")`:

| CLI command | `job_type` string | Handler module file |
|-------------|-------------------|---------------------|
| `assgen gen audio sfx generate` | `audio.sfx.generate` | `audio_sfx_generate.py` |
| `assgen gen visual concept generate` | `visual.concept.generate` | `visual_concept_generate.py` |
| `assgen gen scene depth estimate` | `scene.depth.estimate` | `scene_depth_estimate.py` |

**To verify a handler exists:**
```bash
python -c "from assgen.catalog import all_job_types; print('\n'.join(all_job_types()))"
```

**To read a handler's params contract before writing an app.py (required for all Tier 2/3):**
```bash
# Step 1: check the module docstring
head -30 src/assgen/server/handlers/audio_ambient_generate.py

# Step 2: list every params.get() call
grep -n "params.get" src/assgen/server/handlers/audio_ambient_generate.py
```

---

## 5. Unified Task Sequence

Complete these phases in order. Each phase depends on the previous.

### Phase 0 — Infrastructure Blockers (must complete before any Space goes live)

| Task | File | Notes |
|------|------|-------|
| 0.1 Add PyPI publish step | `.github/workflows/release.yml` | After `hatch build`, before `Build docs site`. One-time PyPI Trusted Publisher setup required — see below |
| 0.2 Add `[spaces]` extra | `pyproject.toml` | Per repo health doc P0.2 |
| 0.3 Add `opencv-python-headless` to `[spaces]` extra | `pyproject.toml` | Required by `visual.texture.upscale` handler |
| 0.4 Create `src/assgen/sdk.py` | New file | Per packaging doc Section 2 — ~85 lines. Use `get_model_for_job()`, not `get_catalog()` |
| 0.5 Create `scripts/sync_spaces.py` | New file | Per packaging doc Section 5 — use `HfApi.upload_folder()`, not subprocess |
| 0.6 Add repo health P0/P1 items | Various | Per `20260411_120300_UTC_repo_health_improvements.md`, items 1.1–1.6 |
| 0.7 Verify SDK works | Terminal | `python -c "from assgen.sdk import run; print('OK')"` |
| 0.8 Create `scripts/generate_run_configs.py` | New file | Per `20260411_131500_UTC_pycharm_run_configs.md` Section 7 — 72 PyCharm run configurations for all feasible Spaces, grouped by domain. The XMLs are already generated and tracked in `.idea/runConfigurations/`. This script regenerates them if the Space list changes. |

### Phase 1 — spaces/ Directory Setup

| Task | Notes |
|------|-------|
| Create `spaces/_template/` | Copy template from packaging doc Section 4 |
| Add spaces-sync job to `release.yml` | Per packaging doc Section 5 — needs `HF_TOKEN` secret (manual, see Section 6) |

### Phase 2 — Tier 1 Spaces (10 Spaces)

Implement in this order (simplest to most complex):

1. `assgen.procedural.terrain.heightmap` — CPU-only, no GPU decorator, simplest possible
2. `assgen.audio.sfx.generate` — AudioGen, ZeroGPU, confirmed params
3. `assgen.audio.music.compose` — same pattern as sfx
4. `assgen.audio.voice.tts` — Bark, voice preset dropdown
5. `assgen.texture.upscale` — Real-ESRGAN, image input, key is `"input"` not `"input_path"`
6. `assgen.concept.generate` — SDXL, key is `"steps"` not `"num_inference_steps"`
7. `assgen.texture.generate` — same SDXL fix as above
8. `assgen.scene.depth.estimate` — no colormap dropdown; `"colormap": "true"` hardcoded
9. `assgen.model.create` — Hunyuan3D-2, key is `"image"` not `"image_path"`
10. `assgen.narrative.dialogue.npc` — Phi-3.5, keys `"character"/"context"/"lines"`, read output from JSON file

Full `app.py` + `README.md` for all 10 are in `_spec_tier1`. Use the corrected param keys
from `_implementation_risks` Section 4 (verified table), not the raw code examples in `_spec_tier1`
where they conflict.

> **PyCharm:** As soon as `spaces/assgen.X/app.py` is written, the corresponding run config in
> `.idea/runConfigurations/space_assgen_X.xml` is already tracked in git and shows up immediately
> in PyCharm's Run dropdown under its domain folder. No manual IDE setup needed.

**After implementing Space #2 (`assgen.audio.sfx.generate`) — stop and verify locally:**
```bash
cd spaces/assgen.audio.sfx.generate
pip install -e "../../.[spaces]"
python app.py
# Gradio should open at http://127.0.0.1:7860
# Test with: "footsteps on stone", duration 2s
```
Only proceed to the remaining Tier 1 Spaces after this local test passes.

### Phase 3 — First Deployment

Follow the 15-step sequence in `_implementation_risks` Section 10 exactly. Key gates:
- Step 8: `pip install "assgen[spaces]==0.X.Y"` must succeed before creating Space repos
- Step 12: One Space (audio.sfx.generate) must build green on HF Hub before syncing all 10

### Phase 4 — Tier 2 Spaces (17 Spaces)

For each Tier 2 Space:
1. Read the abbreviated spec in `_spec_tier2_tier3`
2. Run `grep -n "params.get" src/assgen/server/handlers/<handler_module>.py` to confirm all param keys
3. Write `app.py` + `README.md` using the Tier 1 pattern
4. Local test before syncing

**Do not create `requirements.txt` files** — the sync script generates them.

### Phase 5 — Tier 3 Spaces (~30 Spaces)

Same procedure as Tier 4. CPU-only Spaces omit the `spaces` import block and `@spaces.GPU`.
Use `hardware: cpu-basic` in the README.md frontmatter.

---

## 6. Manual Steps the Agent Cannot Perform

These require human action in a browser. Do them before Phase 3.

### 6a. PyPI Trusted Publisher setup (one-time)
1. Log into pypi.org → Your Account → Publishing → "Add a new pending publisher"
2. Set: Owner=`aallbrig`, Repository=`assgen`, Workflow=`release.yml`, Environment=(leave blank)
3. This must be done **before** a version tag is pushed — otherwise the first publish step fails

### 6b. HF_TOKEN GitHub secret
1. Go to huggingface.co → Settings → Access Tokens → New token (role: Write)
2. Copy the token
3. Go to GitHub repo → Settings → Secrets and variables → Actions → New repository secret
4. Name: `HF_TOKEN`, value: paste the token
5. This must be done **before** the `spaces-sync` job is triggered by a tag push

### 6c. HF Space repo creation (batch, one-time per Space)
Run the `hf repo create ...` commands from each Space's spec before first sync.
All 10 Tier 1 creation commands are in `_spec_tier1`. Batch example:
```bash
hf repo create assgen.audio.sfx.generate --repo-type space --space-sdk gradio
hf repo create assgen.audio.music.compose --repo-type space --space-sdk gradio
# ... (one per Space)
```

---

## 7. Versioning Strategy for First Deployment

The first HF Spaces deployment requires a published PyPI package. Steps:

1. Complete Phase 0 (PyPI step in release.yml + Trusted Publisher setup)
2. Choose the next version: look at `git tag --list` — if latest is `v0.1.x`, tag `v0.2.0`
3. `git tag v0.2.0 && git push --tags`
4. Watch release.yml — PyPI publish job must pass before proceeding
5. Verify: `pip index versions assgen` should show `0.2.0`
6. Then create the HF Space repos and run the sync

Do **not** create HF Space repos pointing at a version that isn't yet on PyPI.

---

## 8. Local Development and Test Loop

Use this cycle for every Space before pushing to HF Hub:

```bash
# 1. Navigate to the Space directory
cd spaces/assgen.<name>

# 2. Install assgen with spaces extra (from repo root)
pip install -e "../../.[spaces]"

# 3. For audio spaces: install audiocraft (not on PyPI)
pip install "audiocraft @ git+https://github.com/facebookresearch/audiocraft.git"

# 4. Verify the spaces shim works (no HF environment needed)
python -c "
try:
    import spaces
except ImportError:
    import types; spaces = types.SimpleNamespace(GPU=lambda fn: fn)
@spaces.GPU
def test(): return 'ok'
print(test())
"

# 5. Run the Space locally
python app.py
# Opens at http://127.0.0.1:7860

# 6. Test at least one example input end-to-end
# For audio: submit a prompt, confirm a .wav file is returned
# For image: submit an image, confirm the output renders
# For text: submit text, confirm non-empty string output

# 7. If the handler lacks inference deps, it returns stub output.
#    Stubs are acceptable for CI; only real inference confirms correctness on GPU.
```

---

## 9. Acceptance Criteria — Passing vs Failing

A Space is **done** when all of these pass:

| Check | How to verify |
|-------|--------------|
| Gradio UI loads without error | `python app.py` opens http://127.0.0.1:7860 |
| All UI inputs render correctly | No missing components, correct labels |
| Submitting a test input returns output | Output component populates (may be stub output locally) |
| Output is non-empty and correct type | Audio → .wav file; Image → .png/.jpg; Text → non-empty string; 3D → .glb |
| No silent param mismatch | Cross-check every `params.get()` key in the handler against what app.py passes |
| HF Hub Space build is green | After sync, the Space's "Build" status on HF Hub is "Running" or "Building" (not "Error") |

**Silent failure detection:** If a Space loads and accepts input but always returns a stub/placeholder
regardless of input content, a param key is almost certainly wrong. Compare your `run()` call
against the handler's `params.get()` calls line by line.

---

## 10. Space Name → job_type Mapping Reference

The HF Space repo name drops `visual.` and `support.` prefixes. The `run()` `job_type` argument
does NOT use the same convention — it matches the catalog key exactly.

| Space repo name | `run()` job_type |
|----------------|-----------------|
| `assgen.concept.generate` | `"visual.concept.generate"` |
| `assgen.texture.generate` | `"visual.texture.generate"` |
| `assgen.texture.upscale` | `"visual.texture.upscale"` |
| `assgen.model.create` | `"visual.model.create"` |
| `assgen.rig.auto` | `"visual.rig.auto"` |
| `assgen.animate.keyframe` | `"visual.animate.keyframe"` |
| `assgen.animate.mocap` | `"visual.animate.mocap"` |
| `assgen.narrative.dialogue.npc` | `"narrative.dialogue.npc"` |
| `assgen.narrative.lore.generate` | `"narrative.lore.generate"` |
| `assgen.narrative.quest.design` | `"narrative.quest.design"` |
| `assgen.audio.sfx.generate` | `"audio.sfx.generate"` |
| `assgen.scene.depth.estimate` | `"scene.depth.estimate"` |
| `assgen.procedural.terrain.heightmap` | `"procedural.terrain.heightmap"` |

For domains that keep their prefix (`audio`, `scene`, `procedural`, `pipeline`, `qa`, `data`),
the Space name equals the job_type string exactly.

**Verify any job_type before using it:**
```bash
python -c "from assgen.catalog import all_job_types; print('\n'.join(all_job_types()))"
```
