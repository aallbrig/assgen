---
title: "assgen · NPC Dialogue Generator"
emoji: 💬
colorFrom: pink
colorTo: purple
sdk: gradio
sdk_version: "4.44.0"
app_file: app.py
pinned: false
license: apache-2.0
hardware: zero-gpu
tags:
  - text-generation
  - npc-dialogue
  - game-writing
  - phi
  - assgen
short_description: Generate NPC dialogue from character descriptions using Phi-3.5
---

# assgen · NPC Dialogue Generator

Generate game NPC dialogue from character descriptions and player queries using Phi-3.5-mini.
Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.

**CLI equivalent:** `assgen gen support narrative dialogue npc --persona "..." --player "..." --wait`
**Model:** [microsoft/Phi-3.5-mini-instruct](https://huggingface.co/microsoft/Phi-3.5-mini-instruct)
