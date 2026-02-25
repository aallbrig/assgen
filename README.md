# assgen

AI-driven game asset generation pipeline — Kubernetes-style client/server architecture for 3D game development.

## Architecture

```
┌───────────────────────────────────────────────────────────┐
│  assgen  (client CLI)                                      │
│  ├── visual model create --prompt "sword" --wait           │
│  ├── audio sfx generate "laser blast" --wait              │
│  └── jobs list / status / wait / cancel                   │
└───────────────────┬───────────────────────────────────────┘
                    │ HTTP (REST)
┌───────────────────▼───────────────────────────────────────┐
│  assgen-server                                             │
│  ├── FastAPI REST API  (/jobs  /models  /health)          │
│  ├── WorkerThread      (polls SQLite queue)               │
│  └── ModelManager      (HuggingFace Hub download/cache)   │
└───────────────────┬───────────────────────────────────────┘
                    │
         ~/.config/assgen/assgen.db   (SQLite)
         ~/.local/share/assgen/models/  (model cache)
```

The client auto-detects whether a server is configured:
- If `server_url` is set in `~/.config/assgen/client.yaml` → use that server.
- Otherwise → start a local `assgen-server` process (PID-tracked) and use it.

This lets you run the server on a powerful GPU machine and point your laptop's client at it, or just run everything locally.

## Installation

```bash
pip install assgen

# For GPU inference (RTX 4070 recommended):
pip install "assgen[inference]"
```

## Quick Start

```bash
# Check version
assgen version

# Start local server (optional — client auto-starts if not configured)
assgen-server start --daemon

# Generate a 3D model
assgen visual model create --prompt "low-poly medieval sword" --wait

# Generate sound effects
assgen audio sfx generate "laser gun firing" --wait

# Generate background music
assgen audio music compose "epic orchestral battle theme" --duration 30 --wait

# Auto-rig a character
assgen visual rig auto character.glb --wait

# List recent jobs
assgen jobs list

# Point client at a remote server
assgen server use http://my-gpu-machine:8432
```

## CLI Command Tree

```
assgen
├── visual                    # All 3D visual assets
│   ├── concept               # AI concept art (SDXL)
│   │   ├── generate          # text → concept art
│   │   ├── ref               # multi-view reference sheet
│   │   └── style             # art style samples
│   ├── blockout              # Greybox prototyping
│   │   ├── create            # text/image → blockout mesh
│   │   ├── assemble          # combine pieces into scene
│   │   └── iterate           # quick variation
│   ├── model                 # 3D mesh generation
│   │   ├── create            # text/image → .glb (TripoSR)
│   │   ├── highpoly          # high-poly refinement
│   │   ├── retopo            # auto-retopology
│   │   ├── splat             # Gaussian Splatting (3DGS)
│   │   ├── edit              # deform / boolean / combine
│   │   ├── optimize          # LOD generation
│   │   └── export            # convert to engine format
│   ├── uv                    # UV unwrapping
│   │   ├── auto              # AI smart-unwrap
│   │   ├── manual            # seam suggestions
│   │   └── optimize          # texel density optimisation
│   ├── texture               # PBR texturing & baking
│   │   ├── generate          # text → albedo + PBR maps
│   │   ├── apply             # project onto mesh
│   │   ├── bake              # high-to-low bake
│   │   └── pbr               # full PBR material set
│   ├── rig                   # Character rigging
│   │   ├── auto              # auto-skeleton (UniRig)
│   │   ├── skin              # skin weight maps
│   │   └── retarget          # rig retargeting
│   ├── animate               # Animation generation
│   │   ├── keyframe          # text → animation (AnimateDiff)
│   │   ├── mocap             # video → motion capture
│   │   ├── blend             # mix/loop animations
│   │   └── retarget          # animation retargeting
│   ├── vfx                   # VFX & particles
│   │   ├── particle          # particle sprite sheets
│   │   ├── decal             # dynamic decal textures
│   │   └── sim               # physics VFX bake
│   └── ui                    # UI/HUD elements
│       ├── icon              # icons & sprites
│       ├── hud               # health bars, minimaps
│       └── overlay           # 2D canvas overlays
├── audio                     # Sound & music
│   ├── sfx                   # Sound effects (AudioGen)
│   │   ├── generate          # text → WAV
│   │   ├── edit              # pitch/reverb/layer
│   │   └── library           # browse local SFX library
│   ├── music                 # Music (MusicGen)
│   │   ├── compose           # text → music track
│   │   ├── loop              # seamless loop generation
│   │   └── adaptive          # mood-based stems
│   └── voice                 # Voice synthesis (Bark)
│       ├── tts               # text → speech
│       ├── clone             # voice cloning
│       └── dialog            # batch NPC dialog
├── scene                     # Physics + lighting data
│   ├── physics               # Collision & simulation
│   │   ├── collider          # optimised collision mesh
│   │   ├── rigid             # rigid body setup
│   │   ├── cloth             # cloth/hair simulation bake
│   │   └── export            # engine physics export
│   └── lighting              # Lighting assets
│       ├── hdri              # text → HDR sky map
│       ├── probes            # reflection/irradiance probes
│       ├── volumetrics       # fog, clouds, atmosphere
│       └── bake              # GI lightmap bake
├── pipeline                  # Orchestration
│   ├── workflow              # Multi-step workflows
│   │   ├── create            # define step sequence
│   │   ├── run               # execute with inputs
│   │   └── list              # browse saved workflows
│   ├── batch                 # Batch processing
│   │   ├── queue             # enqueue from JSON manifest
│   │   ├── variant           # style/damage variants
│   │   └── status            # batch queue overview
│   └── integrate             # Engine integration
│       ├── export            # engine-specific export
│       ├── prefab            # bundle into prefab
│       └── script            # behavior stubs
├── support                   # Narrative & data
│   ├── narrative
│   │   ├── dialog            # NPC dialog trees
│   │   └── lore              # world-building text
│   └── data
│       ├── lightmap          # AI lightmap baking
│       └── proc              # procedural gen scripts
├── qa                        # Quality assurance
│   ├── validate              # mesh/UV/normal checks
│   ├── perf                  # polygon/VRAM analysis
│   ├── style                 # art style consistency
│   └── report                # full QA report
├── jobs                      # Job management
│   ├── list                  # list all jobs
│   ├── status <id>           # single job status
│   ├── wait <id>             # wait with progress bar
│   ├── cancel <id>           # cancel a job
│   └── clean                 # remove old jobs from DB
├── models                    # Model management
│   ├── list                  # catalog + install status
│   ├── status <id>           # single model details
│   └── install [id...]       # download from HuggingFace
└── server                    # Server management
    ├── start [--daemon]       # start local server
    ├── stop                   # stop local server
    ├── status                 # server health check
    ├── config                 # show resolved config
    ├── use <url>              # point client at server
    └── unset                  # revert to auto-start
```

## Configuration

Config lives in the OS-appropriate directory (XDG on Linux/macOS, `%APPDATA%` on Windows):

| File | Purpose |
|------|---------|
| `client.yaml` | Server URL, poll interval, default --wait |
| `server.yaml` | Host, port, device (cuda/cpu), log level |
| `models.yaml` | User catalog overrides |
| `assgen.db` | SQLite job database |
| `server.pid` | Running local server PID |

```yaml
# ~/.config/assgen/client.yaml
server_url: null          # null = auto-start local server
default_wait: false
poll_interval: 2.0

# ~/.config/assgen/server.yaml
host: "127.0.0.1"
port: 8432
device: "auto"            # auto | cuda | cpu
log_level: "info"
```

## Running as a systemd Service

```ini
# /etc/systemd/system/assgen-server.service
[Unit]
Description=assgen asset generation server
After=network.target

[Service]
Type=simple
User=youruser
ExecStart=/path/to/.venv/bin/assgen-server start
Restart=on-failure
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
systemctl enable --now assgen-server
journalctl -u assgen-server -f   # follow JSON-structured logs
```

## Hardware Notes

- **RTX 4070 (12GB VRAM)**: Sufficient for SDXL, TripoSR, MusicGen-Small, AudioGen-Medium
- Set `device: "cuda"` in `server.yaml` for GPU acceleration
- For lighter models, `device: "cpu"` works but is slower
- Use `HF_TOKEN` env var for authenticated Hub downloads (higher rate limits)

## Adding Real Inference Handlers

The worker dispatches each `job_type` to `assgen/server/handlers/<job_type>.py`.
Create a module with a `run()` function:

```python
# src/assgen/server/handlers/visual_model_create.py
from pathlib import Path
from typing import Any, Callable

def run(
    job_type: str,
    params: dict[str, Any],
    model_id: str | None,
    model_path: str | None,
    device: str,
    progress_cb: Callable[[float, str], None],
) -> dict[str, Any]:
    progress_cb(0.2, "Loading model")
    # ... load transformers pipeline from model_path ...
    progress_cb(0.8, "Running inference")
    # ... run inference ...
    return {"output_path": "/path/to/output.glb"}
```

Without a handler, jobs run through the stub handler (which simulates steps and returns immediately — useful for development).
