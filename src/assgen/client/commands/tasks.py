"""assgen tasks — print the full 3D game development task tree.

Shows every job type in the pipeline, the model assigned to it,
and a one-line description of what it produces.

Usage:
  assgen tasks
  assgen tasks --domain visual
  assgen tasks --json
"""
from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.tree import Tree

console = Console()

app = typer.Typer(invoke_without_command=True, help="Show the full game asset task tree.")

# ---------------------------------------------------------------------------
# Task metadata:  (description, CLI example hint)
# Not everything is in the catalog (some tasks are data-processing, no model)
# ---------------------------------------------------------------------------
_TASK_DESC: dict[str, str] = {
    # visual / concept
    "visual.concept.generate": "Text → concept art, turnarounds, silhouette refs",
    "visual.concept.ref":      "Compile reference sheets (expressions, poses, weapons)",
    "visual.concept.style":    "Generate or enforce a project style guide",
    # visual / blockout
    "visual.blockout.create":  "2D layout sketch / greybox reference image (NOT a 3D mesh)",
    "visual.blockout.assemble":"Compose and scale a scene from blockout pieces",
    "visual.blockout.iterate": "Rapid variant generation for gameplay feedback",
    # visual / model
    "visual.model.create":     "Text/image → full 3D mesh (TripoSR, InstantMesh)",
    "visual.model.retopo":     "Clean topology to hit game polycount targets",
    "visual.model.splat":      "Gaussian Splatting / 3DGS from multi-view images",
    "visual.model.edit":       "Deform, boolean ops, mesh combine",
    # visual / uv
    "visual.uv.auto":          "AI-smart UV unwrap (minimise stretching)",
    "visual.uv.manual":        "Edit seams and packing manually",
    "visual.uv.optimize":      "Texel density normalisation, atlas packing",
    # visual / texture
    "visual.texture.generate": "Text/image → albedo/diffuse texture (output is NOT a full PBR set)",
    "visual.texture.apply":    "Project / assign texture maps via UV layout",
    "visual.texture.bake":     "High-to-low poly transfer (normal, AO, curvature)",
    "visual.texture.pbr":      "Create or edit full PBR material sets",
    "visual.texture.inpaint":  "Fill seams or damaged regions in a texture (SDXL Inpainting)",
    "visual.texture.upscale":  "4× AI texture upscaling (Real-ESRGAN)",
    # visual / rig
    "visual.rig.auto":         "Auto-rig: place skeleton joints and bind (UniRig)",
    "visual.rig.skin":         "Automated weight painting and skinning",
    "visual.rig.retarget":     "Transfer rig structure to a new mesh",
    # visual / animate
    "visual.animate.keyframe": "2D animation preview video (NOT skeletal BVH/FBX — no open model exists yet)",
    "visual.animate.mocap":    "Video pose estimation → BVH/animation clip",
    "visual.animate.blend":    "Mix, layer, or loop animation clips",
    "visual.animate.retarget": "Apply clip to a different skeleton",
    # visual / vfx
    "visual.vfx.particle":     "Generate particle texture sheets and config",
    "visual.vfx.decal":        "Create / apply dynamic decal projections",
    "visual.vfx.sim":          "Physics-based VFX bake (cloth, fluid, smoke)",
    # visual / ui
    "visual.ui.icon":          "Generate icons and sprites",
    "visual.ui.hud":           "Health bars, minimaps, crosshairs, buttons",
    "visual.ui.overlay":       "2D screen-space elements for 3D canvas",
    # audio / sfx
    "audio.sfx.generate":      "Text → discrete sound effect WAV (AudioGen — footsteps, explosions, UI)",
    "audio.sfx.edit":          "Pitch, reverb, trim, mix effects",
    "audio.sfx.library":       "Build / index a local SFX library",
    # audio / music
    "audio.music.compose":     "Text → full music track (MusicGen)",
    "audio.music.loop":        "Create seamless loops and variations",
    "audio.music.adaptive":    "Mood-responsive adaptive tracks",
    # audio / ambient
    "audio.ambient.generate":  "Text → ambient soundscape / atmospheric loop (MusicGen)",
    # audio / voice
    "audio.voice.tts":         "Text-to-speech with emotion (Bark)",
    "audio.voice.clone":       "Voice clone from reference audio sample",
    "audio.voice.dialog":      "Generate NPC dialog trees and lines",
    # scene / physics
    "scene.physics.collider":  "Generate optimised collision meshes",
    "scene.physics.rigid":     "Rigid / soft body setup and export data",
    "scene.physics.cloth":     "Cloth / hair simulation bake",
    # scene / lighting
    "scene.lighting.hdri":     "Generate panoramic HDRI sky / environment map",
    "scene.lighting.probes":   "Reflection / light probe placement",
    "scene.lighting.volumetrics": "Fog, cloud, volumetric light volumes",
    "scene.lighting.bake":     "Lightmap / global illumination bake",
    # scene / depth
    "scene.depth.estimate":    "Monocular depth estimation from a reference image (DPT-Large)",
    # pipeline / workflow
    "pipeline.workflow.create":"Define a reusable asset pipeline (YAML config)",
    "pipeline.workflow.run":   "Execute a workflow with a given set of inputs",
    "pipeline.workflow.list":  "Show all saved workflows",
    # pipeline / batch
    "pipeline.batch.queue":    "Enqueue multiple jobs from a manifest file",
    "pipeline.batch.variant":  "Generate style / damage / color-swap variants",
    "pipeline.batch.status":   "Aggregated batch progress summary",
    # pipeline / integrate
    "pipeline.integrate.prefab":  "Bundle assets as engine prefabs (Unity/Godot/Unreal)",
    "pipeline.integrate.export":  "Format conversion (.uasset, .prefab, glTF, FBX)",
    "pipeline.integrate.script":  "Generate behaviour scripts and attach-point metadata",
    # pipeline / asset (algorithmic)
    "pipeline.asset.manifest":    "Walk directory → manifest.json (path, size, sha256, type, dims)",
    "pipeline.asset.validate":    "Check oversized textures, non-pow2, high-poly meshes",
    "pipeline.asset.rename":      "Batch rename to snake_case / PascalCase / kebab-case",
    "pipeline.asset.report":      "Size budget report grouped by meshes/textures/audio/other",
    # pipeline / git (algorithmic)
    "pipeline.git.lfs_rules":     "Scan asset extensions → .gitattributes LFS rules",
    # support / narrative
    "support.narrative.dialog":   "Quest / dialog tree generation (LLM)",
    "support.narrative.lore":     "World-building text and codex entries",
    # support / data
    "support.data.lightmap":      "Manage and trigger lightmap bake jobs",
    "support.data.proc":          "Procedural generation scripts / configs",
    # narrative (top-level domain — maps to catalog job types)
    "narrative.dialogue.npc":       "NPC dialog lines or branching trees (Phi-3.5 Mini)",
    "narrative.dialogue.validate":  "Lint dialogue JSON: orphan nodes, dead ends, missing keys",
    "narrative.lore.generate":      "World-building lore: codex entries, item text (Phi-3.5 Mini)",
    "narrative.quest.design":       "Quest objectives, rewards, NPC motivations (Phi-3.5 Mini)",
    "narrative.quest.validate":     "Check quest graph for cycles and unreachable nodes",
    "narrative.i18n.extract":       "Extract localisation string keys from JSON files",
    # visual / mesh (algorithmic)
    "visual.mesh.validate":      "Manifold check, holes, non-manifold edges, duplicate verts",
    "visual.mesh.convert":       "Format conversion glb↔obj↔ply↔stl",
    "visual.mesh.merge":         "Combine N meshes into a single file",
    "visual.mesh.bounds":        "AABB, OBB, and bounding sphere",
    "visual.mesh.flipnormals":   "Flip face winding order (normals)",
    "visual.mesh.weld":          "Merge near-duplicate vertices within a threshold",
    "visual.mesh.center":        "Reposition mesh pivot to origin or bbox centre",
    "visual.mesh.scale":         "Scale mesh by factor or unit conversion",
    # visual / lod (algorithmic)
    "visual.lod.generate":       "Generate N LOD meshes via QEM decimation (pyfqmr)",
    # visual / texture (algorithmic)
    "visual.texture.channel_pack":      "Pack R/G/B/A channel images into RGBA texture",
    "visual.texture.convert":           "Convert image format (PNG/TGA/JPG/EXR → WebP/PNG/TGA)",
    "visual.texture.atlas_pack":        "Pack images into a texture atlas + UV manifest JSON",
    "visual.texture.mipmap":            "Generate full mipmap chain, save each level as PNG",
    "visual.texture.normalmap_convert": "Flip G channel to convert DX↔GL normal map conventions",
    "visual.texture.seamless":          "Fix tile seams via offset-blend (tileable texture)",
    "visual.texture.resize":            "Resize texture image; optionally snap to power-of-2",
    "visual.texture.report":            "Format, dimensions, estimated GPU memory report",
    # visual / sprite (algorithmic)
    "visual.sprite.pack":        "Pack animation frames into sprite sheet + manifest JSON",
    # audio / process (algorithmic)
    "audio.process.normalize":     "LUFS or peak normalization",
    "audio.process.trim_silence":  "Strip leading/trailing silence",
    "audio.process.loop_optimize": "Find zero-crossing loop points for seamless looping",
    "audio.process.convert":       "Convert WAV↔OGG↔MP3↔FLAC",
    "audio.process.downmix":       "Downmix stereo to mono (or upmix)",
    "audio.process.resample":      "Change audio sample rate",
    "audio.process.waveform":      "Generate waveform PNG preview",
    # proc / terrain (algorithmic)
    "proc.terrain.heightmap":    "Perlin/fractal/ridged heightmap PNG",
    "proc.texture.noise":        "Tileable noise texture (perlin/voronoi/fBm)",
    "proc.level.dungeon":        "BSP or cellular-automata dungeon layout",
    "proc.level.voronoi":        "Voronoi region map (colour PNG + regions JSON)",
    "proc.foliage.scatter":      "Poisson disk foliage scatter from density map",
    "proc.tileset.wfc":          "Wave Function Collapse tileset synthesis",
    "proc.plant.lsystem":        "L-system plant skeleton (SVG + branches JSON)",
    # qa
    "qa.validate": "Check mesh errors: normals, manifold, UV overlap, naming",
    "qa.perf":     "VRAM / polygon budget analysis, LOD preview",
    "qa.style":    "Visual consistency check against the art guide",
    "qa.report":   "Generate a full QA issues report (MD / JSON / HTML)",
}

# Logical domain → subdomain → [task] tree (all known tasks, not just catalog)
_DOMAIN_TREE: dict[str, dict] = {
    "visual": {
        "_icon": "🎨", "_desc": "3D visual asset creation",
        "concept":  {"_icon": "💡", "_desc": "Concept art & style references",
                     "_tasks": ["generate", "ref", "style"]},
        "blockout": {"_icon": "📦", "_desc": "Rapid greybox / prototype",
                     "_tasks": ["create", "assemble", "iterate"]},
        "model":    {"_icon": "🔷", "_desc": "3D mesh generation & editing",
                     "_tasks": ["create", "retopo", "splat", "edit"]},
        "mesh":     {"_icon": "🔩", "_desc": "Mesh processing (algorithmic)",
                     "_tasks": ["validate", "convert", "merge", "bounds", "flipnormals",
                                "weld", "center", "scale"]},
        "lod":      {"_icon": "📉", "_desc": "Level of Detail generation",
                     "_tasks": ["generate"]},
        "uv":       {"_icon": "🗺",  "_desc": "UV unwrapping & layout",
                     "_tasks": ["auto", "manual", "optimize"]},
        "texture":  {"_icon": "🖼",  "_desc": "PBR textures, baking, materials",
                     "_tasks": ["generate", "apply", "bake", "pbr", "inpaint", "upscale",
                                "channel_pack", "convert", "atlas_pack", "mipmap",
                                "normalmap_convert", "seamless", "resize", "report"]},
        "sprite":   {"_icon": "🎞",  "_desc": "Sprite sheet packing",
                     "_tasks": ["pack"]},
        "rig":      {"_icon": "🦴", "_desc": "Rigging & skinning",
                     "_tasks": ["auto", "skin", "retarget"]},
        "animate":  {"_icon": "🎬", "_desc": "Animation generation",
                     "_tasks": ["keyframe", "mocap", "blend", "retarget"]},
        "vfx":      {"_icon": "✨", "_desc": "Particles, decals, simulations",
                     "_tasks": ["particle", "decal", "sim"]},
        "ui":       {"_icon": "🖥",  "_desc": "Icons, HUD, 2D overlays",
                     "_tasks": ["icon", "hud", "overlay"]},
    },
    "audio": {
        "_icon": "🔊", "_desc": "Sound effects, music, voice synthesis",
        "sfx":     {"_icon": "💥", "_desc": "Sound effects",
                    "_tasks": ["generate", "edit", "library"]},
        "music":   {"_icon": "🎵", "_desc": "Music and adaptive tracks",
                    "_tasks": ["compose", "loop", "adaptive"]},
        "ambient": {"_icon": "🌊", "_desc": "Ambient soundscapes and loops",
                    "_tasks": ["generate"]},
        "voice":   {"_icon": "🗣",  "_desc": "Dialog and voice",
                    "_tasks": ["tts", "clone", "dialog"]},
        "process": {"_icon": "🔧", "_desc": "Algorithmic audio processing",
                    "_tasks": ["normalize", "trim_silence", "loop_optimize", "convert",
                               "downmix", "resample", "waveform"]},
    },
    "scene": {
        "_icon": "🌍", "_desc": "Physics data & environment lighting",
        "physics": {"_icon": "⚡", "_desc": "Collision & simulation data",
                    "_tasks": ["collider", "rigid", "cloth"]},
        "lighting": {"_icon": "💡", "_desc": "Lighting & render environment",
                     "_tasks": ["hdri", "probes", "volumetrics", "bake"]},
        "depth":    {"_icon": "📐", "_desc": "Depth estimation from images",
                     "_tasks": ["estimate"]},
    },
    "pipeline": {
        "_icon": "⚙️",  "_desc": "Workflows, batching, engine integration, asset tools",
        "workflow":  {"_icon": "🔗", "_desc": "Multi-step job chains",
                      "_tasks": ["create", "run", "list"]},
        "batch":     {"_icon": "📋", "_desc": "Bulk job processing",
                      "_tasks": ["queue", "variant", "status"]},
        "integrate": {"_icon": "🚀", "_desc": "Engine packaging & export",
                      "_tasks": ["prefab", "export", "script"]},
        "asset":     {"_icon": "📁", "_desc": "Asset manifest, validation, rename, budget",
                      "_tasks": ["manifest", "validate", "rename", "report"]},
        "git":       {"_icon": "🔀", "_desc": "Git / VCS helpers",
                      "_tasks": ["lfs_rules"]},
    },
    "proc": {
        "_icon": "🎲", "_desc": "Procedural generation (no ML)",
        "terrain":  {"_icon": "🏔",  "_desc": "Procedural terrain heightmaps",
                     "_tasks": ["heightmap"]},
        "texture":  {"_icon": "🔲", "_desc": "Procedural noise textures",
                     "_tasks": ["noise"]},
        "level":    {"_icon": "🗺",  "_desc": "Procedural level layouts",
                     "_tasks": ["dungeon", "voronoi"]},
        "foliage":  {"_icon": "🌿", "_desc": "Foliage scatter from density maps",
                     "_tasks": ["scatter"]},
        "tileset":  {"_icon": "🧩", "_desc": "Wave Function Collapse tilesets",
                     "_tasks": ["wfc"]},
        "plant":    {"_icon": "🌱", "_desc": "L-system plant skeletons",
                     "_tasks": ["lsystem"]},
    },
    "support": {
        "_icon": "📝", "_desc": "Narrative, lore, procedural data",
        "narrative": {"_icon": "📖", "_desc": "Story & lore generation",
                      "_tasks": ["dialog", "lore"]},
        "data":      {"_icon": "📊", "_desc": "Baked & procedural data",
                      "_tasks": ["lightmap", "proc"]},
    },
    "narrative": {
        "_icon": "📖", "_desc": "NPC dialogue, lore, and quest design (LLM + algorithmic)",
        "dialogue": {"_icon": "💬", "_desc": "NPC dialog generation & validation",
                     "_tasks": ["npc", "validate"]},
        "lore":     {"_icon": "📜", "_desc": "World-building lore text",
                     "_tasks": ["generate"]},
        "quest":    {"_icon": "⚔️",  "_desc": "Quest and mission design",
                     "_tasks": ["design", "validate"]},
        "i18n":     {"_icon": "🌐", "_desc": "Internationalisation string extraction",
                     "_tasks": ["extract"]},
    },
    "qa": {
        "_icon": "✅", "_desc": "Asset validation & performance testing",
        "_tasks": ["validate", "perf", "style", "report"],
    },
}


def _build_tree(domain_filter: str | None = None) -> Tree:
    from assgen.catalog import load_catalog
    catalog = load_catalog()

    root = Tree(
        "[bold cyan]assgen[/bold cyan] — 3D Game Asset Production Pipeline",
        guide_style="dim",
    )

    domains = [domain_filter] if domain_filter else list(_DOMAIN_TREE.keys())

    for domain in domains:
        if domain not in _DOMAIN_TREE:
            console.print(f"[red]Unknown domain: {domain}[/red]")
            continue
        dspec = _DOMAIN_TREE[domain]
        icon = dspec.get("_icon", "")
        desc = dspec.get("_desc", "")
        domain_node = root.add(f"{icon} [bold white]{domain}[/bold white]  [dim]{desc}[/dim]")

        for key, val in dspec.items():
            if key.startswith("_"):
                continue

            if key == "_tasks":
                # flat domain (like qa)
                break

            sub_icon = val.get("_icon", "")
            sub_desc = val.get("_desc", "")
            sub_node = domain_node.add(
                f"{sub_icon} [bold]{key}[/bold]  [dim]{sub_desc}[/dim]"
            )
            for action in val.get("_tasks", []):
                job_type = f"{domain}.{key}.{action}"
                _add_task_leaf(sub_node, action, job_type, catalog)

        # flat tasks directly on domain (e.g. qa)
        if "_tasks" in dspec:
            for action in dspec["_tasks"]:
                job_type = f"{domain}.{action}"
                _add_task_leaf(domain_node, action, job_type, catalog)

    return root


def _add_task_leaf(
    parent_node: Tree,
    action: str,
    job_type: str,
    catalog: dict,
) -> None:
    desc = _TASK_DESC.get(job_type, "")
    entry = catalog.get(job_type)

    if entry and entry.get("model_id"):
        model_label = f"[green]{entry['name']}[/green] [dim]({entry['model_id']})[/dim]"
    elif entry:
        model_label = "[dim]no model (data processing)[/dim]"
    else:
        model_label = "[dim yellow]no model configured[/dim yellow]"

    parent_node.add(
        f"[cyan]{action}[/cyan]  {model_label}\n"
        f"  [dim]{desc}[/dim]"
    )


@app.callback(invoke_without_command=True)
def tasks_cmd(
    ctx: typer.Context,
    domain: Optional[str] = typer.Option(
        None, "--domain", "-d",
        help="Filter to a single domain: visual audio scene pipeline support qa",
    ),
    show_json: bool = typer.Option(False, "--json", help="Output as JSON (job-type list)"),
) -> None:
    """Show the complete 3D game development task tree with configured models.

    Every job type in the pipeline is shown with its assigned AI model
    and a one-line description of what it produces.  Use --domain to
    focus on a single production area.

    To configure which model handles a task:
      assgen server config models set <job-type>
    """
    if ctx.invoked_subcommand:
        return

    if show_json:
        import json
        from assgen.catalog import load_catalog
        catalog = load_catalog()
        out = []
        for domain_name, dspec in _DOMAIN_TREE.items():
            if domain and domain_name != domain:
                continue
            for key, val in dspec.items():
                if key.startswith("_"):
                    continue
                if key == "_tasks":
                    break
                for action in val.get("_tasks", []):
                    jt = f"{domain_name}.{key}.{action}"
                    entry = catalog.get(jt, {})
                    out.append({
                        "job_type": jt,
                        "model_id": entry.get("model_id"),
                        "model_name": entry.get("name"),
                        "description": _TASK_DESC.get(jt, ""),
                    })
            if "_tasks" in dspec:
                for action in dspec["_tasks"]:
                    jt = f"{domain_name}.{action}"
                    entry = catalog.get(jt, {})
                    out.append({
                        "job_type": jt,
                        "model_id": entry.get("model_id"),
                        "model_name": entry.get("name"),
                        "description": _TASK_DESC.get(jt, ""),
                    })
        console.print(json.dumps(out, indent=2))
        return

    tree = _build_tree(domain)
    console.print(tree)
    console.print()
    console.print("[dim]Configure models:  assgen server config models[/dim]")
    console.print("[dim]Submit a job:       assgen <domain> <subdomain> <action> --help[/dim]")
