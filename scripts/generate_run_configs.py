#!/usr/bin/env python3
"""
Generate PyCharm run configurations for all feasible HuggingFace Spaces.

Creates one XML file per Space in .idea/runConfigurations/, grouped into
domain folders for easy navigation in the Run Configurations dialog.

Usage:
    python scripts/generate_run_configs.py

Safe to re-run — files are overwritten idempotently.
When adding a new Space, add its entry to SPACES below and re-run.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
RUNCONFIGS_DIR = REPO_ROOT / ".idea" / "runConfigurations"

# One entry per feasible Space: (space_repo_name, pycharm_folder_name)
# Folder names control the grouping in PyCharm's Run Configurations dialog.
SPACES: list[tuple[str, str]] = [
    # ── Audio (14) ───────────────────────────────────────────────────────────
    ("assgen.audio.sfx.generate",           "Spaces: Audio"),
    ("assgen.audio.music.compose",          "Spaces: Audio"),
    ("assgen.audio.music.loop",             "Spaces: Audio"),
    ("assgen.audio.music.adaptive",         "Spaces: Audio"),
    ("assgen.audio.ambient.generate",       "Spaces: Audio"),
    ("assgen.audio.voice.tts",              "Spaces: Audio"),
    ("assgen.audio.voice.clone",            "Spaces: Audio"),
    ("assgen.audio.process.normalize",      "Spaces: Audio"),
    ("assgen.audio.process.trim_silence",   "Spaces: Audio"),
    ("assgen.audio.process.loop_optimize",  "Spaces: Audio"),
    ("assgen.audio.process.convert",        "Spaces: Audio"),
    ("assgen.audio.process.downmix",        "Spaces: Audio"),
    ("assgen.audio.process.resample",       "Spaces: Audio"),
    ("assgen.audio.process.waveform",       "Spaces: Audio"),
    # ── Visual (43) ──────────────────────────────────────────────────────────
    ("assgen.concept.generate",             "Spaces: Visual"),
    ("assgen.concept.style",                "Spaces: Visual"),
    ("assgen.blockout.create",              "Spaces: Visual"),
    ("assgen.model.create",                 "Spaces: Visual"),
    ("assgen.model.multiview",              "Spaces: Visual"),
    ("assgen.model.splat",                  "Spaces: Visual"),
    ("assgen.mesh.validate",                "Spaces: Visual"),
    ("assgen.mesh.convert",                 "Spaces: Visual"),
    ("assgen.mesh.merge",                   "Spaces: Visual"),
    ("assgen.mesh.bounds",                  "Spaces: Visual"),
    ("assgen.mesh.flipnormals",             "Spaces: Visual"),
    ("assgen.mesh.weld",                    "Spaces: Visual"),
    ("assgen.mesh.center",                  "Spaces: Visual"),
    ("assgen.mesh.scale",                   "Spaces: Visual"),
    ("assgen.lod.generate",                 "Spaces: Visual"),
    ("assgen.uv.auto",                      "Spaces: Visual"),
    ("assgen.texture.generate",             "Spaces: Visual"),
    ("assgen.texture.upscale",              "Spaces: Visual"),
    ("assgen.texture.from_concept",         "Spaces: Visual"),
    ("assgen.texture.inpaint",              "Spaces: Visual"),
    ("assgen.texture.pbr",                  "Spaces: Visual"),
    ("assgen.texture.channel_pack",         "Spaces: Visual"),
    ("assgen.texture.convert",              "Spaces: Visual"),
    ("assgen.texture.atlas_pack",           "Spaces: Visual"),
    ("assgen.texture.mipmap",               "Spaces: Visual"),
    ("assgen.texture.normalmap_convert",    "Spaces: Visual"),
    ("assgen.texture.seamless",             "Spaces: Visual"),
    ("assgen.texture.resize",               "Spaces: Visual"),
    ("assgen.texture.report",               "Spaces: Visual"),
    ("assgen.rig.auto",                     "Spaces: Visual"),
    ("assgen.animate.keyframe",             "Spaces: Visual"),
    ("assgen.animate.mocap",                "Spaces: Visual"),
    ("assgen.vfx.particle",                 "Spaces: Visual"),
    ("assgen.sprite.pack",                  "Spaces: Visual"),
    ("assgen.ui.icon",                      "Spaces: Visual"),
    ("assgen.ui.button",                    "Spaces: Visual"),
    ("assgen.ui.panel",                     "Spaces: Visual"),
    ("assgen.ui.widget",                    "Spaces: Visual"),
    ("assgen.ui.mockup",                    "Spaces: Visual"),
    ("assgen.ui.layout",                    "Spaces: Visual"),
    ("assgen.ui.iconset",                   "Spaces: Visual"),
    ("assgen.ui.theme",                     "Spaces: Visual"),
    ("assgen.ui.screen",                    "Spaces: Visual"),
    # ── Scene (3) ────────────────────────────────────────────────────────────
    ("assgen.scene.depth.estimate",         "Spaces: Scene"),
    ("assgen.scene.lighting.hdri",          "Spaces: Scene"),
    ("assgen.scene.physics.collider",       "Spaces: Scene"),
    # ── Procedural (7) ───────────────────────────────────────────────────────
    ("assgen.procedural.terrain.heightmap", "Spaces: Procedural"),
    ("assgen.procedural.texture.noise",     "Spaces: Procedural"),
    ("assgen.procedural.level.dungeon",     "Spaces: Procedural"),
    ("assgen.procedural.level.voronoi",     "Spaces: Procedural"),
    ("assgen.procedural.foliage.scatter",   "Spaces: Procedural"),
    ("assgen.procedural.tileset.wfc",       "Spaces: Procedural"),
    ("assgen.procedural.plant.lsystem",     "Spaces: Procedural"),
    # ── Narrative (5) ────────────────────────────────────────────────────────
    ("assgen.narrative.dialogue.npc",       "Spaces: Narrative"),
    ("assgen.narrative.dialogue.validate",  "Spaces: Narrative"),
    ("assgen.narrative.lore.generate",      "Spaces: Narrative"),
    ("assgen.narrative.quest.design",       "Spaces: Narrative"),
    ("assgen.narrative.quest.validate",     "Spaces: Narrative"),
]

_TEMPLATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<component name="ProjectRunConfigurationManager">
  <configuration default="false" name="Space: {space_name}" type="PythonConfigurationType" factoryName="Python" folderName="{folder}">
    <module name="assgen" />
    <option name="INTERPRETER_OPTIONS" value="" />
    <option name="PARENT_ENVS" value="true" />
    <envs>
      <env name="PYTHONUNBUFFERED" value="1" />
    </envs>
    <option name="SDK_HOME" value="" />
    <option name="WORKING_DIRECTORY" value="$PROJECT_DIR$/spaces/{space_name}" />
    <option name="IS_MODULE_SDK" value="true" />
    <option name="ADD_CONTENT_ROOTS" value="true" />
    <option name="ADD_SOURCE_ROOTS" value="true" />
    <EXTENSION ID="PythonCoverageRunConfigurationExtension" runner="coverage.py" />
    <option name="SCRIPT_NAME" value="$PROJECT_DIR$/spaces/{space_name}/app.py" />
    <option name="PARAMETERS" value="" />
    <option name="SHOW_COMMAND_LINE" value="false" />
    <option name="EMULATE_TERMINAL" value="true" />
    <option name="MODULE_MODE" value="false" />
    <option name="REDIRECT_INPUT" value="false" />
    <option name="INPUT_FILE" value="" />
    <method v="2" />
  </configuration>
</component>
"""


def main() -> None:
    RUNCONFIGS_DIR.mkdir(parents=True, exist_ok=True)
    created = 0
    for space_name, folder in SPACES:
        filename = "space_" + space_name.replace(".", "_") + ".xml"
        path = RUNCONFIGS_DIR / filename
        path.write_text(
            _TEMPLATE.format(space_name=space_name, folder=folder),
            encoding="utf-8",
        )
        created += 1
    print(f"Generated {created} run configurations → {RUNCONFIGS_DIR}")


if __name__ == "__main__":
    main()
