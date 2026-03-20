# Quick Start

This guide gets you from zero to generating your first 3D asset in about 5 minutes.

## 1. Install assgen

```bash
pip install "assgen[inference]"
```

Verify:

```bash
assgen --version
```

## 2. Start the server (optional)

The client **auto-starts** a local server on first use, so this step is optional.
If you want the server running in the background from the start:

```bash
assgen-server start --daemon
assgen server status
```

## 3. Check what tasks and models are available

```bash
assgen tasks
```

This prints a full tree of every game-dev task alongside its assigned AI model:

```
🎮 assgen — Game Asset Generation Pipeline
├── 🖼  Visual Assets
│   ├── 📐 3D Model Generation
│   │   ├── visual.model.create       [stabilityai/TripoSR]        Generate a 3D mesh...
│   │   ├── visual.model.splat        [huggingface/gaussian-...]   Gaussian Splatting...
...
```

Filter by domain:

```bash
assgen tasks --domain audio
```

## 4. Generate your first asset

=== "One-liner (compose)"
    The fastest way to get a complete, game-ready asset is a **compose** command.
    One prompt, one command — the pipeline handles everything:

    ```bash
    # Complete static prop: concept → mesh → UV → texture → LODs → collider → export
    assgen compose prop "wooden barrel, medieval dungeon" --engine godot --wait

    # Full PBR material set: albedo + normal + roughness + AO + metallic
    assgen compose material "mossy cobblestone, wet" --wait

    # Level audio suite: ambient loop + music + 5 SFX
    assgen compose soundscape "dungeon ambience, distant dripping" --wait
    ```

    See the [Compose Pipelines guide](compose-pipelines.md) for all commands.

=== "Individual steps"
    For finer control, run each step manually:
    ```bash
    # Generate a 3D prop (returns a job ID immediately)
    assgen visual model create --prompt "low-poly medieval sword"

    # Or wait for it to complete
    assgen visual model create --prompt "low-poly medieval sword" --wait
    ```

=== "Sound Effect"
    ```bash
    assgen audio sfx generate "laser gun firing" --wait
    ```

=== "Music"
    ```bash
    assgen audio music compose "epic orchestral battle theme" --duration 30 --wait
    ```

## 5. Track jobs

```bash
# List recent jobs
assgen jobs list

# Check status (use the first 8 characters of the job ID)
assgen jobs status a1b2c3d4

# Wait for a job with a live progress bar
assgen jobs wait a1b2c3d4
```

## 6. Configure a model override

Each task uses a default model from the catalog. Override it for any task:

```bash
# Search HuggingFace interactively
assgen config set visual.model.create

# Or specify directly
assgen config set visual.model.create --model-id stabilityai/TripoSR

# Revert to built-in default
assgen config remove visual.model.create
```

## 7. Point at a remote GPU server (optional)

If you have a beefy desktop with a GPU, run `assgen-server` there and point your laptop at it:

```bash
# On the GPU machine
assgen-server start --daemon

# On the client machine
assgen client config set-server http://192.168.1.100:8432
assgen client config show    # verify the health check passes
```

---

## What's next?

- [Compose Pipelines](compose-pipelines.md) — one command, complete asset pipelines
- [CLI Reference](cli-reference.md) — every command and option
- [Configuration](configuration.md) — server, client, and model catalog settings
- [Model Validation](model-validation.md) — allow-lists and HF pipeline-tag checks
- [Server Setup](server-setup.md) — systemd service, firewall, remote access
