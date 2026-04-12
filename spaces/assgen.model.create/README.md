---
title: "assgen · 3D Model Generator"
emoji: 🗿
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: "5.23.0"
app_file: app.py
pinned: false
license: apache-2.0
hardware: zero-gpu
tags:
  - image-to-3d
  - 3d-generation
  - game-assets
  - hunyuan3d
  - assgen
short_description: Generate 3D game assets from images using Hunyuan3D-2
---

# assgen · 3D Model Generator

Generate 3D game asset meshes from reference images using Hunyuan3D-2.
Output is a downloadable `.glb` file ready for Unity, Godot, or Blender.
Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.

**CLI equivalent:** `assgen gen visual model create --image ref.png --wait`
**Model:** [tencent/Hunyuan3D-2](https://huggingface.co/tencent/Hunyuan3D-2)

> ⚠️ Cold start may take 2–3 minutes while Hunyuan3D-2 (~14 GB) loads.
> ZeroGPU (A100 80 GB) has sufficient headroom. If this Space consistently times out,
> it may need a dedicated A100 tier.
