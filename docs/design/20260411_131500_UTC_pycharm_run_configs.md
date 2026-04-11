# PyCharm Run Configurations for HF Spaces

_Generated: 2026-04-11 13:15:00 UTC_

This document specifies the developer tooling that lets you open any Gradio Space in PyCharm
(or any JetBrains IDE with Python support) and run it with a single click — no terminal required.

---

## 1. What Gets Created and Where

```
.idea/
└── runConfigurations/
    ├── space_assgen_audio_sfx_generate.xml      # Space: assgen.audio.sfx.generate
    ├── space_assgen_audio_music_compose.xml
    ├── ...                                       # 72 total — one per feasible Space
    └── space_assgen_ui_screen.xml
```

Each XML file is a standard PyCharm Python run configuration. Opening the project in
PyCharm shows all 72 configurations pre-populated under "Run > Edit Configurations",
organised into five domain folders.

---

## 2. `.gitignore` Allowlist

The repo's `.gitignore` normally ignores the entire `.idea/` directory. An allowlist
block tracks only the run configuration XMLs, keeping all other IDE-local files private:

```gitignore
# IDE — ignore all of .idea except tracked run configurations
.idea/*
!.idea/runConfigurations/
.idea/runConfigurations/*
!.idea/runConfigurations/*.xml
```

This is already applied. The six existing non-Space configurations (`assgen_cli.xml`,
`assgen_server.xml`, `pytest_all_tests.xml`, etc.) are also tracked under the same rule.

---

## 3. Domain Folder Groups

Configurations are assigned to named folders for navigation in the Run Configurations dialog:

| PyCharm Folder | Spaces |
|---|---|
| `Spaces: Audio` | 14 audio generation + processing spaces |
| `Spaces: Visual` | 43 concept, texture, 3D, mesh, rig, animate, UI, sprite spaces |
| `Spaces: Scene` | 3 depth, lighting, physics spaces |
| `Spaces: Procedural` | 7 terrain, noise, dungeon, WFC, L-system spaces |
| `Spaces: Narrative` | 5 dialogue, lore, quest spaces |

---

## 4. Configuration Properties

Every Space run configuration uses the same settings, matching the project's existing
run config style:

| Property | Value |
|---|---|
| Type | Python |
| Module | `assgen` (uses project SDK = `.venv`) |
| Working directory | `$PROJECT_DIR$/spaces/<space-name>/` |
| Script | `$PROJECT_DIR$/spaces/<space-name>/app.py` |
| `EMULATE_TERMINAL` | `true` (so the Gradio URL prints in the console pane) |
| `PYTHONUNBUFFERED` | `1` |
| `IS_MODULE_SDK` | `true` (inherits project `.venv`) |

---

## 5. XML Template

When adding a new Space (e.g. after a new command is added to assgen), create its run
config by copying this template to `.idea/runConfigurations/space_<name_with_underscores>.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<component name="ProjectRunConfigurationManager">
  <configuration default="false"
                 name="Space: assgen.<domain>.<command>"
                 type="PythonConfigurationType"
                 factoryName="Python"
                 folderName="Spaces: <Domain>">
    <module name="assgen" />
    <option name="INTERPRETER_OPTIONS" value="" />
    <option name="PARENT_ENVS" value="true" />
    <envs>
      <env name="PYTHONUNBUFFERED" value="1" />
    </envs>
    <option name="SDK_HOME" value="" />
    <option name="WORKING_DIRECTORY" value="$PROJECT_DIR$/spaces/assgen.<domain>.<command>" />
    <option name="IS_MODULE_SDK" value="true" />
    <option name="ADD_CONTENT_ROOTS" value="true" />
    <option name="ADD_SOURCE_ROOTS" value="true" />
    <EXTENSION ID="PythonCoverageRunConfigurationExtension" runner="coverage.py" />
    <option name="SCRIPT_NAME" value="$PROJECT_DIR$/spaces/assgen.<domain>.<command>/app.py" />
    <option name="PARAMETERS" value="" />
    <option name="SHOW_COMMAND_LINE" value="false" />
    <option name="EMULATE_TERMINAL" value="true" />
    <option name="MODULE_MODE" value="false" />
    <option name="REDIRECT_INPUT" value="false" />
    <option name="INPUT_FILE" value="" />
    <method v="2" />
  </configuration>
</component>
```

**Filename convention:** replace every `.` in the Space name with `_` and prefix with `space_`:
`assgen.audio.sfx.generate` → `space_assgen_audio_sfx_generate.xml`

---

## 6. Generating Run Configs in Bulk

When implementing a new batch of Spaces, regenerate all XMLs at once using this script
(safe to re-run — it overwrites existing files idempotently):

```bash
python scripts/generate_run_configs.py
```

This script lives at `scripts/generate_run_configs.py` and reads the list of feasible
Spaces from `assgen.catalog` (all_job_types) cross-referenced with the feasibility matrix.
See Section 7 for the script source.

Alternatively, run the inline generator directly:

```bash
python3 - <<'EOF'
import os
RUNCONFIGS_DIR = ".idea/runConfigurations"
SPACES = [
    # paste the SPACES list from the agent briefing Section 5 / Phase 0.8
]
TEMPLATE = """..."""  # paste template from Section 5 above
for space_name, folder in SPACES:
    filename = "space_" + space_name.replace(".", "_") + ".xml"
    with open(os.path.join(RUNCONFIGS_DIR, filename), "w") as f:
        f.write(TEMPLATE.format(space_name=space_name, folder=folder))
EOF
```

---

## 7. `scripts/generate_run_configs.py` Spec

Create this file alongside `scripts/sync_spaces.py`. It should be callable standalone:

```python
#!/usr/bin/env python3
"""
Generate PyCharm run configurations for all HuggingFace Spaces.

Usage:
    python scripts/generate_run_configs.py

Safe to re-run — existing files are overwritten idempotently.
"""
from __future__ import annotations
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
RUNCONFIGS_DIR = REPO_ROOT / ".idea" / "runConfigurations"

# One entry per feasible Space: (space_repo_name, pycharm_folder_name)
SPACES: list[tuple[str, str]] = [
    # Audio (14)
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
    # Visual (43)
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
    # Scene (3)
    ("assgen.scene.depth.estimate",         "Spaces: Scene"),
    ("assgen.scene.lighting.hdri",          "Spaces: Scene"),
    ("assgen.scene.physics.collider",       "Spaces: Scene"),
    # Procedural (7)
    ("assgen.procedural.terrain.heightmap", "Spaces: Procedural"),
    ("assgen.procedural.texture.noise",     "Spaces: Procedural"),
    ("assgen.procedural.level.dungeon",     "Spaces: Procedural"),
    ("assgen.procedural.level.voronoi",     "Spaces: Procedural"),
    ("assgen.procedural.foliage.scatter",   "Spaces: Procedural"),
    ("assgen.procedural.tileset.wfc",       "Spaces: Procedural"),
    ("assgen.procedural.plant.lsystem",     "Spaces: Procedural"),
    # Narrative (5)
    ("assgen.narrative.dialogue.npc",       "Spaces: Narrative"),
    ("assgen.narrative.dialogue.validate",  "Spaces: Narrative"),
    ("assgen.narrative.lore.generate",      "Spaces: Narrative"),
    ("assgen.narrative.quest.design",       "Spaces: Narrative"),
    ("assgen.narrative.quest.validate",     "Spaces: Narrative"),
]

TEMPLATE = """\
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
            TEMPLATE.format(space_name=space_name, folder=folder),
            encoding="utf-8",
        )
        created += 1
    print(f"Generated {created} run configurations in {RUNCONFIGS_DIR}")


if __name__ == "__main__":
    main()
```

---

## 8. When to Re-run

- **Now:** All 72 XMLs are already created and tracked in git.
- **After adding a new Space:** Add its entry to `SPACES` in `generate_run_configs.py`
  and re-run the script. Commit the new XML.
- **After removing a Space:** Remove its entry and delete the XML manually, then commit.
- **Never edit the XMLs by hand** — use the script to keep the SPACES list as the
  single source of truth.

---

## 9. Usage in PyCharm

1. Open the project root in PyCharm (File > Open > `/path/to/assgen`)
2. PyCharm detects the `.venv` and sets it as the project SDK automatically
3. Open "Run > Edit Configurations" (or the run selector dropdown at the top)
4. Find the `Spaces: Audio`, `Spaces: Visual`, etc. folders
5. Select any Space and click Run (▶) — Gradio opens at `http://127.0.0.1:7860`

> **Note:** If `spaces/assgen.X/app.py` does not exist yet (Space not implemented),
> PyCharm shows a "Script file not found" warning. The run config is still valid —
> it just needs the implementation file to exist before it can execute.
