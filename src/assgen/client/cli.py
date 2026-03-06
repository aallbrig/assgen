"""assgen — root CLI entry point.

Command hierarchy:
  assgen visual      → concept, blockout, model, uv, texture, rig, animate, vfx, ui
  assgen audio       → sfx, music, voice
  assgen scene       → physics, lighting
  assgen pipeline    → workflow, batch, integrate
  assgen support     → narrative, data
  assgen qa          → validate, perf, style, report
  assgen tasks       → full task tree with configured models
  assgen jobs        → list, status, wait, cancel, clean
  assgen models      → list, status, install
  assgen server      → start, stop, status, config (show/set/models), use, unset
  assgen client      → config (show/set-server/unset-server)
  assgen config      → list, show, set, remove, search
  assgen version     → print version info
"""
from __future__ import annotations

import typer
from rich.console import Console

# ── sub-apps ────────────────────────────────────────────────────────────────
from assgen.client.commands.client_cmd import app as client_app
from assgen.client.commands.config     import app as config_app
from assgen.client.commands.upgrade    import app as upgrade_app
from assgen.client.commands.jobs      import app as jobs_app
from assgen.client.commands.models    import app as models_app
from assgen.client.commands.server    import app as server_app
from assgen.client.commands.tasks     import app as tasks_app
from assgen.client.commands.pipeline  import app as pipeline_app
from assgen.client.commands.qa        import app as qa_app
from assgen.client.commands.support   import app as support_app

# visual sub-apps
from assgen.client.commands.visual.concept  import app as concept_app
from assgen.client.commands.visual.blockout import app as blockout_app
from assgen.client.commands.visual.model    import app as model_app
from assgen.client.commands.visual.uv       import app as uv_app
from assgen.client.commands.visual.texture  import app as texture_app
from assgen.client.commands.visual.rig      import app as rig_app
from assgen.client.commands.visual.animate  import app as animate_app
from assgen.client.commands.visual.vfx      import app as vfx_app
from assgen.client.commands.visual.ui_cmd   import app as ui_app

# audio sub-apps
from assgen.client.commands.audio.sfx   import app as sfx_app
from assgen.client.commands.audio.music import app as music_app
from assgen.client.commands.audio.voice import app as voice_app

# scene sub-apps
from assgen.client.commands.scene.physics  import app as physics_app
from assgen.client.commands.scene.lighting import app as lighting_app

console = Console()

# ── root app ─────────────────────────────────────────────────────────────────
app = typer.Typer(
    name="assgen",
    help="AI-driven game asset generation pipeline.",
    no_args_is_help=True,
    add_completion=True,
    rich_markup_mode="rich",
)

# ── visual ───────────────────────────────────────────────────────────────────
visual_app = typer.Typer(
    help="3D visual asset creation: models, textures, rigs, animations, VFX, UI.",
    no_args_is_help=True,
)
visual_app.add_typer(concept_app,  name="concept",  help="Concept art and style references")
visual_app.add_typer(blockout_app, name="blockout", help="Rapid greybox / blockout prototyping")
visual_app.add_typer(model_app,    name="model",    help="3D mesh generation, retopo, splat, export")
visual_app.add_typer(uv_app,       name="uv",       help="UV unwrapping and layout optimisation")
visual_app.add_typer(texture_app,  name="texture",  help="PBR textures, baking, material sets")
visual_app.add_typer(rig_app,      name="rig",      help="Auto-rigging, skinning, retargeting")
visual_app.add_typer(animate_app,  name="animate",  help="Keyframe, mocap, and animation blending")
visual_app.add_typer(vfx_app,      name="vfx",      help="Particle systems, decals, simulations")
visual_app.add_typer(ui_app,       name="ui",       help="Icons, HUD elements, 2D overlays")
app.add_typer(visual_app, name="visual")

# ── audio ────────────────────────────────────────────────────────────────────
audio_app = typer.Typer(
    help="Sound effects, music, and voice synthesis.",
    no_args_is_help=True,
)
audio_app.add_typer(sfx_app,   name="sfx",   help="Sound effects generation")
audio_app.add_typer(music_app, name="music", help="Music and ambient track generation")
audio_app.add_typer(voice_app, name="voice", help="TTS, voice cloning, and dialog batching")
app.add_typer(audio_app, name="audio")

# ── scene ────────────────────────────────────────────────────────────────────
scene_app = typer.Typer(
    help="Physics collision data and lighting assets.",
    no_args_is_help=True,
)
scene_app.add_typer(physics_app,  name="physics",  help="Colliders, rigid bodies, cloth sim")
scene_app.add_typer(lighting_app, name="lighting", help="HDRI skies, probes, volumetrics, lightmaps")
app.add_typer(scene_app, name="scene")

# ── infrastructure ───────────────────────────────────────────────────────────
app.add_typer(pipeline_app, name="pipeline", help="Workflows, batching, and engine integration")
app.add_typer(support_app,  name="support",  help="Narrative, lore, and procedural data")
app.add_typer(qa_app,       name="qa",       help="Asset validation and performance testing")
app.add_typer(tasks_app,    name="tasks",    help="Browse all game dev tasks and their configured models")
app.add_typer(jobs_app,     name="jobs",     help="Job queue management")
app.add_typer(models_app,   name="models",   help="Model catalog and installation")
app.add_typer(server_app,   name="server",   help="Local server process management")
app.add_typer(client_app,   name="client",   help="Client configuration: server targeting and connection settings")
app.add_typer(config_app,   name="config",   help="Configure job-type → model mappings")
app.add_typer(upgrade_app,  name="upgrade",  help="Check for and install the latest assgen release")


# ── version command ───────────────────────────────────────────────────────────
@app.command("version")
def version_cmd() -> None:
    """Print version information and exit."""
    from assgen.version import format_version_string
    console.print(format_version_string("assgen"))
