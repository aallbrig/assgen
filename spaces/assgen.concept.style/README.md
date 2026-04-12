---
title: "assgen · Style Transfer (Concept Art)"
emoji: 🖌️
colorFrom: pink
colorTo: purple
sdk: gradio
sdk_version: "5.23.0"
app_file: app.py
pinned: false
license: apache-2.0
hardware: zero-gpu
tags:
  - style-transfer
  - concept-art
  - game-assets
  - ip-adapter
  - sdxl
  - assgen
short_description: Game concept art with style transfer via IP-Adapter
---

# assgen · Style Transfer (Concept Art)

Generate game concept art in the style of a reference image using IP-Adapter + SDXL.
Upload any style reference (painting, photo, sketch) and describe your content.
Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.

**CLI equivalent:** `assgen gen visual concept style "forest scene" --style ref.png --wait`
**Model:** [h94/IP-Adapter](https://huggingface.co/h94/IP-Adapter) + SDXL
