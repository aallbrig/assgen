---
title: "assgen · Depth Estimator"
emoji: 📐
colorFrom: teal
colorTo: green
sdk: gradio
sdk_version: "4.44.0"
app_file: app.py
pinned: false
license: apache-2.0
hardware: zero-gpu
tags:
  - depth-estimation
  - computer-vision
  - game-assets
  - dpt
  - assgen
short_description: Monocular depth estimation for game scenes using DPT-Large
---

# assgen · Depth Estimator

Generate depth maps from game scene images using Intel DPT-Large.
Useful for depth-of-field setup, scene geometry estimation, and depth compositing.
Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.

**CLI equivalent:** `assgen gen scene depth estimate scene.png --wait`
**Model:** [Intel/dpt-large](https://huggingface.co/Intel/dpt-large)
