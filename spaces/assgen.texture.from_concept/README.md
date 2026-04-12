---
title: "assgen · Texture from Concept Art"
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
  - texture-generation
  - style-transfer
  - game-assets
  - ip-adapter
  - sdxl
  - assgen
short_description: Tileable textures guided by concept art (IP-Adapter)
---

# assgen · Texture from Concept Art

Generate tileable PBR-ready textures guided by a concept art style reference.
Uses IP-Adapter + SDXL with automatic seamless texture prompt engineering.
Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.

**CLI equivalent:** `assgen gen visual texture from-concept concept.png "stone wall" --wait`
**Model:** [h94/IP-Adapter](https://huggingface.co/h94/IP-Adapter) + SDXL
