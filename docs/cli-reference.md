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

## Global output flags

Three mutually exclusive output modes are available on every command:

| Flag | Description |
|------|-------------|
| _(default)_ | Rich human-readable output with colours and progress bars |
| `--json` | Emit machine-readable JSON to stdout; suppresses progress bars |
| `--yaml` | Emit machine-readable YAML to stdout; suppresses progress bars |

`--json` and `--yaml` are useful for scripting and piping to other tools:

```bash
# JSON — pipe to jq
assgen --json gen visual concept generate "ruined castle" --wait | jq .job_id

# YAML — human-friendly alternative
assgen --yaml jobs status a1b2c3d4

# Use in a pipeline
JOB=$(assgen --json gen visual model create --wait | python -c "import sys,json; print(json.load(sys.stdin)['job_id'])")
assgen --yaml jobs status "$JOB"
```

---

## assgen tasks

```bash
assgen tasks [--domain DOMAIN] [--json]
```

Displays a rich tree of all 71 game development tasks with their assigned AI models.

| Option | Description |
|--------|-------------|
| `--domain` | Filter by domain: `visual`, `audio`, `scene`, `pipeline`, `qa`, `support` |
| `--json` | Output as JSON for scripting |

---

## assgen gen visual

### `assgen gen visual model`

```bash
assgen gen visual model create --prompt "medieval sword" [--input-image img.png] \
    [--format glb] [--model-id org/repo] [--wait]
assgen gen visual model retopo input.glb [--target-faces 5000] [--wait]
assgen gen visual model splat [--input-dir ./frames] [--wait]
assgen gen visual model optimize input.glb [--lod-levels 3] [--wait]
assgen gen visual model export input.glb [--engine unity|unreal|godot] [--wait]
```

### `assgen gen visual texture`

```bash
assgen gen visual texture generate input.glb --prompt "worn leather" [--resolution 2048] [--wait]
assgen gen visual texture bake high.glb low.glb [--map-types all] [--wait]
assgen gen visual texture pbr input.glb [--style "sci-fi metal"] [--wait]
```

### `assgen gen visual rig`

```bash
assgen gen visual rig auto character.glb [--skeleton humanoid|animal|custom] [--wait]
assgen gen visual rig skin character.glb [--bone-influence 4] [--wait]
assgen gen visual rig retarget source.glb target.glb [--wait]
```

### `assgen gen visual animate`

```bash
assgen gen visual animate keyframe character.glb --prompt "walk cycle" [--frames 60] [--wait]
assgen gen visual animate mocap video.mp4 [--target character.glb] [--wait]
assgen gen visual animate blend anim1.glb anim2.glb [--weight 0.5] [--wait]
```

### Other visual subcommands

```bash
assgen gen visual concept generate --prompt "fantasy castle" [--wait]
assgen gen visual uv auto mesh.glb [--wait]
assgen gen visual vfx particle --prompt "fire explosion" [--wait]
assgen gen visual ui icon --prompt "health potion" [--size 256] [--wait]
```

---

## assgen gen audio

```bash
assgen gen audio sfx generate "laser gun firing" [--duration 2.0] [--model-id org/repo] [--wait]
assgen gen audio music compose "epic battle theme" [--duration 30] [--wait]
assgen gen audio music loop input.wav [--target-duration 60] [--wait]
assgen gen audio voice tts "Welcome, hero." [--voice en_default] [--wait]
assgen gen audio voice dialog dialog.json [--voice npcs.yaml] [--wait]
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

`jobs status` displays the job type, status, timestamps, **and the original user
input parameters** (prompt, flags, file paths) so you can review or reproduce
any previous run.  Pass `--json` / `--yaml` to get machine-readable output
suitable for re-running the job with tweaked parameters:

```bash
# Inspect a past run in YAML
assgen --yaml jobs status a1b2c3d4

# Capture params and re-submit
assgen --json jobs status a1b2c3d4 | jq .params
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
assgen gen visual model create --help
assgen gen audio sfx generate --help
```
