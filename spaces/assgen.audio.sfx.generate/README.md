---
title: "assgen · Audio SFX Generator"
emoji: 🔊
colorFrom: purple
colorTo: blue
sdk: gradio
sdk_version: "5.23.0"
app_file: app.py
pinned: false
license: apache-2.0
hardware: zero-gpu
tags:
  - audio
  - sound-effects
  - game-assets
  - audioldm
  - assgen
short_description: Generate game sound effects from text using AudioLDM2
---

# assgen · Audio SFX Generator

Generate WAV game sound effects from text descriptions using AudioLDM2.
Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.

**CLI equivalent:** `assgen gen audio sfx generate "sword clash" --duration 2`
**Model:** [cvssp/audioldm2](https://huggingface.co/cvssp/audioldm2)

> Note: `facebook/audiogen-medium` was removed from transformers 5.x.
> MusicGen was tried as a substitute but produces music-like noise for SFX prompts.
> AudioLDM2 is trained on general audio/sound effects and is the correct model here.
