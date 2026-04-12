---
title: "assgen · Texture Upscaler"
emoji: 🔍
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
  - super-resolution
  - texture-upscaling
  - game-assets
  - real-esrgan
  - assgen
short_description: 4× AI texture upscaling using Real-ESRGAN
---

# assgen · Texture Upscaler

Upscale game textures up to 4× using Real-ESRGAN AI super-resolution.
Input is capped at 512×512 to stay within ZeroGPU time limits.
Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.

**CLI equivalent:** `assgen gen visual texture upscale input.png --scale 4 --wait`
**Model:** [ai-forever/Real-ESRGAN](https://huggingface.co/ai-forever/Real-ESRGAN)
