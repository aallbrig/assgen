---
title: "assgen · Texture Inpainting"
emoji: 🖼️
colorFrom: yellow
colorTo: red
sdk: gradio
sdk_version: "5.23.0"
app_file: app.py
pinned: false
license: apache-2.0
hardware: zero-gpu
tags:
  - inpainting
  - texture-generation
  - game-assets
  - sdxl
  - assgen
short_description: Fill masked texture regions with SDXL Inpainting
---

# assgen · Texture Inpainting

Fill masked regions of a game texture using SDXL Inpainting.
Upload a texture and a white-on-black mask, describe what to fill in.
Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.

**CLI equivalent:** `assgen gen visual texture inpaint texture.png --mask mask.png --wait`
**Model:** [diffusers/stable-diffusion-xl-1.0-inpainting-0.1](https://huggingface.co/diffusers/stable-diffusion-xl-1.0-inpainting-0.1)
