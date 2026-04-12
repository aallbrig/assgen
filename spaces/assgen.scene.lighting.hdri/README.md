---
title: "assgen · HDRI Panorama Generator"
emoji: 🌅
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: "4.44.0"
python_version: "3.11"
app_file: app.py
pinned: false
license: apache-2.0
hardware: zero-gpu
tags:
  - hdri
  - panorama
  - game-lighting
  - ldm3d
  - assgen
short_description: 360° panorama HDRI reference images using LDM3D-pano
---

# assgen · HDRI Panorama Generator

Generate 360° equirectangular panoramas for game scene lighting reference using LDM3D-pano.
Outputs 1024×512 LDR PNG suitable as HDRI reference in game engines.
Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.

**CLI equivalent:** `assgen gen scene lighting hdri "sunset over desert" --wait`
**Model:** [Intel/ldm3d-pano](https://huggingface.co/Intel/ldm3d-pano)
