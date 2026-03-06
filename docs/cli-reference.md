# CLI Reference

The CLI reference below is **generated directly from the source code** — every
flag, argument, and help string you see here comes from the same Typer
annotations that power `assgen --help`.  Any change to the code is immediately
reflected here on the next docs build.

## assgen

::: mkdocs-typer
    :module: assgen.client.cli
    :command: app
    :prog_name: assgen
    :depth: 0



```
assgen [OPTIONS] COMMAND
```

| Subcommand | Description |
|-----------|-------------|
| `tasks` | Browse all game dev tasks and their assigned AI models |
| `visual` | 3D visual assets (models, textures, rigs, animations, VFX) |
| `audio` | Sound effects, music, and voice synthesis |
| `scene` | Physics collision data and lighting assets |
| `pipeline` | Workflows, batching, and engine integration |
| `support` | Narrative, lore, and procedural data |
| `qa` | Asset validation and performance testing |
| `jobs` | Job queue management |
| `models` | Model catalog and installation |
| `config` | Task → model catalog management |
| `client` | Client configuration (server targeting) |
| `server` | Server process management |
| `upgrade` | Check for and install the latest release |
| `version` | Print version information |

---

## assgen tasks

```bash
assgen tasks [--domain DOMAIN] [--json]
```

Displays a rich tree of all 50+ game development tasks with their assigned AI models.

| Option | Description |
|--------|-------------|
| `--domain` | Filter by domain: `visual`, `audio`, `scene`, `pipeline`, `qa`, `support` |
| `--json` | Output as JSON for scripting |

---

## assgen visual

### `assgen visual model`

```bash
assgen visual model create --prompt "medieval sword" [--input-image img.png] \
    [--format glb] [--model-id org/repo] [--wait]
assgen visual model retopo input.glb [--target-faces 5000] [--wait]
assgen visual model splat [--input-dir ./frames] [--wait]
assgen visual model optimize input.glb [--lod-levels 3] [--wait]
assgen visual model export input.glb [--engine unity|unreal|godot] [--wait]
```

### `assgen visual texture`

```bash
assgen visual texture generate input.glb --prompt "worn leather" [--resolution 2048] [--wait]
assgen visual texture bake high.glb low.glb [--map-types all] [--wait]
assgen visual texture pbr input.glb [--style "sci-fi metal"] [--wait]
```

### `assgen visual rig`

```bash
assgen visual rig auto character.glb [--skeleton humanoid|animal|custom] [--wait]
assgen visual rig skin character.glb [--bone-influence 4] [--wait]
assgen visual rig retarget source.glb target.glb [--wait]
```

### `assgen visual animate`

```bash
assgen visual animate keyframe character.glb --prompt "walk cycle" [--frames 60] [--wait]
assgen visual animate mocap video.mp4 [--target character.glb] [--wait]
assgen visual animate blend anim1.glb anim2.glb [--weight 0.5] [--wait]
```

### Other visual subcommands

```bash
assgen visual concept generate --prompt "fantasy castle" [--wait]
assgen visual uv auto mesh.glb [--wait]
assgen visual vfx particle --prompt "fire explosion" [--wait]
assgen visual ui icon --prompt "health potion" [--size 256] [--wait]
```

---

## assgen audio

```bash
assgen audio sfx generate "laser gun firing" [--duration 2.0] [--model-id org/repo] [--wait]
assgen audio music compose "epic battle theme" [--duration 30] [--wait]
assgen audio music loop input.wav [--target-duration 60] [--wait]
assgen audio voice tts "Welcome, hero." [--voice en_default] [--wait]
assgen audio voice dialog dialog.json [--voice npcs.yaml] [--wait]
```

---

## assgen jobs

```bash
assgen jobs list [--status queued|running|completed|failed] [--limit 50]
assgen jobs status <id>        # full 36-char UUID or 8-char prefix
assgen jobs wait <id>          # block with live progress bar
assgen jobs cancel <id>
assgen jobs clean [--days 30]  # remove completed jobs older than N days
```

---

## assgen models

```bash
assgen models list [--domain DOMAIN] [--installed]
assgen models status <model-id>
assgen models install [model-id ...]   # download from HuggingFace
```

---

## assgen config

Manages the task → HuggingFace model catalog. User overrides are saved to
`~/.config/assgen/models.yaml` and sent with each job submission.

```bash
assgen config list [--domain DOMAIN] [--installed]
assgen config show <job-type>
assgen config set <job-type> [--model-id org/repo]   # interactive if no --model-id
assgen config remove <job-type>                       # revert to built-in default
assgen config search <query>                          # search HuggingFace
```

---

## assgen client config

```bash
assgen client config show              # show resolved server URL + live health check
assgen client config set-server <url>  # point client at a remote server
assgen client config unset-server      # revert to auto-start local server
```

---

## assgen server config

```bash
assgen server config show              # show all resolved server settings
assgen server config set <key> <val>   # persist to ~/.config/assgen/server.yaml
assgen server config models [--domain] # view task → model catalog
```

### Configurable keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `host` | string | `127.0.0.1` | Bind address |
| `port` | int | `8432` | Listen port |
| `workers` | int | `1` | Concurrent worker threads |
| `device` | string | `auto` | `auto` / `cuda` / `cpu` / `mps` |
| `log_level` | string | `info` | Logging verbosity |
| `model_load_timeout` | int | `120` | Max seconds to wait for model download |
| `job_retention_days` | int | `30` | Days to keep completed jobs in DB |
| `allow_list` | list | `[]` | Allowed model IDs (`[]` = allow all) |
| `skip_model_validation` | bool | `false` | Bypass HF pipeline-tag compatibility check |

---

## assgen server

```bash
assgen server start [--daemon]    # start local assgen-server
assgen server stop                # stop local assgen-server
assgen server status              # check if server is healthy
assgen server use <url>           # alias for: assgen client config set-server
assgen server unset               # alias for: assgen client config unset-server
```

---

## assgen upgrade

```bash
assgen upgrade               # check and prompt to upgrade
assgen upgrade --check       # exit 0 if up-to-date, exit 1 if outdated
assgen upgrade --yes         # skip confirmation prompt
assgen upgrade --pre         # include pre-release versions
```

---

## assgen version

```bash
assgen version
# assgen  version: 0.0.1  python: 3.12.3  platform: Linux-6.8.0  build: v0.0.1-0-gabcdef0
```

---

## Global options

All commands support `--help`. The `--wait` / `-w` flag is available on all asset
generation commands and blocks until the job completes, showing a progress bar.

```bash
assgen visual model create --help
assgen audio sfx generate --help
```
