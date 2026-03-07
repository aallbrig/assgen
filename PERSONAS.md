# assgen Personas

These personas represent the primary users of assgen.  They are used to:

- Prioritise which tasks belong in the catalog
- Evaluate whether a CLI command makes sense
- Decide what sensible defaults and `--help` text should say
- Identify gaps that need new HuggingFace models or new commands

---

## Persona 1 — Alex, the Solo Indie Dev

> *"I make everything myself.  I just need something good enough to ship."*

**Background**  
Alex is building a 3D action-RPG in Godot, completely solo, in their spare time.
They have a day job as a web developer, so time is the scarcest resource.
They have a mid-range GPU (RTX 3060) and know enough Python to edit a YAML file.

**Project**: a 3D dungeon-crawler with hand-crafted levels but AI-generated props,
textures, and music.

**Primary assgen workflows**

| Step | Command |
|---|---|
| Sketch a concept for a new prop | `assgen gen visual concept generate --prompt "rusty iron brazier, medieval"` |
| Turn that concept into a 3D mesh | `assgen gen visual model create --prompt "rusty iron brazier" --wait` |
| Generate a PBR texture set for it | `assgen gen visual texture generate --prompt "rusty iron, PBR diffuse sheet" --wait` |
| Compose a 30-second looping dungeon theme | `assgen gen audio music loop --prompt "dark dungeon ambience, low strings, eerie" --wait` |
| Quickly voice an NPC placeholder line | `assgen gen audio voice tts "The dungeon claims all who enter." --wait` |

**Pain points**
- Waiting 10 minutes per asset kills flow; wants `--wait` to stream progress, not block silently
- Needs `.glb` output they can drag straight into Godot
- Music must loop seamlessly; a 10-second clip is useless

**Acceptance criteria for assgen**
- A prop, texture, and 30-second loop generated in a single lunch break
- Zero manual post-processing required to import into Godot

---

## Persona 2 — Jordan, the Level / Environment Artist

> *"I build worlds.  I need a huge variety of assets without a huge art team."*

**Background**  
Jordan works at a 6-person indie studio making an open-world survival game in Unreal Engine 5.
They are the only environment artist.  They need terrain variety, skyboxes, tileable
textures, and hundreds of environmental props (rocks, stumps, crates).

**Project**: a procedurally generated post-apocalyptic world with biome-specific assets.

**Primary assgen workflows**

| Step | Command |
|---|---|
| Generate concept art for a biome | `assgen gen visual concept generate --prompt "overgrown highway, post-apocalyptic, foggy"` |
| Create a 360° sky/HDRI for a scene | `assgen gen scene lighting hdri --prompt "stormy industrial skyline at dusk" --wait` |
| Generate seamless ground texture | `assgen gen visual texture generate --prompt "cracked asphalt, seamless, 4K" --wait` |
| Fix a seam in a generated texture | `assgen gen visual texture inpaint --input crack.png --mask seam_mask.png --wait` |
| Estimate depth from a reference photo | `assgen gen scene depth estimate --input reference.jpg --wait` |

**Pain points**
- Tiling artefacts in AI-generated textures are a productivity blocker — inpainting is essential
- HDRI generation quality is inconsistent; wants iterative prompting without re-running the whole pipeline
- Props need LOD variants; no ML model exists yet for automatic LOD — wants a clear message that this is algorithmic

**Acceptance criteria for assgen**
- Generates a full tileable PBR set (albedo, normal, roughness) from one prompt
- HDRI output is equirectangular and importable in Unreal without conversion

**Known gap**: automatic LOD generation is algorithmic (not ML); assgen should emit a
helpful error pointing to Unreal's built-in decimation tools rather than silently failing.

---

## Persona 3 — Maya, the Character Artist

> *"Characters are the heart of our game.  Rigging by hand is killing us."*

**Background**  
Maya works at a 15-person studio building a third-person RPG.  She handles character
modelling, rigging, and basic animation sets.  Their engine is Unity.  They have
multiple NPCs to ship each sprint and the rig + skin process takes days per character.

**Project**: a fantasy RPG with 40+ unique NPC character models.

**Primary assgen workflows**

| Step | Command |
|---|---|
| Generate front/back/side reference sheet | `assgen gen visual concept generate --prompt "elf ranger, full body, front back side views, white background"` |
| Image-to-3D from approved concept | `assgen gen visual model create --input concept.png --wait` |
| Auto-rig the generated mesh | `assgen gen visual rig auto --input character.glb --wait` |
| Generate idle and walk animations | `assgen gen visual animate keyframe --input rigged.glb --prompt "looping idle, breathing" --wait` |
| Extract pose from reference video | `assgen gen visual animate mocap --input reference.mp4 --wait` |

**Pain points**
- Auto-rig quality varies by mesh complexity; needs clear error output when a mesh is
  too complex for UniRig so she knows to simplify it in Blender first
- Text-to-3D struggles with bipedal characters — image-to-3D from a concept sheet
  is almost always better; the default should prefer `--input` over `--prompt` when
  the job type is `visual.model.create`
- Animation BVH export format must be specified; Unity uses Humanoid rig conventions

**Acceptance criteria for assgen**
- A rig + basic animation set in under 20 minutes for a human-proportioned character
- `assgen gen visual rig auto` gives a clear error (not a 500) when the mesh has holes

**Known gap**: text-to-motion (generating BVH/FBX motion data from a text description like
"character throws a punch") has no open, ungated HuggingFace model as of 2026-03.
The `visual.animate.keyframe` entry (AnimateDiff) generates a video preview, not
retargetable motion data.  Tracked as a future catalog entry.

---

## Persona 4 — Sam, the Game Audio Designer

> *"Every sound should feel hand-crafted.  I just need to prototype 10× faster."*

**Background**  
Sam is an audio designer at a mid-size studio (30 people) shipping a sci-fi shooter.
They are the sole audio designer and need to produce hundreds of SFX variants,
adaptive music stems, ambient loops, and VO scratch tracks.

**Project**: a sci-fi shooter with a reactive music system and full VO cast.

**Primary assgen workflows**

| Step | Command |
|---|---|
| Generate a laser SFX variant | `assgen gen audio sfx generate --prompt "plasma rifle shot, sci-fi, sharp crack" --wait` |
| Compose a combat music loop | `assgen gen audio music loop --prompt "tense sci-fi combat, electronic drums, 120bpm" --wait` |
| Generate ambient space station hum | `assgen gen audio ambient generate --prompt "deep space station ambience, low hum, metallic resonance" --wait` |
| Record scratch VO for a villain | `assgen gen audio voice tts "Your species ends today." --voice villain --wait` |
| Clone a director's voice for ADR | `assgen gen audio voice clone --input reference.wav --text "We need to retreat now." --wait` |

**Pain points**
- SFX clips are often too short (< 2 seconds) — needs `--duration` flag support
- Adaptive music stems need to be at the same BPM and key for runtime blending
- Voice clone quality is acceptable for scratch tracks but not final VO — that is fine, just needs
  to be clearly communicated in `--help`

**Acceptance criteria for assgen**
- Can generate 20 SFX variants for a weapon in under an hour  
- Music loops are seamless at the loop point (no audible click)
- `--wait` streams audio waveform progress, not just a spinner

**Known gap**: `audio.ambient.generate` is currently backed by `facebook/musicgen-stereo-large`
with an ambient-focused prompt.  A dedicated ambient/soundscape model (like stable-audio-open-1.0)
would be better but requires an HF token (gated=auto).  Will revisit when stable-audio-open
goes fully public.

---

## Persona 5 — Casey, the Technical Artist / Pipeline TD

> *"I turn art into game-ready assets automatically.  If I have to touch it, it's broken."*

**Background**  
Casey is a technical artist at a large studio (100+ people) responsible for the asset pipeline:
automated import, validation, LOD generation, lightmap baking, and CI integration.
They run assgen as part of their CI/CD system (GitHub Actions), not interactively.

**Project**: automating a Unity asset pipeline for a live-service mobile game.

**Primary assgen workflows**

```bash
# In CI — validate every asset in a PR
assgen qa validate assets/ --checks normals,uvs,manifold --strict

# Generate NPC dialogue for a quest (LLM)
assgen gen support narrative dialog "grizzled blacksmith" \
    --context "player has just saved the village" \
    --lines 8 --branching

# Auto-generate lore for a new region
assgen gen support narrative lore "The Ashfield Wastes" \
    --format codex --length 400

# Export all assets in a directory to Unreal-compatible format
assgen gen pipeline integrate export --input assets/ --engine unreal --wait
```

**Pain points**
- The server must be configurable via environment variables for CI use (`ASSGEN_SERVER_URL`,
  `ASSGEN_DEVICE`) — no interactive prompts
- Needs machine-readable output (`--json` flag) for downstream parsing in CI scripts
- The allow_list in server.yaml is essential: Casey can't have developers downloading
  arbitrary multi-GB models in CI

**Acceptance criteria for assgen**
- Every command exits with code 0 (success) or non-zero (failure) — no ambiguous output
- `--json` flag on all commands produces structured output parseable by `jq`
- Server allow_list blocks unapproved models and logs a clear reason in JSON

**Known gap**: `--json` output flag is not yet implemented on the client.  This is the
single highest-priority feature for Casey's use case.

---

## What the personas tell us

### Covered well
- 3D mesh generation from image or text (`visual.model.create`)
- Auto-rigging (`visual.rig.auto`)
- Music loops and adaptive stems (`audio.music.*`)
- TTS and voice cloning (`audio.voice.*`)
- Basic SFX (`audio.sfx.generate`)
- Concept art generation (`visual.concept.*`)
- Asset validation (`qa.validate`)

### Known gaps (tracked, no good open HF model yet)
| Gap | Blocker |
|---|---|
| Text-to-motion (BVH/FBX retargetable) | No ungated open model on HF as of 2026-03 |
| Automatic LOD generation | Algorithmic — no ML equivalent yet |
| Seamless texture diffusion | FLUX-based options exist but FLUX.1-dev is gated |
| Texture super-resolution | Real-ESRGAN weights exist but no HF pipeline_tag |

### Future catalog entries (model exists, not yet added)
| Task | Model | Why not yet |
|---|---|---|
| `visual.texture.inpaint` | `diffusers/stable-diffusion-xl-1.0-inpainting-0.1` | Needs to be added |
| `narrative.dialogue.npc` | `microsoft/Phi-3.5-mini-instruct` | `support` command maps to wrong job type |
| `narrative.lore.generate` | `microsoft/Phi-3.5-mini-instruct` | Same |
| `audio.ambient.generate` | `facebook/musicgen-stereo-large` | Not differentiated from adaptive |
| `scene.depth.estimate` | `Intel/dpt-large` | Not in catalog |

### Feature requests implied by personas
- `--json` flag on all client commands (Casey)
- `--duration` flag on audio commands (Sam)
- `--format` / `--engine` flag on export (Casey)
- Clearer error messages when a model rejects a mesh (Maya)
