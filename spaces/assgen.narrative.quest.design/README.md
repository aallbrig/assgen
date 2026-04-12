---
title: "assgen · Quest Designer"
emoji: ⚔️
colorFrom: purple
colorTo: indigo
sdk: gradio
sdk_version: "5.23.0"
app_file: app.py
pinned: false
license: apache-2.0
hardware: zero-gpu
tags:
  - text-generation
  - game-design
  - quest-design
  - phi
  - assgen
short_description: Quest design with objectives using Phi-3.5-mini
---

# assgen · Quest Designer

Generate structured game quest designs (title, objectives, twists) from world context.
Outputs structured JSON for integration into game narrative systems.
Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.

**CLI equivalent:** `assgen gen support narrative quest design "stolen tome" --wait`
**Model:** [microsoft/Phi-3.5-mini-instruct](https://huggingface.co/microsoft/Phi-3.5-mini-instruct)
