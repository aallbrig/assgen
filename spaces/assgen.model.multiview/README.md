---
title: "assgen · Multi-View Generator"
emoji: 🔄
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: "4.44.0"
python_version: "3.11"
app_file: app.py
pinned: false
license: apache-2.0
hardware: zero-gpu
tags:
  - multi-view-synthesis
  - 3d-assets
  - game-assets
  - zero123
  - assgen
short_description: 6-view synthesis from single image using Zero123++
---

# assgen · Multi-View Generator

Generate 6 surrounding views of a 3D object from a single input image using Zero123++.
Useful as a precursor to 3D reconstruction.
Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.

**CLI equivalent:** `assgen gen visual model multiview input.png --wait`
**Model:** [sudo-ai/zero123plus](https://huggingface.co/sudo-ai/zero123plus)
