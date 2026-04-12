---
title: "assgen · Keyframe Animation Generator"
emoji: 🎬
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
  - animation
  - animatediff
  - game-assets
  - text-to-video
  - assgen
short_description: Text-to-animation GIF clips using AnimateDiff
---

# assgen · Keyframe Animation Generator

Generate animated GIF clips from text descriptions using AnimateDiff with SD1.5.
Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.

**CLI equivalent:** `assgen gen visual animate keyframe "warrior swinging sword" --wait`
**Model:** [guoyww/animatediff-motion-adapter-v1-5-2](https://huggingface.co/guoyww/animatediff-motion-adapter-v1-5-2)
