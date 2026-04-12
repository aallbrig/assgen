---
title: "assgen · Terrain Heightmap Generator"
emoji: 🏔️
colorFrom: green
colorTo: yellow
sdk: gradio
sdk_version: "4.44.0"
python_version: "3.11"
app_file: app.py
pinned: false
license: apache-2.0
hardware: cpu-basic
tags:
  - procedural-generation
  - terrain
  - heightmap
  - game-assets
  - assgen
short_description: Generate procedural terrain heightmaps — CPU only, instant
---

# assgen · Terrain Heightmap Generator

Generate procedural terrain heightmaps using fractal Perlin noise.
CPU only — no GPU wait, results are instant.
Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.

**CLI equivalent:** `assgen gen procedural terrain heightmap --width 512 --height 512 --seed 42`
