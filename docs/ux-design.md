# assgen — User Experience Design

This document describes how `assgen` is meant to feel from the user's perspective across the three modes of operation and documents the design decisions behind the client/server architecture.

---

## The Three Modes

### Mode 1 — Solo (no server configured)

The most common starting point. The user has just installed assgen on their machine and wants to try it out without any configuration.

```
$ assgen gen audio sfx generate "laser gun firing"

⚡ No server detected — starting local assgen-server on http://127.0.0.1:8432
   (It will stay running between commands. Stop with: assgen server stop)

✓ Server ready

Job enqueued  id=a1b2c3d4  type=audio.sfx.generate
Track with: assgen jobs status a1b2c3d4
Or wait  with: assgen jobs wait a1b2c3d4
```

Or with `--wait`:

```
$ assgen gen audio sfx generate "laser gun firing" --wait

⚡ No server detected — starting local assgen-server on http://127.0.0.1:8432
   (It will stay running between commands. Stop with: assgen server stop)

✓ Server ready

⠸ Downloading facebook/audiogen-medium (4/12 files)…    8%  0:00:42
⠼ Model facebook/audiogen-medium already cached ✓        15%  0:00:01
⠦ Inference running…                                     60%  0:01:12
⠧ Post-processing audio…                                 90%  0:01:31

✓  Job a1b2c3d4 completed in 1m 33s

  Output file: ~/assgen-outputs/a1b2c3d4/laser_gun_firing.wav
  Duration:    2.0s  |  Sample rate: 44100 Hz

  To play:   afplay ~/assgen-outputs/a1b2c3d4/laser_gun_firing.wav
  Or open:   assgen jobs open a1b2c3d4
```

**Key behaviours in solo mode:**

- The server starts the first time and **stays running** between commands (via PID file). The second `assgen gen …` in the same terminal session is instant — no re-start.
- Models are downloaded to a shared OS-level location (`~/.local/share/assgen/models` on Linux, `%LOCALAPPDATA%\assgen\assgen\models` on Windows) so re-runs skip the download entirely.
- Output files are written to `~/assgen-outputs/<job-id>/` by default, or overridden with `--output`.
- The server is **not** killed when the command exits. It stays alive so the next command is faster. Use `assgen server stop` to shut it down explicitly.

---

### Mode 2 — Local server (explicit control)

For users who want the server running as a background service on their machine rather than relying on auto-start. Useful in development, or when you want to see server logs.

```bash
# Terminal A — start server with visible logs
$ assgen-server start
[2024-03-07 10:00:00] INFO  Server listening on http://127.0.0.1:8432
[2024-03-07 10:00:00] INFO  Worker thread started (device=cuda)
[2024-03-07 10:05:23] INFO  Job a1b2c3d4 QUEUED  type=visual.model.create
[2024-03-07 10:05:23] INFO  Downloading TencentARC/InstantMesh...
[2024-03-07 10:06:18] INFO  Job a1b2c3d4 RUNNING  progress=0.22
[2024-03-07 10:07:45] INFO  Job a1b2c3d4 COMPLETED

# Terminal B — use it normally
$ assgen gen visual model create --prompt "low-poly sword" --wait
⠸ Downloading TencentARC/InstantMesh (8/24 files)…    12%  0:00:55
...
```

**Key difference from solo mode:** The client detects the running server (via PID file / health check) and uses it directly. No new server is spawned.

---

### Mode 3 — Remote server (laptop → desktop)

The primary production use case: your beefy desktop runs the server and your laptop acts as the client. The desktop has a 4070; the laptop has nothing.

**One-time setup on the desktop (Windows 10):**

```powershell
# Install
pip install assgen

# Configure to accept connections from the network (not just localhost)
assgen-server config set host 0.0.0.0
assgen-server config set port 8432

# Start the server (keep this terminal open, or use --daemon)
assgen-server start
# Or as a background Windows service:
assgen-server start --daemon
```

**One-time setup on the laptop:**

```bash
# Point the client at the desktop
assgen client config set-server http://MY-DESKTOP-IP:8432

# Verify connection
assgen server status
# → Connected to http://MY-DESKTOP-IP:8432 (assgen 0.0.1, device=cuda, model=...)
```

**Then just use it normally:**

```bash
$ assgen gen visual model create --prompt "low-poly sword" --wait

⠸ Model TencentARC/InstantMesh already cached ✓         15%  0:00:01
⠼ Generating mesh from prompt…                          40%  0:00:45
⠧ Exporting to GLB…                                     88%  0:01:12

✓  Job a1b2c3d4 completed in 1m 14s (on http://MY-DESKTOP-IP:8432)

  Output file: ./sword_a1b2c3d4.glb  (downloaded from server)
  Format: GLB  |  Vertices: 12,340  |  File size: 2.1 MB
```

**What happens under the hood (remote mode):**

1. Client sends `POST /jobs` to the desktop server
2. Desktop server runs inference on the 4070 (models cached on desktop disk)
3. Desktop server writes output to its own `outputs/` directory
4. Client polls `GET /jobs/{id}` every 2 seconds, showing progress
5. When complete, client calls `GET /jobs/{id}/files` to discover output filenames
6. Client downloads each file from `GET /jobs/{id}/files/{filename}` and saves to local disk

The laptop user gets the generated file locally even though all computation happened on the desktop.

---

## Server Lifecycle

| Situation | What happens |
|-----------|--------------|
| No `server_url` configured, no PID file | Auto-start server, write PID file, server stays up |
| No `server_url` configured, PID file exists, process alive, health OK | Reuse existing server — instant |
| No `server_url` configured, PID file exists, process dead | Clean up stale PID, start fresh |
| `server_url` configured (remote or manual) | Connect directly, no auto-start logic |
| `assgen server stop` | Send SIGTERM to PID, remove PID file |
| Machine reboots | PID file becomes stale, auto-start cleans it up on next command |

**Why does the server persist between commands?** The biggest cost for most AI workflows is loading model weights into GPU VRAM — this can take 30–120 seconds for large models. Keeping the server alive means the second `assgen gen ...` call skips that cost entirely.

---

## File Flow

```
Server side                        Client side
──────────────────────────────     ──────────────────────────────
Job runs inference
  → writes output file(s) to        (polling GET /jobs/{id})
    ~/.local/share/assgen/
      outputs/{job_id}/
        output.glb
        output_preview.png

Job status → COMPLETED
  output: {files: ["output.glb"]}
                                   ← client sees COMPLETED
                                   client calls GET /jobs/{id}/files
                                   client calls GET /jobs/{id}/files/output.glb
                                   → saved to ./output.glb (or --output path)
                                   client prints "Output saved to ./output.glb"
```

For **local** server use, the file path on the server IS the file path on the client (same machine). The client skips the download and just prints the local path.

For **remote** server use, the client always downloads the file.

---

## Configuration Reference

### Client config (`~/.config/assgen/client.yaml`)

```yaml
server_url: null          # null = auto-start; or "http://MY-DESKTOP:8432"
default_wait: false       # true = always block and show progress bar
default_timeout: 300      # seconds before --wait gives up
poll_interval: 2.0        # seconds between status polls
output_dir: null          # null = current dir; or "/home/user/assgen-outputs"
```

### Server config (`~/.config/assgen/server.yaml`)

```yaml
host: "127.0.0.1"         # change to "0.0.0.0" for network access
port: 8432
device: "auto"            # "auto" | "cuda" | "cpu" | "mps"
log_level: "info"
model_load_timeout: 120   # seconds to wait for model to load
job_retention_days: 30    # days to keep completed jobs in DB

# Security — leave allow_list empty to allow all models
allow_list: []
skip_model_validation: false
```

---

## Command Summary

```
assgen gen <domain> <subdomain> <action> [OPTIONS]
  Submit a job to the server (auto-starting it if needed)

  --wait / --no-wait   Block and show progress bar until done
  --output PATH        Where to save output file(s)
  --model-id TEXT      Override the catalog model (validated by server)

assgen jobs list [-s STATUS] [--limit N]
  Show recent jobs

assgen jobs status <id>
  Show full details for a single job

assgen jobs wait <id> [--timeout N]
  Block until a job completes (attach to a running job)

assgen jobs download <id> [--output DIR]
  Download output files for a completed job

assgen server status
  Check if a server is reachable and show its config

assgen server start
  Start a local server in the foreground (for development)

assgen server stop
  Stop the local auto-started server

assgen client config set-server <URL>
  Point this client at a specific server

assgen client config unset-server
  Revert to auto-start mode

assgen tasks [--domain DOMAIN]
  Browse all supported game-dev tasks and their assigned models

assgen config list
  Show all job-type → model mappings

assgen config set <job-type> <model-id>
  Override the model for a job type on this server
```

---

## Design Principles

1. **Zero configuration required.** `pip install assgen && assgen gen audio sfx generate "explosion"` works on first run. The server starts itself, downloads the model, and runs inference.

2. **The client is always talking to a server** — even if it's a server the client started itself. This means all commands are thin HTTP wrappers; there is no inference code in the client package at all.

3. **Local and remote are identical from the CLI perspective.** The only difference is whether `server_url` is configured. Every feature (progress bars, output downloads, job history) works identically.

4. **The server is stateless enough to restart cleanly.** Jobs are persisted in SQLite. If the server crashes, jobs in RUNNING state are re-queued on next start.

5. **Model weights are cached, not re-downloaded.** The first run downloads a model; every subsequent run uses the local cache. `assgen models list` shows what's cached.

6. **Output files belong to the user, not the server.** Jobs complete with file paths; clients download them. Files are never ephemeral.
