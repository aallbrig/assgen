---
title: "assgen · Pose Estimation (MoCap)"
emoji: 🕺
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: "5.23.0"
app_file: app.py
pinned: false
license: apache-2.0
hardware: zero-gpu
tags:
  - pose-estimation
  - motion-capture
  - game-animation
  - sapiens
  - assgen
short_description: Human pose estimation for mocap using Sapiens
---

# assgen · Pose Estimation (MoCap)

Estimate human pose keypoints from images using Sapiens Pose.
Returns an annotated overlay image and raw BVH/JSON pose data.
Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.

**CLI equivalent:** `assgen gen visual animate mocap character.png --wait`
**Model:** [facebook/sapiens-pose-0.3b](https://huggingface.co/facebook/sapiens-pose-0.3b)
