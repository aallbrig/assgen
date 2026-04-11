"""assgen compose — multi-step asset pipeline commands.

Compose commands run a complete, multi-step generation pipeline from a single
command. Each step waits for the previous to complete and passes its output
files into the next step as upstream context — no manual job chaining required.

Available compose pipelines:

  assgen compose npc          Full NPC creation: concept → mesh → rig → animate → texture → export
  assgen compose weapon        Weapon asset: concept → mesh → LOD → texture → collider → export
  assgen compose prop          Static prop: concept → mesh → UV → texture → LOD → collider → export
  assgen compose material      PBR texture set: generate → seamless → normalmap → pbr → export
  assgen compose soundscape    Level audio: ambient → music → SFX × N → export
  assgen compose ui-kit        Themed UI set: style ref → buttons → panels → icons → export
  assgen compose environment   Themed level kit: N props + ground material + ambient audio → export

The cost of a compose command equals the sum of its individual steps — there is
no additional inference overhead beyond what you would run manually.
"""
from __future__ import annotations

import typer

from assgen.client.output import console

app = typer.Typer(
    help="Multi-step asset pipeline commands (NPC, weapon, prop, material, soundscape, …).",
    no_args_is_help=True,
)

_ENGINE_OPT = typer.Option("unity", "--engine", help="unity | unreal | godot")
_WAIT_OPT   = typer.Option(True,  "--wait/--no-wait",
                            help="Block until the full pipeline completes (default: on)")
_OUT_OPT    = typer.Option(None, "--output", "-o", help="Output directory")
_QUALITY_OPT = typer.Option("standard", "--quality", "-q", help="draft | standard | high")


# ── NPC ──────────────────────────────────────────────────────────────────────

@app.command("npc")
def compose_npc(
    prompt: str = typer.Argument(
        ...,
        help="Character description, e.g. 'pig shopkeeper with apron, medieval fantasy'",
    ),
    style: str | None = typer.Option(
        None, "--style",
        help="Visual style applied to all generation steps, e.g. 'painterly, warm tones'",
    ),
    voice: str | None = typer.Option(
        None, "--voice",
        help="TTS voice description for NPC dialog lines, e.g. 'gruff male merchant, aged'",
    ),
    animations: str = typer.Option(
        "idle,walk,talk",
        "--animations", "-a",
        help="Comma-separated animation clips to retarget onto the character",
    ),
    skeleton: str = typer.Option(
        "humanoid", "--skeleton",
        help="biped | humanoid (humanoid = Unity-compatible 55-bone naming)",
    ),
    engine: str = _ENGINE_OPT,
    lod: bool = typer.Option(True,  "--lod/--no-lod",     help="Generate LOD 0/1/2 levels"),
    collider: bool = typer.Option(True, "--collider/--no-collider", help="Generate collision mesh"),
    multiview: bool = typer.Option(
        True, "--multiview/--no-multiview",
        help="Use Zero123++ multi-view for better mesh quality (slower)",
    ),
    quality: str = _QUALITY_OPT,
    output: str | None = _OUT_OPT,
    wait: bool = _WAIT_OPT,
    dry_run: bool = typer.Option(False, "--dry-run", help="Print pipeline steps without executing"),
) -> None:
    """Generate a complete game NPC from a text description.

    Runs a multi-step pipeline:
      1. Concept art (SDXL)
      2. Multi-view turnaround (Zero123++)  [--no-multiview to skip]
      3. 3D mesh reconstruction (TripoSR)
      4. UV unwrap
      5. Concept-guided texture generation (IP-Adapter)
      6. Auto-rig with humanoid skeleton (UniRig)
      7. Animation retargeting (bundled BVH clips)
      8. LOD levels 0/1/2  [--no-lod to skip]
      9. Collision mesh    [--no-collider to skip]
      10. NPC dialog text generation
      11. Text-to-speech for dialog lines
      12. Engine export

    Examples:
        assgen compose npc "pig shopkeeper with apron, medieval fantasy" --wait
        assgen compose npc "dark elf archer" --style "gritty realistic" --engine unreal --wait
        assgen compose npc "robot guard" --no-multiview --animations idle,walk,attack_light --wait
    """
    style_tag = f", {style}" if style else ""
    full_prompt = f"{prompt}{style_tag}"
    anim_list = [a.strip() for a in animations.split(",") if a.strip()]
    global_params = {"_quality": quality} if quality != "standard" else {}
    if output:
        global_params["output_dir"] = output

    steps: list[dict] = [
        {
            "id": "concept",
            "job_type": "visual.concept.generate",
            "params": {
                "prompt": f"{full_prompt}, character concept art, front view, full body, white background",
                "width": 768, "height": 1024,
            },
        },
    ]

    if multiview:
        steps.append({
            "id": "multiview",
            "job_type": "visual.model.multiview",
            "from_step": "concept",
            "params": {"prompt": full_prompt},
        })
        mesh_from = "multiview"
    else:
        mesh_from = "concept"

    steps += [
        {
            "id": "mesh",
            "job_type": "visual.model.splat",
            "from_step": mesh_from,
            "params": {"prompt": full_prompt},
        },
        {
            "id": "uv",
            "job_type": "visual.uv.auto",
            "from_step": "mesh",
        },
        {
            "id": "texture",
            "job_type": "visual.texture.from_concept",
            "from_step": "uv",
            "params": {
                "prompt": full_prompt,
                "concept_step": "concept",  # hint to handler to look for concept image
            },
        },
        {
            "id": "rig",
            "job_type": "visual.rig.auto",
            "from_step": "mesh",
            "params": {"skeleton": skeleton},
        },
        {
            "id": "animations",
            "job_type": "visual.animate.retarget",
            "from_step": "rig",
            "params": {"clips": anim_list, "skeleton": skeleton},
        },
    ]

    if lod:
        steps.append({
            "id": "lod",
            "job_type": "visual.lod.generate",
            "from_step": "mesh",
            "params": {"levels": 3},
        })

    if collider:
        steps.append({
            "id": "collider",
            "job_type": "scene.physics.collider",
            "from_step": "mesh",
        })

    dialog_prompt = voice or f"{prompt}, NPC merchant greeting the player"
    steps += [
        {
            "id": "dialog",
            "job_type": "narrative.dialogue.npc",
            "params": {
                "prompt": dialog_prompt,
                "character": prompt,
                "line_count": 5,
            },
        },
        {
            "id": "voice",
            "job_type": "audio.voice.tts",
            "from_step": "dialog",
            "params": {"voice": voice or "en_default"},
        },
        {
            "id": "export",
            "job_type": "pipeline.integrate.export",
            "from_step": "mesh",
            "params": {"engine": engine},
        },
    ]

    _execute_or_dry_run(steps, global_params, dry_run, wait, pipeline_name="NPC")


# ── Weapon ───────────────────────────────────────────────────────────────────

@app.command("weapon")
def compose_weapon(
    prompt: str = typer.Argument(..., help="Weapon description, e.g. 'rusted iron longsword'"),
    style: str | None = typer.Option(None, "--style"),
    engine: str = _ENGINE_OPT,
    lod: bool = typer.Option(True,  "--lod/--no-lod"),
    collider: bool = typer.Option(True, "--collider/--no-collider"),
    quality: str = _QUALITY_OPT,
    output: str | None = _OUT_OPT,
    wait: bool = _WAIT_OPT,
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Generate a complete weapon asset: concept → mesh → LOD → texture → collider → export.

    Examples:
        assgen compose weapon "rusted iron longsword, dark fantasy" --wait
        assgen compose weapon "plasma rifle" --style "sci-fi, chrome" --engine unreal --wait
    """
    style_tag = f", {style}" if style else ""
    full_prompt = f"{prompt}{style_tag}"
    global_params = {"_quality": quality} if quality != "standard" else {}

    steps: list[dict] = [
        {
            "id": "concept",
            "job_type": "visual.concept.generate",
            "params": {
                "prompt": f"{full_prompt}, weapon concept art, isolated on white, side view",
                "width": 1024, "height": 512,
            },
        },
        {
            "id": "mesh",
            "job_type": "visual.model.splat",
            "from_step": "concept",
            "params": {"prompt": full_prompt},
        },
        {
            "id": "uv",
            "job_type": "visual.uv.auto",
            "from_step": "mesh",
        },
        {
            "id": "texture",
            "job_type": "visual.texture.from_concept",
            "from_step": "uv",
            "params": {"prompt": full_prompt},
        },
    ]

    if lod:
        steps.append({"id": "lod", "job_type": "visual.lod.generate",
                       "from_step": "mesh", "params": {"levels": 3}})
    if collider:
        steps.append({"id": "collider", "job_type": "scene.physics.collider",
                       "from_step": "mesh"})

    steps.append({"id": "export", "job_type": "pipeline.integrate.export",
                   "from_step": "mesh", "params": {"engine": engine}})

    _execute_or_dry_run(steps, global_params, dry_run, wait, pipeline_name="Weapon")


# ── Prop ─────────────────────────────────────────────────────────────────────

@app.command("prop")
def compose_prop(
    prompt: str = typer.Argument(
        ...,
        help="Prop description, e.g. 'wooden barrel with iron bands, medieval'",
    ),
    style: str | None = typer.Option(None, "--style",
        help="Visual style, e.g. 'low poly, flat shading'"),
    prop_type: str = typer.Option(
        "prop", "--type",
        help="furniture | container | decoration | foliage | structure | prop",
    ),
    engine: str = _ENGINE_OPT,
    lod: bool = typer.Option(True,  "--lod/--no-lod", help="Generate LOD 0/1/2 levels"),
    collider: bool = typer.Option(True, "--collider/--no-collider", help="Generate collision mesh"),
    quality: str = _QUALITY_OPT,
    output: str | None = _OUT_OPT,
    wait: bool = _WAIT_OPT,
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Generate a static game prop from a text description.

    Runs a 7-step pipeline:
      1. Concept art (SDXL)
      2. 3D mesh reconstruction (TripoSR)
      3. UV unwrap
      4. Concept-guided texture (IP-Adapter)
      5. LOD levels 0/1/2   [--no-lod to skip]
      6. Collision mesh      [--no-collider to skip]
      7. Engine export

    Examples:
        assgen compose prop "wooden barrel with iron bands, medieval" --engine godot --wait
        assgen compose prop "sci-fi crate with glowing vents" --type container --quality high --wait
        assgen compose prop "ornate stone fountain" --type decoration --style "low poly" --wait
    """
    style_tag = f", {style}" if style else ""
    type_hints = {
        "furniture": "furniture piece, game asset, isolated on white",
        "container": "container/crate/barrel, game asset, isolated on white",
        "decoration": "decorative prop, game asset, isolated on white",
        "foliage": "plant/foliage, game asset, isolated on white",
        "structure": "structural piece, game asset, isolated on white",
        "prop": "game prop, isolated on white, front view",
    }
    type_hint = type_hints.get(prop_type, type_hints["prop"])
    full_prompt = f"{prompt}{style_tag}"
    concept_prompt = f"{full_prompt}, {type_hint}"

    global_params = {"_quality": quality} if quality != "standard" else {}
    if output:
        global_params["output_dir"] = output

    steps: list[dict] = [
        {
            "id": "concept",
            "job_type": "visual.concept.generate",
            "params": {"prompt": concept_prompt, "width": 1024, "height": 1024},
        },
        {
            "id": "mesh",
            "job_type": "visual.model.splat",
            "from_step": "concept",
            "params": {"prompt": full_prompt},
        },
        {
            "id": "uv",
            "job_type": "visual.uv.auto",
            "from_step": "mesh",
        },
        {
            "id": "texture",
            "job_type": "visual.texture.from_concept",
            "from_step": "uv",
            "params": {"prompt": full_prompt},
        },
    ]

    if lod:
        steps.append({"id": "lod", "job_type": "visual.lod.generate",
                       "from_step": "mesh", "params": {"levels": 3}})
    if collider:
        steps.append({"id": "collider", "job_type": "scene.physics.collider",
                       "from_step": "mesh"})

    steps.append({"id": "export", "job_type": "pipeline.integrate.export",
                   "from_step": "mesh", "params": {"engine": engine}})

    _execute_or_dry_run(steps, global_params, dry_run, wait, pipeline_name="Prop")


# ── Material ─────────────────────────────────────────────────────────────────

@app.command("material")
def compose_material(
    prompt: str = typer.Argument(
        ...,
        help="Surface description, e.g. 'weathered cobblestone, mossy'",
    ),
    style: str | None = typer.Option(None, "--style"),
    mat_type: str = typer.Option(
        "surface", "--type",
        help="stone | wood | metal | fabric | organic | surface",
    ),
    resolution: int = typer.Option(
        1024, "--resolution", "-r",
        help="Output texture resolution in pixels (512 | 1024 | 2048 | 4096)",
    ),
    upscale: bool = typer.Option(
        False, "--upscale/--no-upscale",
        help="Run a 2× Real-ESRGAN upscale pass for crisper detail",
    ),
    engine: str = _ENGINE_OPT,
    quality: str = _QUALITY_OPT,
    output: str | None = _OUT_OPT,
    wait: bool = _WAIT_OPT,
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Generate a full PBR material set from a text description.

    Runs a 5-6 step pipeline:
      1. Albedo texture (SDXL)
      2. Make seamless/tileable (algorithmic)
      3. Normal map derivation (algorithmic)
      4. PBR channel generation — roughness / AO / metallic (algorithmic)
      5. 2× upscale (Real-ESRGAN)  [--upscale to enable]
      6. Engine material folder export

    Output files: albedo.png, normal.png, roughness.png, ao.png, metallic.png

    Examples:
        assgen compose material "weathered cobblestone, mossy" --engine godot --wait
        assgen compose material "rusted metal plate" --type metal --resolution 2048 --wait
        assgen compose material "dark oak wood planks" --type wood --upscale --wait
    """
    style_tag = f", {style}" if style else ""
    type_hints = {
        "stone":   "stone surface material, seamless texture, top-down view",
        "wood":    "wood grain surface, seamless texture, top-down view",
        "metal":   "metal surface material, seamless texture, top-down view",
        "fabric":  "fabric/cloth surface, seamless texture, top-down view",
        "organic": "organic surface material, seamless texture, top-down view",
        "surface": "surface material, seamless texture, top-down view",
    }
    type_hint = type_hints.get(mat_type, type_hints["surface"])
    full_prompt = f"{prompt}{style_tag}"
    albedo_prompt = f"{full_prompt}, {type_hint}"

    global_params = {"_quality": quality} if quality != "standard" else {}
    if output:
        global_params["output_dir"] = output

    steps: list[dict] = [
        {
            "id": "albedo",
            "job_type": "visual.texture.generate",
            "params": {
                "prompt": albedo_prompt,
                "width": resolution, "height": resolution,
            },
        },
        {
            "id": "seamless",
            "job_type": "visual.texture.seamless",
            "from_step": "albedo",
        },
        {
            "id": "normalmap",
            "job_type": "visual.texture.normalmap_convert",
            "from_step": "seamless",
        },
        {
            "id": "pbr",
            "job_type": "visual.texture.pbr",
            "from_step": "seamless",
            "params": {"prompt": full_prompt},
        },
    ]

    if upscale:
        steps.append({
            "id": "upscale",
            "job_type": "visual.texture.upscale",
            "from_step": "seamless",
            "params": {"scale": 2},
        })

    steps.append({
        "id": "export",
        "job_type": "pipeline.integrate.export",
        "from_step": "pbr",
        "params": {"engine": engine, "asset_type": "material"},
    })

    _execute_or_dry_run(steps, global_params, dry_run, wait, pipeline_name="Material")


# ── Soundscape ───────────────────────────────────────────────────────────────

@app.command("soundscape")
def compose_soundscape(
    prompt: str = typer.Argument(
        ...,
        help="Environment/mood description, e.g. 'enchanted forest at night'",
    ),
    sfx_count: int = typer.Option(
        5, "--sfx-count",
        help="Number of SFX clips to generate",
    ),
    sfx_list: str | None = typer.Option(
        None, "--sfx-list",
        help="Comma-separated explicit SFX prompts, e.g. 'footstep on dirt,wind,door creak'",
    ),
    duration: int = typer.Option(
        30, "--duration",
        help="Length of ambient/music clips in seconds",
    ),
    music: bool = typer.Option(True, "--music/--no-music",
        help="Generate theme music in addition to ambient"),
    quality: str = _QUALITY_OPT,
    output: str | None = _OUT_OPT,
    wait: bool = _WAIT_OPT,
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Generate a complete audio suite for a game level or biome.

    Runs a 4-6 step pipeline:
      1. Ambient loop (MusicGen-stereo)
      2. Theme music (MusicGen-large)  [--no-music to skip]
      3. Loopable music variant (MusicGen-stereo-medium)  [--no-music to skip]
      4. SFX clips × N (AudioGen)
      5. Loop optimisation (algorithmic)
      6. Audio folder export

    Examples:
        assgen compose soundscape "enchanted forest at night" --wait
        assgen compose soundscape "medieval tavern" --sfx-list "mug clinking,fire crackling,crowd murmur" --wait
        assgen compose soundscape "space station interior" --no-music --sfx-count 8 --wait
    """
    global_params = {"_quality": quality} if quality != "standard" else {}
    if output:
        global_params["output_dir"] = output

    # Build SFX prompts — explicit list or auto-derived from environment prompt
    if sfx_list:
        sfx_prompts = [s.strip() for s in sfx_list.split(",") if s.strip()]
    else:
        sfx_prompts = [f"{prompt} sound effect {i+1}" for i in range(sfx_count)]

    steps: list[dict] = [
        {
            "id": "ambient",
            "job_type": "audio.ambient.generate",
            "params": {
                "prompt": f"{prompt}, ambient background loop, loopable",
                "duration": duration,
            },
        },
    ]

    if music:
        steps += [
            {
                "id": "music",
                "job_type": "audio.music.compose",
                "params": {
                    "prompt": f"{prompt}, game level theme music",
                    "duration": duration,
                },
            },
            {
                "id": "music_loop",
                "job_type": "audio.music.loop",
                "from_step": "music",
                "params": {"duration": duration},
            },
        ]

    for i, sfx_prompt in enumerate(sfx_prompts):
        steps.append({
            "id": f"sfx_{i}",
            "job_type": "audio.sfx.generate",
            "params": {"prompt": sfx_prompt, "duration": min(duration, 10)},
        })

    steps += [
        {
            "id": "optimize",
            "job_type": "audio.process.loop_optimize",
            "from_step": "ambient",
            "params": {"target_duration": duration},
        },
        {
            "id": "export",
            "job_type": "pipeline.integrate.export",
            "from_step": "ambient",
            "params": {"asset_type": "audio"},
        },
    ]

    _execute_or_dry_run(steps, global_params, dry_run, wait, pipeline_name="Soundscape")


# ── UI Kit ───────────────────────────────────────────────────────────────────

@app.command("ui-kit")
def compose_ui_kit(
    prompt: str = typer.Argument(
        ...,
        help="Visual style description, e.g. 'dark fantasy RPG'",
    ),
    icons: str = typer.Option(
        "health,mana,stamina,gold,attack,defense",
        "--icons",
        help="Comma-separated icon names to generate",
    ),
    palette: str | None = typer.Option(
        None, "--palette",
        help="Colour palette hint, e.g. 'dark tones, gold accents'",
    ),
    engine: str = _ENGINE_OPT,
    quality: str = _QUALITY_OPT,
    output: str | None = _OUT_OPT,
    wait: bool = _WAIT_OPT,
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Generate a cohesive UI element set for a game.

    Runs a 5-8 step pipeline:
      1. Style reference sheet (SDXL) — establishes visual identity
      2. Button states — normal, hover, pressed (SDXL)
      3. Panel/dialog background (SDXL)
      4. Icon set × N (SDXL) — one per icon name
      5. Widget elements — slider, progress bar (SDXL)
      6. Engine UI folder export

    All elements share the same style prompt for visual consistency.

    Examples:
        assgen compose ui-kit "dark fantasy RPG" --wait
        assgen compose ui-kit "cute cartoon mobile game" --icons "heart,star,coin,gem" --engine unity --wait
        assgen compose ui-kit "minimal sci-fi HUD" --palette "cyan, dark navy" --wait
    """
    palette_tag = f", {palette}" if palette else ""
    style_prompt = f"{prompt}{palette_tag}, game UI design, flat design"

    global_params = {"_quality": quality} if quality != "standard" else {}
    if output:
        global_params["output_dir"] = output

    icon_list = [ic.strip() for ic in icons.split(",") if ic.strip()]

    steps: list[dict] = [
        {
            "id": "style_ref",
            "job_type": "visual.concept.generate",
            "params": {
                "prompt": f"{style_prompt}, UI style reference sheet, multiple elements",
                "width": 1024, "height": 1024,
            },
        },
        {
            "id": "button",
            "job_type": "visual.ui.button",
            "params": {
                "prompt": f"{style_prompt}, UI button, game interface element",
                "states": ["normal", "hover", "pressed"],
            },
        },
        {
            "id": "panel",
            "job_type": "visual.ui.panel",
            "params": {
                "prompt": f"{style_prompt}, dialog/inventory panel background, game UI",
            },
        },
    ]

    for _i, icon_name in enumerate(icon_list):
        steps.append({
            "id": f"icon_{icon_name}",
            "job_type": "visual.ui.icon",
            "params": {
                "prompt": f"{icon_name} icon, {style_prompt}",
                "size": 128,
            },
        })

    steps += [
        {
            "id": "widget",
            "job_type": "visual.ui.widget",
            "params": {
                "prompt": f"{style_prompt}, UI widget elements, slider and progress bar",
            },
        },
        {
            "id": "export",
            "job_type": "pipeline.integrate.export",
            "from_step": "style_ref",
            "params": {"engine": engine, "asset_type": "ui"},
        },
    ]

    _execute_or_dry_run(steps, global_params, dry_run, wait, pipeline_name="UI Kit")


# ── Environment ───────────────────────────────────────────────────────────────

@app.command("environment")
def compose_environment(
    prompt: str = typer.Argument(
        ...,
        help="Environment theme, e.g. 'medieval tavern interior'",
    ),
    count: int = typer.Option(
        6, "--count", "-n",
        help="Number of props to generate",
    ),
    items: str | None = typer.Option(
        None, "--items",
        help="Explicit comma-separated prop list, e.g. 'barrel,chair,table,torch'  (overrides --count)",
    ),
    style: str | None = typer.Option(None, "--style"),
    engine: str = _ENGINE_OPT,
    audio: bool = typer.Option(True, "--audio/--no-audio",
        help="Generate ambient audio and theme music"),
    ground: bool = typer.Option(True, "--ground/--no-ground",
        help="Generate a tiling ground/floor material"),
    quality: str = _QUALITY_OPT,
    output: str | None = _OUT_OPT,
    wait: bool = _WAIT_OPT,
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Generate a cohesive level environment kit from a theme description.

    Produces a batch of themed props, an optional ground material, and
    optional ambient audio — all sharing the same visual identity.

    Runs a multi-phase pipeline:
      Phase 1 — Style reference (1× concept generate)
      Phase 2 — Props: for each prop: concept → mesh → UV → texture → LOD → collider
      Phase 3 — Ground material: texture → seamless → normalmap → PBR  [--no-ground to skip]
      Phase 4 — Audio: ambient loop + theme music  [--no-audio to skip]
      Phase 5 — Batch export

    Examples:
        assgen compose environment "medieval tavern interior" --count 8 --engine godot --wait
        assgen compose environment "sci-fi space station" --items "console,crate,pipe,terminal" --wait
        assgen compose environment "enchanted forest" --no-audio --quality high --wait
    """
    style_tag = f", {style}" if style else ""
    full_prompt = f"{prompt}{style_tag}"
    global_params = {"_quality": quality} if quality != "standard" else {}
    if output:
        global_params["output_dir"] = output

    # Determine prop list
    if items:
        prop_list = [p.strip() for p in items.split(",") if p.strip()]
    else:
        prop_list = [f"{prompt} prop {i+1}" for i in range(count)]

    steps: list[dict] = [
        # Phase 1: shared style reference
        {
            "id": "style_ref",
            "job_type": "visual.concept.generate",
            "params": {
                "prompt": f"{full_prompt}, environment mood board, multiple props visible, concept art",
                "width": 1024, "height": 1024,
            },
        },
    ]

    # Phase 2: one mini-pipeline per prop
    for i, prop_name in enumerate(prop_list):
        prop_id = f"prop{i}"
        prev_mesh = f"{prop_id}_mesh"
        steps += [
            {
                "id": f"{prop_id}_concept",
                "job_type": "visual.concept.generate",
                "params": {
                    "prompt": f"{prop_name}, {full_prompt}, game prop, isolated on white",
                    "width": 1024, "height": 1024,
                },
            },
            {
                "id": f"{prop_id}_mesh",
                "job_type": "visual.model.splat",
                "from_step": f"{prop_id}_concept",
            },
            {
                "id": f"{prop_id}_uv",
                "job_type": "visual.uv.auto",
                "from_step": prev_mesh,
            },
            {
                "id": f"{prop_id}_texture",
                "job_type": "visual.texture.from_concept",
                "from_step": f"{prop_id}_uv",
                "params": {"prompt": f"{prop_name}, {full_prompt}"},
            },
            {
                "id": f"{prop_id}_lod",
                "job_type": "visual.lod.generate",
                "from_step": prev_mesh,
                "params": {"levels": 3},
            },
            {
                "id": f"{prop_id}_collider",
                "job_type": "scene.physics.collider",
                "from_step": prev_mesh,
            },
        ]

    # Phase 3: ground material
    if ground:
        steps += [
            {
                "id": "ground_albedo",
                "job_type": "visual.texture.generate",
                "params": {
                    "prompt": f"{full_prompt}, floor/ground surface material, seamless texture, top-down",
                    "width": 1024, "height": 1024,
                },
            },
            {
                "id": "ground_seamless",
                "job_type": "visual.texture.seamless",
                "from_step": "ground_albedo",
            },
            {
                "id": "ground_normal",
                "job_type": "visual.texture.normalmap_convert",
                "from_step": "ground_seamless",
            },
            {
                "id": "ground_pbr",
                "job_type": "visual.texture.pbr",
                "from_step": "ground_seamless",
            },
        ]

    # Phase 4: ambient audio
    if audio:
        steps += [
            {
                "id": "ambient",
                "job_type": "audio.ambient.generate",
                "params": {"prompt": f"{full_prompt}, ambient background loop", "duration": 30},
            },
            {
                "id": "music",
                "job_type": "audio.music.compose",
                "params": {"prompt": f"{full_prompt}, game level theme music", "duration": 60},
            },
        ]

    # Phase 5: export — use last prop's mesh as representative
    last_prop_mesh = f"prop{len(prop_list)-1}_mesh"
    steps.append({
        "id": "export",
        "job_type": "pipeline.integrate.export",
        "from_step": last_prop_mesh,
        "params": {"engine": engine},
    })

    _execute_or_dry_run(steps, global_params, dry_run, wait, pipeline_name="Environment")


# ── Shared execution helper ───────────────────────────────────────────────────

def _execute_or_dry_run(
    steps: list[dict],
    global_params: dict,
    dry_run: bool,
    wait: bool,
    pipeline_name: str,
) -> None:
    if dry_run:
        console.print(f"\n[bold]{pipeline_name} pipeline[/bold]  ({len(steps)} steps, dry-run)\n")
        for step in steps:
            src = f"  ← from [italic]{step['from_step']!r}[/italic]" if step.get("from_step") else ""
            p = step.get("params", {})
            p_str = f"  [dim]{p}[/dim]" if p else ""
            console.print(f"  [cyan]{step['id']:20}[/cyan]  {step['job_type']}{src}{p_str}")
        console.print()
        return

    if not wait:
        console.print(
            "[yellow]Note:[/yellow] compose pipelines always wait for each step — "
            "--no-wait is ignored. Use [italic]assgen pipeline workflow[/italic] for fire-and-forget."
        )

    console.print(f"\n[bold]Starting {pipeline_name} pipeline[/bold]  ({len(steps)} steps)\n")

    from assgen.client.compose import run_pipeline

    def _on_step(step_id: str, status: str, msg: str) -> None:
        icons = {"SUBMITTING": "⏳", "RUNNING": "🔄", "DONE": "✅"}
        icon = icons.get(status, " ")
        console.print(f"  {icon}  [cyan]{step_id:20}[/cyan]  {msg}")

    try:
        results = run_pipeline(steps, global_params=global_params, on_step=_on_step)
        total = len(results)
        console.print(f"\n[green]✓ {pipeline_name} pipeline complete[/green]  ({total} steps)")
    except RuntimeError as exc:
        console.print(f"\n[red]✗ {pipeline_name} pipeline failed:[/red] {exc}")
        raise typer.Exit(1) from exc
