# HuggingFace Spaces — Feasibility Analysis for assgen Generation Commands

_Generated: 2026-04-11 12:00:00 UTC_

This document is the reference input for the HF Spaces implementation agents. Read this first,
then proceed to the implementation spec documents.

---

## 1. Namespace Convention

HuggingFace Space repo names use dots as namespace separators, matching the pattern the user
established via examples:

| Rule | Example |
|------|---------|
| Drop the `gen` CLI prefix | `assgen gen audio sfx generate` → `assgen.audio.sfx.generate` |
| Drop the `visual` CLI domain prefix | `assgen gen visual rig auto` → `assgen.rig.auto` |
| Drop the `support` CLI grouping prefix | `assgen gen support narrative dialogue npc` → `assgen.narrative.dialogue.npc` |
| Keep all other domain prefixes (`audio`, `scene`, `procedural`, `pipeline`, `qa`, `narrative`, `data`) | `assgen gen scene lighting hdri` → `assgen.scene.lighting.hdri` |

**Full mapping table is in Section 3.**

The HF repo creation command pattern is:
```bash
hf repo create assgen.audio.sfx.generate --repo-type space --space-sdk gradio
```
Repos are created under your authenticated HF account. The full URL will be
`https://huggingface.co/spaces/{YOUR_HF_USERNAME}/assgen.audio.sfx.generate`.

---

## 1b. Technical Integration Architecture

See `20260411_120400_UTC_hf_spaces_packaging_and_sdk.md` for full details. Summary:

| Decision | Choice | Rationale |
|----------|--------|-----------|
| How Spaces call assgen | `assgen.sdk.run(job_type, params)` | Stable public API; handlers maintained once |
| Package install in Space | `assgen[spaces]` from PyPI | Single `requirements.txt` line per Space |
| audiocraft (not on PyPI) | `audiocraft @ git+...` added by sync script | Unavoidable until Meta publishes to PyPI |
| Space source location | `spaces/assgen.<name>/` in this repo | Single source of truth; CI syncs to HF Hub on tag |
| CI trigger | Same semver tag as release.yml | PyPI publish fires first, then Spaces sync |
| CPU vs ZeroGPU | Per-space `hardware:` in README.md | ~30 CPU-only, ~27 ZeroGPU |

**Prerequisite before any Space can go live:** Add PyPI publish step to `release.yml`
(see `20260411_120300_UTC_repo_health_improvements.md` Section 0.1).

---

## 2. HuggingFace Spaces Platform Constraints

Understanding these constraints drives the feasibility decisions below.

| Constraint | Details |
|-----------|---------|
| **Free CPU tier** | 2 vCPUs, 16 GB RAM, no GPU. Python 3.10. Fine for algorithmic / non-ML tasks. |
| **ZeroGPU** | Shared NVIDIA A100 (80 GB VRAM). Jobs queued dynamically. Use `@spaces.GPU` decorator. ~60 s limit per invocation. Free but rate-limited. |
| **Dedicated GPU tiers** | T4 small ($0.60/hr), A10G small ($3.15/hr), A100 ($4.13/hr). Required for models >20 GB or long inference. |
| **No persistent storage** | `/tmp` only. No writes outside the Space repo directory between requests. |
| **No privileged binaries** | Cannot install Blender, game engines, or arbitrary native Linux packages beyond what pip/apt provides. |
| **File upload limits** | Gradio default is 200 MB per upload. Large mesh files (>50 MB) will be close to the edge. |
| **Inference timeout** | ZeroGPU hard-kills after ~60 s per GPU call. Very large models (Hunyuan3D-2) may need dedicated GPU. |
| **`spaces` package** | Pre-installed in HF Spaces environments. Import with `import spaces`; no `requirements.txt` entry needed. |
| **HF Hub model cache** | Models are downloaded to `/tmp` on cold start. Large models add significant cold-start time. |

---

## 3. Complete Feasibility Matrix

### 3a. Visual Domain (drops `visual.` prefix in namespace)

| CLI Command | HF Space Name | Feasible | Tier | Hardware | Primary Model |
|-------------|---------------|----------|------|----------|---------------|
| `assgen gen visual concept generate` | `assgen.concept.generate` | ✅ | 1 | ZeroGPU | SDXL Base 1.0 |
| `assgen gen visual concept style` | `assgen.concept.style` | ✅ | 2 | ZeroGPU | IP-Adapter + SDXL |
| `assgen gen visual blockout create` | `assgen.blockout.create` | ✅ | 3 | ZeroGPU | SDXL (renders sketch) |
| `assgen gen visual model create` | `assgen.model.create` | ✅ | 1 | ZeroGPU (A100) | Hunyuan3D-2 |
| `assgen gen visual model multiview` | `assgen.model.multiview` | ✅ | 2 | ZeroGPU | Zero123++ |
| `assgen gen visual model splat` | `assgen.model.splat` | ✅ | 2 | ZeroGPU | TripoSR |
| `assgen gen visual model retopo` | `assgen.model.retopo` | ❌ | — | — | Blender required |
| `assgen gen visual mesh validate` | `assgen.mesh.validate` | ✅ | 2 | CPU | trimesh |
| `assgen gen visual mesh convert` | `assgen.mesh.convert` | ✅ | 3 | CPU | trimesh |
| `assgen gen visual mesh merge` | `assgen.mesh.merge` | ✅ | 3 | CPU | trimesh |
| `assgen gen visual mesh bounds` | `assgen.mesh.bounds` | ✅ | 3 | CPU | trimesh |
| `assgen gen visual mesh flipnormals` | `assgen.mesh.flipnormals` | ✅ | 3 | CPU | trimesh |
| `assgen gen visual mesh weld` | `assgen.mesh.weld` | ✅ | 3 | CPU | trimesh |
| `assgen gen visual mesh center` | `assgen.mesh.center` | ✅ | 3 | CPU | trimesh |
| `assgen gen visual mesh scale` | `assgen.mesh.scale` | ✅ | 3 | CPU | trimesh |
| `assgen gen visual lod generate` | `assgen.lod.generate` | ✅ | 3 | CPU | pyfqmr |
| `assgen gen visual uv auto` | `assgen.uv.auto` | ✅ | 3 | CPU | xatlas |
| `assgen gen visual texture generate` | `assgen.texture.generate` | ✅ | 1 | ZeroGPU | SDXL Base 1.0 |
| `assgen gen visual texture from_concept` | `assgen.texture.from_concept` | ✅ | 2 | ZeroGPU | IP-Adapter + SDXL |
| `assgen gen visual texture pbr` | `assgen.texture.pbr` | ✅ | 3 | CPU | algorithmic (Pillow) |
| `assgen gen visual texture bake` | `assgen.texture.bake` | ❌ | — | — | Blender renderer required |
| `assgen gen visual texture inpaint` | `assgen.texture.inpaint` | ✅ | 2 | ZeroGPU | SDXL Inpainting |
| `assgen gen visual texture upscale` | `assgen.texture.upscale` | ✅ | 1 | ZeroGPU | Real-ESRGAN x4+ |
| `assgen gen visual texture channel_pack` | `assgen.texture.channel_pack` | ✅ | 3 | CPU | Pillow |
| `assgen gen visual texture convert` | `assgen.texture.convert` | ✅ | 3 | CPU | Pillow |
| `assgen gen visual texture atlas_pack` | `assgen.texture.atlas_pack` | ✅ | 3 | CPU | Pillow |
| `assgen gen visual texture mipmap` | `assgen.texture.mipmap` | ✅ | 3 | CPU | Pillow |
| `assgen gen visual texture normalmap_convert` | `assgen.texture.normalmap_convert` | ✅ | 3 | CPU | Pillow |
| `assgen gen visual texture seamless` | `assgen.texture.seamless` | ✅ | 3 | CPU | Pillow |
| `assgen gen visual texture resize` | `assgen.texture.resize` | ✅ | 3 | CPU | Pillow |
| `assgen gen visual texture report` | `assgen.texture.report` | ✅ | 3 | CPU | Pillow |
| `assgen gen visual rig auto` | `assgen.rig.auto` | ✅ | 2 | ZeroGPU | UniRig |
| `assgen gen visual animate keyframe` | `assgen.animate.keyframe` | ✅ | 2 | ZeroGPU | AnimateDiff v1.5 |
| `assgen gen visual animate mocap` | `assgen.animate.mocap` | ✅ | 2 | ZeroGPU | Sapiens Pose 0.3B |
| `assgen gen visual animate retarget` | `assgen.animate.retarget` | ❌ | — | — | Skeletal solver (Blender/BVH) required |
| `assgen gen visual vfx particle` | `assgen.vfx.particle` | ✅ | 3 | CPU | Pillow + numpy |
| `assgen gen visual ui icon` | `assgen.ui.icon` | ✅ | 2 | ZeroGPU | SDXL |
| `assgen gen visual ui button` | `assgen.ui.button` | ✅ | 3 | ZeroGPU | SDXL |
| `assgen gen visual ui panel` | `assgen.ui.panel` | ✅ | 3 | ZeroGPU | SDXL |
| `assgen gen visual ui widget` | `assgen.ui.widget` | ✅ | 3 | ZeroGPU | SDXL |
| `assgen gen visual ui mockup` | `assgen.ui.mockup` | ✅ | 2 | ZeroGPU | ControlNet + SDXL |
| `assgen gen visual ui layout` | `assgen.ui.layout` | ✅ | 3 | ZeroGPU | SDXL |
| `assgen gen visual ui iconset` | `assgen.ui.iconset` | ✅ | 3 | ZeroGPU | SDXL |
| `assgen gen visual ui theme` | `assgen.ui.theme` | ✅ | 3 | ZeroGPU | SDXL |
| `assgen gen visual ui screen` | `assgen.ui.screen` | ✅ | 3 | ZeroGPU | SDXL |
| `assgen gen visual sprite pack` | `assgen.sprite.pack` | ✅ | 3 | CPU | Pillow |

### 3b. Audio Domain

| CLI Command | HF Space Name | Feasible | Tier | Hardware | Primary Model |
|-------------|---------------|----------|------|----------|---------------|
| `assgen gen audio sfx generate` | `assgen.audio.sfx.generate` | ✅ | 1 | ZeroGPU | AudioGen Medium |
| `assgen gen audio music compose` | `assgen.audio.music.compose` | ✅ | 1 | ZeroGPU | MusicGen Medium |
| `assgen gen audio music loop` | `assgen.audio.music.loop` | ✅ | 2 | ZeroGPU | MusicGen Medium |
| `assgen gen audio music adaptive` | `assgen.audio.music.adaptive` | ✅ | 3 | ZeroGPU | MusicGen Large |
| `assgen gen audio ambient generate` | `assgen.audio.ambient.generate` | ✅ | 2 | ZeroGPU | MusicGen Stereo Large |
| `assgen gen audio voice tts` | `assgen.audio.voice.tts` | ✅ | 1 | ZeroGPU | Bark (suno/bark) |
| `assgen gen audio voice clone` | `assgen.audio.voice.clone` | ✅ | 2 | ZeroGPU | XTTS-v2 |
| `assgen gen audio process normalize` | `assgen.audio.process.normalize` | ✅ | 3 | CPU | pydub + pyloudnorm |
| `assgen gen audio process trim_silence` | `assgen.audio.process.trim_silence` | ✅ | 3 | CPU | pydub |
| `assgen gen audio process loop_optimize` | `assgen.audio.process.loop_optimize` | ✅ | 3 | CPU | scipy |
| `assgen gen audio process convert` | `assgen.audio.process.convert` | ✅ | 3 | CPU | pydub (needs ffmpeg) |
| `assgen gen audio process downmix` | `assgen.audio.process.downmix` | ✅ | 3 | CPU | pydub |
| `assgen gen audio process resample` | `assgen.audio.process.resample` | ✅ | 3 | CPU | scipy |
| `assgen gen audio process waveform` | `assgen.audio.process.waveform` | ✅ | 3 | CPU | matplotlib |

### 3c. Scene Domain

| CLI Command | HF Space Name | Feasible | Tier | Hardware | Primary Model |
|-------------|---------------|----------|------|----------|---------------|
| `assgen gen scene physics collider` | `assgen.scene.physics.collider` | ✅ | 3 | CPU | V-HACD / CoACD |
| `assgen gen scene lighting hdri` | `assgen.scene.lighting.hdri` | ✅ | 2 | ZeroGPU | Intel LDM3D-pano |
| `assgen gen scene depth estimate` | `assgen.scene.depth.estimate` | ✅ | 1 | ZeroGPU | Intel DPT-Large |

### 3d. Procedural Domain

| CLI Command | HF Space Name | Feasible | Tier | Hardware | Primary Model |
|-------------|---------------|----------|------|----------|---------------|
| `assgen gen procedural terrain heightmap` | `assgen.procedural.terrain.heightmap` | ✅ | 1 | CPU | numpy / noise |
| `assgen gen procedural texture noise` | `assgen.procedural.texture.noise` | ✅ | 3 | CPU | numpy |
| `assgen gen procedural level dungeon` | `assgen.procedural.level.dungeon` | ✅ | 2 | CPU | BSP / cellular automata |
| `assgen gen procedural level voronoi` | `assgen.procedural.level.voronoi` | ✅ | 3 | CPU | scipy |
| `assgen gen procedural foliage scatter` | `assgen.procedural.foliage.scatter` | ✅ | 3 | CPU | Poisson disk / numpy |
| `assgen gen procedural tileset wfc` | `assgen.procedural.tileset.wfc` | ✅ | 3 | CPU | Wave Function Collapse |
| `assgen gen procedural plant lsystem` | `assgen.procedural.plant.lsystem` | ✅ | 3 | CPU | L-system |

### 3e. Pipeline Domain — ALL INFEASIBLE

| CLI Command | HF Space Name | Feasible | Reason |
|-------------|---------------|----------|--------|
| `assgen gen pipeline asset manifest` | `assgen.pipeline.asset.manifest` | ❌ | Operates on a local game project directory tree; no meaningful web demo |
| `assgen gen pipeline asset validate` | `assgen.pipeline.asset.validate` | ❌ | Same — whole-project file walker |
| `assgen gen pipeline asset rename` | `assgen.pipeline.asset.rename` | ❌ | Same — batch renames local files |
| `assgen gen pipeline asset report` | `assgen.pipeline.asset.report` | ❌ | Same — reads local project tree |
| `assgen gen pipeline git lfs_rules` | `assgen.pipeline.git.lfs_rules` | ❌ | Outputs `.gitattributes` content for a local Git repo; no web demo value |
| `assgen gen pipeline integrate export` | `assgen.pipeline.integrate.export` | ❌ | Requires Unity/Godot/Unreal engine installed locally |

### 3f. Support / Narrative Domain

| CLI Command | HF Space Name | Feasible | Tier | Hardware | Primary Model |
|-------------|---------------|----------|------|----------|---------------|
| `assgen gen support narrative dialogue npc` | `assgen.narrative.dialogue.npc` | ✅ | 1 | ZeroGPU | Phi-3.5-mini-instruct |
| `assgen gen support narrative dialogue validate` | `assgen.narrative.dialogue.validate` | ⚠️ | 3 | CPU | networkx — low demo value |
| `assgen gen support narrative lore generate` | `assgen.narrative.lore.generate` | ✅ | 2 | ZeroGPU | Phi-3.5-mini-instruct |
| `assgen gen support narrative quest design` | `assgen.narrative.quest.design` | ✅ | 2 | ZeroGPU | Phi-3.5-mini-instruct |
| `assgen gen support narrative quest validate` | `assgen.narrative.quest.validate` | ⚠️ | 3 | CPU | networkx — low demo value |
| `assgen gen support data i18n extract` | `assgen.data.i18n.extract` | ❌ | — | — | Extracts strings from local source files; no web demo |

### 3g. QA Domain — ALL INFEASIBLE

| CLI Command | Feasible | Reason |
|-------------|----------|--------|
| `assgen gen qa validate` | ❌ | Validates a full local game asset project; requires directory context |
| `assgen gen qa report` | ❌ | Same — whole-project analysis tool |

---

## 4. Infeasibility Justifications (Detail)

### `assgen.model.retopo` — Requires Blender
Auto-retopology as implemented depends on Blender's Python API (`bpy`) or a native retopology
solver (e.g., QuadriFlow, Instant Meshes) that compiles from C++ and cannot be pip-installed in
a standard HF Spaces environment. The `pyfqmr` fallback in the assgen handler does decimation,
not retopology — the mesh stays triangulated with no quads.

**Potential workaround (not in scope):** A dedicated Blender Docker image on a dedicated GPU
Space could work, but that's a custom Space type, not standard Gradio.

### `assgen.texture.bake` — Requires Blender's GPU rasterizer
High-to-low-poly baking requires a rasterization pass: render the high-poly mesh onto the UV
space of the low-poly mesh. This needs either Blender Cycles/EEVEE or a GPU-accelerated OpenGL
rasterizer. Neither is available in HF Spaces' standard pip environment.

### `assgen.animate.retarget` — Requires skeletal solver
Retargeting an animation from one skeleton to another requires BVH parsing, bone chain
matching, and inverse kinematics solving. The assgen handler uses CMU Mocap data + Blender's
NLA (non-linear animation) system. No pip-installable pure-Python skeletal solver exists that
handles arbitrary rig topologies.

### Pipeline commands — No web demo meaning
These six commands operate on a developer's local game project directory:
- They walk directory trees to find assets
- They write `.gitattributes` or manifest JSON files into the project
- They invoke game engine CLI tools (`unity`, `godot`, `unreal`)

None of these have a useful input/output pair for a Gradio web demo.

### `assgen.data.i18n.extract` — Local project operation
Parses source code files (`.cs`, `.gd`, `.lua`, `.py`) within a game project to extract
localization strings. Requires access to a real game project on disk.

### QA commands — Whole-project context required
Both `assgen gen qa validate` and `assgen gen qa report` analyze an entire asset project tree:
they check polygon budgets across all meshes, texture resolution consistency, UV island
overlap across the whole atlas. Uploading an entire game project to a web demo is impractical.

---

## 5. Priority Tier Summary

### Tier 1 — Implement First (10 Spaces)
Highest demo value, clearest input/output, best showcase for assgen capabilities.
Full implementation specs (complete `app.py`, `requirements.txt`, `README.md`) are in
`20260411_120100_UTC_hf_spaces_spec_tier1.md`.

| # | Space Name | What It Shows |
|---|-----------|----------------|
| 1 | `assgen.audio.sfx.generate` | AudioGen: text → game sound effect WAV |
| 2 | `assgen.audio.music.compose` | MusicGen: text → game music track |
| 3 | `assgen.audio.voice.tts` | Bark: text → expressive NPC speech |
| 4 | `assgen.concept.generate` | SDXL: text → game concept art |
| 5 | `assgen.texture.generate` | SDXL: text → tileable game texture |
| 6 | `assgen.texture.upscale` | Real-ESRGAN: 4× AI texture upscaling |
| 7 | `assgen.model.create` | Hunyuan3D-2: image → 3D game asset (.glb) |
| 8 | `assgen.scene.depth.estimate` | DPT-Large: image → depth map |
| 9 | `assgen.narrative.dialogue.npc` | Phi-3.5: text prompt → NPC dialogue lines |
| 10 | `assgen.procedural.terrain.heightmap` | Pure Python: params → terrain heightmap PNG |

### Tier 2 — High Value, Implement After Tier 1 (17 Spaces)
Strong demos but heavier setup or narrower audience. Abbreviated specs in
`20260411_120200_UTC_hf_spaces_spec_tier2_tier3.md`.

`assgen.audio.ambient.generate`, `assgen.audio.voice.clone`, `assgen.audio.music.loop`,
`assgen.model.multiview`, `assgen.model.splat`, `assgen.rig.auto`, `assgen.animate.keyframe`,
`assgen.animate.mocap`, `assgen.concept.style`, `assgen.texture.inpaint`,
`assgen.texture.from_concept`, `assgen.scene.lighting.hdri`, `assgen.narrative.lore.generate`,
`assgen.narrative.quest.design`, `assgen.ui.icon`, `assgen.ui.mockup`,
`assgen.procedural.level.dungeon`

### Tier 3 — Utility Tools (30+ Spaces)
CPU-only or narrow-use tools. Good for completeness but lower demo impact.
Also listed in `20260411_120200_UTC_hf_spaces_spec_tier2_tier3.md`.

All mesh utilities, audio processing tools, texture utilities, remaining procedural generators,
and `assgen.mesh.validate`.

---

## 6. Spaces Summary Counts

| Status | Count |
|--------|-------|
| ✅ Feasible (Tier 1) | 10 |
| ✅ Feasible (Tier 2) | 17 |
| ✅ Feasible (Tier 3) | ~30 |
| ⚠️ Low demo value (technically feasible) | 2 |
| ❌ Infeasible | 12 |
| **Total commands analyzed** | **82** |
