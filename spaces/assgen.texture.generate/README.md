---
title: "assgen · Texture Generator"
emoji: 🧱
colorFrom: yellow
colorTo: red
sdk: gradio
sdk_version: "4.44.0"
python_version: "3.11"
app_file: app.py
pinned: false
license: apache-2.0
hardware: zero-gpu
tags:
  - image-generation
  - texture-generation
  - game-assets
  - stable-diffusion
  - assgen
short_description: Generate tileable game textures from text using SDXL
---

# assgen · Texture Generator

Generate seamless tileable PBR-ready albedo textures from text descriptions.
The handler automatically applies texture-specific prompt guidance (seamless, top-down, uniform lighting).
Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.

**CLI equivalent:** `assgen gen visual texture generate "rough stone wall" --wait`
**Model:** [stabilityai/stable-diffusion-xl-base-1.0](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0)
