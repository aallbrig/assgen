---
title: "assgen · Auto Rigger"
emoji: 🦴
colorFrom: red
colorTo: yellow
sdk: gradio
sdk_version: "5.23.0"
app_file: app.py
pinned: false
license: apache-2.0
hardware: zero-gpu
tags:
  - auto-rigging
  - 3d-animation
  - game-assets
  - unirig
  - assgen
short_description: Auto-rig 3D meshes for animation using UniRig
---

# assgen · Auto Rigger

Automatically generate animation rigs for 3D meshes using UniRig.
Input a GLB or OBJ mesh, get back a rigged GLB ready for animation.
Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.

**CLI equivalent:** `assgen gen visual rig auto character.glb --wait`
**Model:** [VAST-AI/UniRig](https://huggingface.co/VAST-AI/UniRig)
