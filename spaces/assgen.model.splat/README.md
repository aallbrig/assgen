---
title: "assgen · Image-to-3D (TripoSR)"
emoji: 🗿
colorFrom: gray
colorTo: blue
sdk: gradio
sdk_version: "5.23.0"
app_file: app.py
pinned: false
license: apache-2.0
hardware: zero-gpu
tags:
  - 3d-generation
  - image-to-3d
  - game-assets
  - triposr
  - assgen
short_description: Image-to-3D mesh reconstruction using TripoSR
---

# assgen · Image-to-3D (TripoSR)

Convert a single foreground image to a 3D GLB mesh using TripoSR.
Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.

**CLI equivalent:** `assgen gen visual model splat input.png --wait`
**Model:** [stabilityai/TripoSR](https://huggingface.co/stabilityai/TripoSR)
