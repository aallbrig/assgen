# Compose Pipelines

Compose commands run a **complete, multi-step generation pipeline** from a single
prompt. Every step waits for the previous one to finish and passes its output
files into the next step as context — no manual job chaining, no copying IDs,
no intermediate bookkeeping.

The cost equals the sum of the individual steps. There is no overhead.

---

## When to use compose vs gen

| Scenario | Use |
|---|---|
| You want a complete game-ready asset in one command | `compose` |
| You want to tweak one specific step interactively | `assgen gen ...` |
| You want to reuse an existing mesh from disk | `assgen gen ...` with `--input` |
| You want to script asset batch generation | `compose ... --wait` in a loop |
| You want to see exactly what would run | `compose ... --dry-run` |

---

## Common flags

All compose commands accept:

| Flag | Description |
|---|---|
| `--wait` | Block until the pipeline completes and print a results table |
| `--dry-run` | Print the full step plan without submitting any jobs |
| `--quality {low,medium,high}` | Scale mesh complexity and texture resolution |
| `--engine {unity,unreal,godot}` | Export folder structure for the final step |

---

## assgen compose npc

Generate a complete game NPC: concept art → multi-view images → 3D mesh → UV →
PBR texture → rig → animations → LOD levels → collision → voice lines → export.

```bash
# Pig shopkeeper for a medieval fantasy game
assgen compose npc "pig shopkeeper with apron, medieval fantasy" --wait

# Dark elf archer — Unreal Engine, high quality
assgen compose npc "dark elf archer, gritty realistic" \
    --style "gritty realistic" --engine unreal --quality high --wait

# Quick prototype — skip multiview and LODs
assgen compose npc "robot guard" --no-multiview --no-lod --wait

# Preview the 12-step chain before committing
assgen compose npc "wizard sage" --dry-run
```

**Key flags:** `--style`, `--voice`, `--no-multiview`, `--no-lod`, `--no-collider`

---

## assgen compose weapon

Generate a complete weapon asset: concept art → mesh → UV unwrap →
concept-guided texture → LOD levels → collision mesh → export.

```bash
assgen compose weapon "rusted iron longsword, dark fantasy" --wait
assgen compose weapon "plasma rifle" --style "sci-fi, chrome" --engine unreal --wait
assgen compose weapon "elven bow, silver filigree" --quality high --wait
```

---

## assgen compose prop

Generate a static game prop — furniture, containers, decorations, foliage, or
structural elements. Ideal for high-volume prop production.

```
concept art → mesh → UV unwrap → concept-guided texture → LOD levels
→ collision mesh → engine export
```

```bash
# Barrel for a medieval dungeon (Godot)
assgen compose prop "wooden barrel with iron bands, medieval" \
    --engine godot --wait

# Quick low-poly decoration
assgen compose prop "stone pillar, dungeon" \
    --type decoration --quality low --wait

# Ornate chest — preview first
assgen compose prop "ornate treasure chest, gold trim" --dry-run

# Hanging lantern
assgen compose prop "oil lantern, hanging, warm glow" --wait
```

**Flags:**
- `--type {furniture,container,decoration,foliage,structure}` — steers the concept prompt
- `--quality {low,medium,high}` — mesh and texture fidelity

!!! tip "High-volume prop generation"
    Run several props in parallel by submitting without `--wait`, then
    monitor with `assgen jobs list`:
    ```bash
    assgen compose prop "barrel" --engine godot
    assgen compose prop "crate" --engine godot
    assgen compose prop "torch bracket" --engine godot
    assgen jobs list
    ```

---

## assgen compose material

Generate a full PBR material set from a text description.

```
albedo texture → seamless tiling → normal map → PBR channels
(roughness / AO / metallic) → optional upscale → export
```

Output files: `albedo.png`, `normal.png`, `roughness.png`, `ao.png`, `metallic.png`

```bash
# Cobblestone ground material
assgen compose material "weathered cobblestone, mossy, medieval" --wait

# High-res rusted metal with upscaling
assgen compose material "rusted iron sheet, factory floor" \
    --resolution 2048 --upscale --wait

# Wood for Godot
assgen compose material "worn oak planks, aged" \
    --type wood --engine godot --wait

# Organic skin material
assgen compose material "dragon scale, iridescent, reptilian" \
    --type organic --quality high --wait
```

**Flags:**
- `--resolution {512,1024,2048,4096}` — texture dimensions (default: 1024)
- `--upscale / --no-upscale` — apply Real-ESRGAN 2× pass after generation
- `--type {organic,metal,stone,wood,fabric}` — prompt augmentation hint

!!! note "Import into Godot"
    Drag all five PNGs into `res://assets/materials/`.  In the **StandardMaterial3D**
    inspector, assign each channel:

    | Channel | File |
    |---|---|
    | Albedo | `albedo.png` |
    | Normal Map | `normal.png` |
    | Roughness | `roughness.png` |
    | Ambient Occlusion | `ao.png` |
    | Metallic | `metallic.png` |

---

## assgen compose soundscape

Generate a complete audio suite for a game level or biome: ambient loop +
theme music + a set of themed sound effects, all in one command.

```
ambient loop → theme music → loopable music → N themed SFX
→ loop optimization → export
```

```bash
# Enchanted forest at night (5 SFX)
assgen compose soundscape "enchanted forest at night" --wait

# Busy tavern with explicit SFX list
assgen compose soundscape "medieval tavern, busy crowd" \
    --sfx-list "coin clink,wooden chair scrape,fire crackle,mug slam,door creak" \
    --wait

# Dungeon — ambient + SFX only, no music
assgen compose soundscape "dungeon corridor, dripping water" \
    --no-music --sfx-count 8 --wait

# Long ambient loop for an open world region
assgen compose soundscape "volcanic crater, rumbling" \
    --duration 60 --sfx-count 4 --wait
```

**Flags:**
- `--sfx-count N` — number of SFX to generate (default: 5)
- `--sfx-list "a,b,c"` — explicit SFX prompts (overrides `--sfx-count`)
- `--no-music` — skip music, generate ambient loop + SFX only
- `--duration N` — audio length in seconds (default: 30)

!!! tip "Loop import in Godot"
    For ambient loops and music: in the **Import** dock set **Loop Mode → Forward**
    and click **Reimport** before adding the stream to an `AudioStreamPlayer`.

---

## assgen compose ui-kit

Generate a cohesive UI element set for a game. All elements share a common
style reference generated in the first step.

```
style reference → button states (normal/hover/pressed) → dialog panel
→ N icons → widget elements (slider, progress bar) → export
```

```bash
# Dark fantasy RPG UI
assgen compose ui-kit "dark fantasy RPG" --wait

# Sci-fi HUD with custom icons
assgen compose ui-kit "sci-fi HUD, blue holographic glow" \
    --icons "health,shield,ammo,radar,objective" --wait

# Cozy farming game with warm palette
assgen compose ui-kit "cozy farming game, warm" \
    --palette "warm earthy tones, hand-drawn style" --wait

# Preview the step plan
assgen compose ui-kit "horror survival" --dry-run
```

**Flags:**
- `--icons "a,b,c"` — comma-separated icon names (default: health, mana, stamina, gold, sword, shield)
- `--palette "description"` — color palette hint prepended to every step's prompt

---

## assgen compose environment

Generate a full level environment kit: multiple props sharing a common style,
a ground material, and ambient audio — all in a single command.

```
style reference → N × (concept → mesh → UV → texture → LOD → collider)
→ ground material (albedo → seamless → normal → PBR)
→ ambient loop + theme music → batch export
```

This is the highest-level compose command and the most powerful value multiplier:
a 6-prop environment runs **26 sequential steps** and would otherwise require
dozens of manual commands.

```bash
# Medieval tavern interior — 6 props, Godot export
assgen compose environment "medieval tavern interior" \
    --count 6 --engine godot --wait

# Sci-fi corridor kit — 4 props, Unreal
assgen compose environment "sci-fi maintenance corridor" \
    --count 4 --engine unreal --wait

# Explicit item list
assgen compose environment "haunted forest clearing" \
    --items "dead tree,moss-covered gravestone,iron fence,broken lantern,fog machine" \
    --wait

# Skip audio and ground (props only)
assgen compose environment "crystal cave" \
    --count 5 --no-audio --no-ground --wait

# Always preview first — 26 steps is a lot to cancel mid-way
assgen compose environment "medieval tavern" --count 6 --dry-run
```

**Flags:**
- `--count N` — number of props to generate (default: 6)
- `--items "a,b,c"` — explicit prop list (overrides `--count`)
- `--no-audio` — skip ambient loop and music
- `--no-ground` — skip ground material set
- `--quality {low,medium,high}` — applied to every prop step

!!! warning "Runtime expectations"
    With 6 props + ground + audio you are running 26 ML inference steps
    back-to-back.  On an RTX 3060:

    | Props | Steps | Approx. time |
    |---|---|---|
    | 3 | 14 | ~25 min |
    | 6 | 26 | ~50 min |
    | 6 + `--quality low` | 26 | ~20 min |

    Use `--quality low` for rapid prototyping and upgrade individual props
    with `assgen gen` commands once you've confirmed the kit direction.

---

## Dry-run: preview before committing

Every compose command supports `--dry-run`. It prints the full step table —
step ID, job type, upstream dependency, and parameters — without submitting anything.

```bash
assgen compose environment "desert ruins" --count 4 --dry-run
```

```
Environment pipeline  (20 steps, dry-run)

  style_ref       visual.concept.generate   {'prompt': 'desert ruins, environment ...'}
  prop0_concept   visual.concept.generate   {'prompt': 'desert ruins prop 1, ...'}
  prop0_mesh      visual.model.splat        ← from 'prop0_concept'
  ...
```

Use dry-run to:
- Verify the step count before a long run
- Check that your `--items` list generates the right prompts
- Share the pipeline plan with a teammate before burning GPU time

---

## Checking progress on a running pipeline

```bash
# All recent jobs
assgen jobs list

# Detailed status for a specific job
assgen jobs status <job-id>

# Full info including the original prompt, in YAML
assgen jobs status <job-id> --yaml
```

The `--yaml` output shows the exact prompt, parameters, and CLI command used
to submit the job — useful for reproducing or tweaking a prior run.
