# assgen

**AI-driven game asset generation pipeline** — a Kubernetes-style client/server CLI that lets you generate 3D models, textures, rigs, animations, sound effects, and music using open-source HuggingFace models running locally on your GPU.

<p class="hero-badges">
  <a href="https://github.com/aallbrig/assgen/actions/workflows/ci.yml">
    <img src="https://github.com/aallbrig/assgen/actions/workflows/ci.yml/badge.svg" alt="CI">
  </a>
  <a href="https://github.com/aallbrig/assgen/releases">
    <img src="https://img.shields.io/github/v/release/aallbrig/assgen" alt="Latest Release">
  </a>
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
</p>

---

## What is assgen?

assgen is a command-line tool designed for indie game developers and artists who want to leverage AI for asset creation — without cloud costs, without proprietary APIs, and without leaving their terminal.

You describe what you want. assgen dispatches the work to a local server that downloads the right model from HuggingFace, runs inference on your GPU, and saves the result.

```bash
# Generate a 3D prop
assgen gen visual model create --prompt "low-poly medieval sword" --wait

# Generate a sound effect
assgen gen audio sfx generate "laser gun firing" --wait

# View all available tasks and their assigned AI models
assgen tasks
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  assgen  (client CLI, runs anywhere)                 │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP REST
┌──────────────────────▼──────────────────────────────┐
│  assgen-server  (FastAPI + SQLite job queue)         │
│  ├── ModelManager   (HuggingFace Hub download/cache) │
│  ├── WorkerThread   (GPU inference)                  │
│  └── Validation     (allow-list + HF tag checking)  │
└─────────────────────────────────────────────────────┘
```

The client auto-starts a local server on first use, or you can point it at a remote GPU machine:

```bash
assgen client config set-server http://my-gpu-desktop:8432
```

## Feature Highlights

=== "3D Assets"
    - Text/image → rigged 3D mesh (`.glb`, `.fbx`, `.obj`)
    - Auto UV unwrapping and PBR texture generation
    - Gaussian Splatting (3DGS) from multi-view images
    - Auto-rigging and skin weight generation (UniRig)
    - Animation: keyframe generation, mocap from video

=== "Audio"
    - Sound effects from text prompts (AudioLDM2)
    - Music composition (MusicGen)
    - Voice/TTS and NPC dialog batching (Bark)

=== "Pipeline"
    - Scene lighting: HDRI sky generation, GI lightmap baking
    - Physics: collision mesh generation, cloth sim baking
    - Multi-step workflows with batch processing
    - Engine export (Unity, Unreal, Godot)

=== "Security"
    - Server `allow_list`: restrict which HF models can be downloaded
    - Pipeline-tag validation: prevents mismatched models (e.g. TTS for 3D generation)
    - Configurable per-server overrides

## Requirements

- Python 3.11+
- For inference: an NVIDIA GPU (RTX 4070 or better recommended — 12GB VRAM handles SDXL, TripoSR, AudioLDM2)
- For check-only / orchestration: CPU is fine

## Workflow Guides

Jump straight to a guide written for your role:

| Role | Engine | Guide |
|---|---|---|
| Solo indie dev | Godot | [Prop → texture → music in a lunch break](workflow-solo-indie.md) |
| Environment / level artist | Unreal Engine 5 | [Biome textures, HDRI skies, seam inpainting](workflow-environment-artist.md) |
| Character artist | Unity | [Concept → mesh → rig → animate](workflow-character-artist.md) |
| Game audio designer | Any | [SFX variants, adaptive music, VO scratch](workflow-audio-designer.md) |
| Pipeline TD / technical artist | Any (CI/CD) | [GitHub Actions, allow-list, QA validation](workflow-ci-pipeline.md) |

---

[Get started →](install.md){ .md-button .md-button--primary }
[View source on GitHub →](https://github.com/aallbrig/assgen){ .md-button }
