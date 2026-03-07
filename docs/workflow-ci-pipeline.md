# Workflow: CI/CD Pipeline Integration

> **Persona: Casey** — technical artist / pipeline TD at a 100+ person studio.
> Runs assgen from GitHub Actions, not interactively. Every command must be
> scriptable, exit-code correct, and produce parseable output.

---

## Key requirements

| Requirement | How assgen addresses it |
|---|---|
| No interactive prompts | All config via env vars or YAML; no TTY needed |
| Predictable exit codes | `0` = success, non-zero = failure, always |
| Remote GPU, no client GPU in CI | `ASSGEN_SERVER_URL` env var points at GPU runner |
| Model allow-list | `server.yaml allow_list` blocks unapproved downloads |
| Asset validation | `assgen gen qa validate` command |
| Machine-readable output | `--json` flag *(roadmap — see below)* |

---

## Environment variables

All assgen configuration can be driven by environment variables — no file editing required in CI:

| Variable | Purpose | Example |
|---|---|---|
| `ASSGEN_SERVER_URL` | Point client at a remote server | `http://gpu-runner:8432` |
| `ASSGEN_CONFIG_DIR` | Override config directory | `/opt/assgen-ci-config` |
| `ASSGEN_DATA_DIR` | Override model cache root | `/mnt/models` |
| `ASSGEN_LOG_LEVEL` | Log verbosity | `INFO` or `DEBUG` |
| `ASSGEN_DEVICE` | Inference device on the server | `cuda` or `cpu` |

Set them as GitHub Actions secrets / environment variables, never in committed config files.

---

## GitHub Actions: asset validation on PRs

Add this workflow to validate every 3D asset committed in a pull request:

```yaml
# .github/workflows/asset-validation.yml
name: Asset Validation

on:
  pull_request:
    paths:
      - 'assets/**/*.glb'
      - 'assets/**/*.fbx'
      - 'assets/**/*.obj'

jobs:
  validate:
    runs-on: self-hosted        # requires a runner with GPU + assgen-server
    env:
      ASSGEN_SERVER_URL: http://localhost:8432
      ASSGEN_LOG_LEVEL: INFO

    steps:
      - uses: actions/checkout@v4

      - name: Start assgen server
        run: |
          assgen-server start --daemon --device cuda
          assgen server status   # blocks until healthy

      - name: Validate changed assets
        run: |
          # Get list of changed GLB files
          git diff --name-only origin/${{ github.base_ref }}...HEAD \
            | grep '\.glb$' > changed_assets.txt

          if [ -s changed_assets.txt ]; then
            while IFS= read -r asset; do
              echo "Validating: $asset"
              assgen gen qa validate "$asset" \
                --checks normals,uvs,manifold \
                --strict
            done < changed_assets.txt
          else
            echo "No GLB assets changed."
          fi

      - name: Stop assgen server
        if: always()
        run: assgen server stop
```

`--strict` makes the command exit non-zero on any warning, not just errors —
recommended for CI where you want to catch issues early.

---

## Server allow-list: locking down model downloads

In CI, unapproved multi-GB model downloads are a showstopper.
The `allow_list` in `server.yaml` is your control plane:

```yaml
# /opt/assgen-ci-config/server.yaml
host: "0.0.0.0"
port: 8432
device: "cuda"
log_level: "INFO"

# ONLY these models may be downloaded or used.
# Any job that would require a different model returns HTTP 403.
allow_list:
  - "stabilityai/TripoSR"
  - "facebook/audiogen-medium"
  - "suno/bark"
  - "stabilityai/stable-diffusion-xl-base-1.0"
  - "microsoft/Phi-3.5-mini-instruct"
  - "Intel/dpt-large"
```

Set `ASSGEN_CONFIG_DIR` to point at this locked-down config in your CI runner setup:

```bash
export ASSGEN_CONFIG_DIR=/opt/assgen-ci-config
```

If a developer's PR tries to use a model not in the allow_list, the server returns
`403 Forbidden` with a JSON body explaining which model was blocked and why.

---

## NPC dialogue and lore generation (LLM in CI)

Generate localisation-ready NPC dialogue and lore entries as part of a content pipeline:

```bash
# Generate NPC dialogue for a quest
assgen gen support narrative dialog "grizzled blacksmith" \
  --context "player has just saved the village from bandits" \
  --lines 8 \
  --branching \
  --wait

# Generate codex lore for a new region
assgen gen support narrative lore "The Ashfield Wastes" \
  --format codex \
  --length 400 \
  --wait
```

Pipe these into your localisation pipeline (Crowdin, Lokalise, or a custom tool)
via the job output files.

---

## Asset export for Unreal / Unity

```bash
# Convert a directory of .glb files to Unreal-compatible format
assgen gen pipeline integrate export \
  --input assets/props/ \
  --engine unreal \
  --wait
```

Outputs `.fbx` files with Unreal naming conventions, ready for batch import.

---

## Quality assurance commands

```bash
# Validate mesh geometry
assgen gen qa validate mesh.glb --checks normals,uvs,manifold --strict

# Performance check (polycount, texture memory)
assgen gen qa perf mesh.glb --budget mobile

# Style consistency check against a reference
assgen gen qa style mesh.glb --reference reference_prop.glb

# Generate QA report for a directory
assgen gen qa report assets/ --output-dir reports/ --format json
```

---

## Exit codes

| Exit code | Meaning |
|---|---|
| `0` | Command succeeded |
| `1` | Command failed (job error, validation failure) |
| `2` | Usage error (bad flag, missing argument) |

Every assgen command follows this contract — safe to use in `set -e` scripts
and GitHub Actions `if: failure()` conditionals.

---

## Machine-readable output (`--json`)

!!! note "Roadmap"
    `--json` structured output is on the assgen roadmap.  When shipped, all
    commands will accept `--json` and emit a JSON object to stdout:
    ```json
    {
      "job_id": "f25e1364",
      "status": "completed",
      "output_path": "./model_f25e1364.glb",
      "duration_s": 87.3
    }
    ```
    This will make pipeline integration via `jq` trivial.

Until `--json` ships, parse the job ID from `assgen jobs list` output and poll
with `assgen jobs status <id>` to build your own scripted wait loop:

```bash
JOB_ID=$(assgen gen visual model create --prompt "barrel" | grep "Job" | awk '{print $2}')
while true; do
  STATUS=$(assgen jobs status "$JOB_ID" | grep "status:" | awk '{print $2}')
  [ "$STATUS" = "completed" ] && break
  [ "$STATUS" = "failed" ] && { echo "Job failed"; exit 1; }
  sleep 5
done
```

---

## Pre-baking model cache for CI

On a fresh CI runner, the first job downloads the model.
Pre-bake the cache during runner setup so jobs start immediately:

```bash
# In your runner AMI / Docker image build script:
assgen models install stabilityai/TripoSR
assgen models install facebook/audiogen-medium
assgen models install suno/bark
```

Check cache status:

```bash
assgen models list         # shows all catalog models and installed status
assgen models status TripoSR   # size, path, last used
```

---

## Docker Compose for CI services

```yaml
# docker-compose.ci.yml
services:
  assgen-server:
    image: ghcr.io/aallbrig/assgen-server:latest
    environment:
      ASSGEN_DEVICE: cuda
      ASSGEN_CONFIG_DIR: /config
    volumes:
      - ./ci-config:/config:ro
      - model-cache:/root/.local/share/assgen
    ports:
      - "8432:8432"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

volumes:
  model-cache:
```

```bash
docker compose -f docker-compose.ci.yml up -d
export ASSGEN_SERVER_URL=http://localhost:8432
assgen server status   # confirm healthy
```

---

## Next steps

- [Configuration](configuration.md) — full `server.yaml` and environment variable reference
- [Server Setup](server-setup.md) — systemd service, firewall, SSH tunnel
- [Model Validation](model-validation.md) — allow-list enforcement details
- [API Reference](api-reference.md) — REST API for custom integrations beyond the CLI
