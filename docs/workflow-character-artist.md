# Workflow: Character Artist

> **Persona: Maya** — only character artist at a 15-person studio shipping a fantasy RPG in Unity.
> 40+ unique NPC characters per project. Auto-rigging is the biggest time-saver.

---

## What you'll build

End-to-end NPC character pipeline:

1. Reference concept sheet (front/back/side views)
2. 3D mesh from the concept sheet (image-to-3D)
3. Auto-rig with humanoid skeleton
4. Idle and walk animation preview
5. Mocap extraction from a reference video

---

## Prerequisites

```bash
pip install "assgen[inference]"
assgen server status   # confirm CUDA device is visible
```

---

## Step 1 — Concept reference sheet

A front/back/side reference sheet gives the image-to-3D model the geometry cues it needs.
Do not skip this — text-to-3D for bipedal characters is unreliable.

```bash
assgen gen visual concept generate \
  --prompt "elf ranger NPC, full body character sheet, front back side views, white background, clean line art, fantasy RPG style" \
  --wait
```

Review the output.  Check:

- Limbs are symmetric and clearly separated from the body in all views
- No overlapping silhouettes between front and side

If unsatisfied, tweak the prompt and regenerate (takes ~1 minute).

---

## Step 2 — Image-to-3D mesh

```bash
assgen gen visual model create \
  --input concept_<id>.png \
  --wait
```

!!! warning "When to use `--prompt` vs `--input`"
    `--input` (image-to-3D) **almost always produces better results** for characters.
    TripoSR is trained on object images — give it one.
    Text-only `--prompt` works for simple props but not bipedal characters.

Output: `model_<id>.glb`

**Quick mesh quality check before rigging:**

```bash
# Open in any GLB viewer (e.g. gltf.report) and look for:
# - Watertight mesh (no holes at wrists, ankles, neck)
# - Reasonable poly count (< 50k for game NPC)
# - No inverted normals (shading should be smooth)
```

!!! tip "Mesh is not clean enough for UniRig?"
    Import into Blender (free), run **Mesh → Clean Up → Fill Holes**,
    export back to `.glb`, then retry the rig step.
    UniRig fails loudly if the mesh has holes — you'll see a clear error message,
    not a silent 500.

---

## Step 3 — Auto-rig

```bash
assgen gen visual rig auto \
  --input model_<id>.glb \
  --skeleton humanoid \
  --wait
```

The `--skeleton humanoid` flag tells UniRig to output a biped rig that maps to
Unity's Humanoid avatar definition — required for Mecanim and any retargetable
animation clip.

Output: `rig_<id>.glb` — mesh + skeleton + skin weights.

**Rig quality checklist:**

| Check | How |
|---|---|
| Spine chain is single, vertical | Open in Blender → Armature → Bones |
| Finger count matches mesh | Count bones in hand chain |
| Skin weights paint smoothly | Object Mode → Weight Paint |

---

## Step 4 — Keyframe animation preview

!!! note "What this step produces"
    `visual.animate.keyframe` uses AnimateDiff to render a **video preview** of the
    motion — it is not a retargetable BVH or FBX animation clip.  Use it to validate
    the rig looks plausible before investing in mocap or hand-keyed animation.

```bash
assgen gen visual animate keyframe \
  --input rig_<id>.glb \
  --prompt "looping idle animation, breathing, weight shift, natural" \
  --wait
```

Output: `animate_<id>.mp4` — a short preview video.

To get actual keyframe animation data for Unity, use the mocap step below
or a dedicated animation tool like Cascadeur or Mixamo.

---

## Step 5 — Mocap from reference video

If you have a short reference video of the motion you want:

```bash
assgen gen visual animate mocap \
  --input reference_walk.mp4 \
  --wait
```

Output: `mocap_<id>.bvh` — a BVH motion file.

**Import BVH into Unity:**

1. Import the `.bvh` via the Unity Package Manager BVH importer, or use the
   **BVH Importer** asset from the Unity Asset Store (free)
2. Set **Rig** → **Animation Type → Humanoid** and map to the assgen-generated skeleton
3. Drag animation clips onto your Animator Controller

---

## Full pipeline script

```bash
#!/bin/bash
set -e
CHARACTER="elf ranger NPC, fantasy RPG"

echo "→ Generating concept sheet..."
CONCEPT=$(assgen gen visual concept generate \
  --prompt "$CHARACTER, full body, front back side views, white background" \
  --wait --output-dir ./output | grep "output:" | awk '{print $2}')

echo "→ Creating 3D mesh from concept..."
MESH=$(assgen gen visual model create --input "$CONCEPT" --wait \
  --output-dir ./output | grep "output:" | awk '{print $2}')

echo "→ Auto-rigging (humanoid)..."
RIG=$(assgen gen visual rig auto --input "$MESH" --skeleton humanoid --wait \
  --output-dir ./output | grep "output:" | awk '{print $2}')

echo "→ Preview animation..."
assgen gen visual animate keyframe \
  --input "$RIG" --prompt "looping idle, breathing" --wait

echo "✓ Done: $RIG"
```

---

## Unity export checklist

Before handing off to engineering:

- [ ] Mesh is < 50k triangles (use Blender Decimate modifier if over)
- [ ] Single UV island per mesh (no overlaps)
- [ ] Skeleton uses Humanoid mapping (`--skeleton humanoid` ✓)
- [ ] Textures are power-of-two resolution (512, 1024, 2048)
- [ ] `.glb` file is < 50 MB

---

## Known limitations

| Gap | Status | Workaround |
|---|---|---|
| Text-to-motion (BVH from text prompt) | No open model available (2026-03) | Use Mixamo for standard motions, mocap for custom |
| Animation retargeting | Manual | Blender's Rigify retarget or Unity Humanoid avatar |
| Facial rigging | Not in catalog | Manual in Blender; ARKit blendshapes not yet supported |

---

## Next steps

- [CLI Reference](cli-reference.md) — `rig auto`, `animate keyframe`, `animate mocap` flags
- [Configuration](configuration.md) — override the rig or animate model
- [Server Setup](server-setup.md) — keep the server running across sprints
