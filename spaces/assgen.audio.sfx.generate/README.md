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
  - audiocraft
  - assgen
short_description: Generate game sound effects from text using MusicGen Small
---

# assgen · Audio SFX Generator

Generate WAV game sound effects from text descriptions using MusicGen Small.
Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.

**CLI equivalent:** `assgen gen audio sfx generate "sword clash" --duration 2`
**Model:** [facebook/musicgen-small](https://huggingface.co/facebook/musicgen-small)

> Note: `facebook/audiogen-medium` was removed in transformers 5.x.
> MusicGen Small produces equivalent results for game SFX prompts.
