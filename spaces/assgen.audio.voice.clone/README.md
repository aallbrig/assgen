---
title: "assgen · Voice Cloning"
emoji: 🎤
colorFrom: purple
colorTo: pink
sdk: gradio
sdk_version: "4.44.0"
python_version: "3.11"
app_file: app.py
pinned: false
license: apache-2.0
hardware: zero-gpu
tags:
  - voice-cloning
  - text-to-speech
  - game-audio
  - xtts
  - assgen
short_description: Clone any NPC voice from a reference clip (XTTS-v2)
---

# assgen · Voice Cloning

Clone a voice from a 5–30 s reference audio clip and synthesize speech in that voice.
Supports 14 languages. Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.

**CLI equivalent:** `assgen gen audio voice clone --speaker-wav ref.wav --text "..." --wait`
**Model:** [coqui/XTTS-v2](https://huggingface.co/coqui/XTTS-v2)
