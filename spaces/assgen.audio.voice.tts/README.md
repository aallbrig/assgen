---
title: "assgen · NPC Voice TTS"
emoji: 🎙️
colorFrom: green
colorTo: green
sdk: gradio
sdk_version: "4.44.0"
app_file: app.py
pinned: false
license: apache-2.0
hardware: zero-gpu
tags:
  - audio
  - text-to-speech
  - game-assets
  - bark
  - assgen
short_description: Generate expressive NPC voices from text using Bark
---

# assgen · NPC Voice TTS

Generate expressive NPC speech — including `[laughs]`, `[sighs]`, `[gasps]` — using Bark.
Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.

**CLI equivalent:** `assgen gen audio voice tts "Halt! Who goes there?" --voice v2/en_speaker_6`
**Model:** [suno/bark](https://huggingface.co/suno/bark)
