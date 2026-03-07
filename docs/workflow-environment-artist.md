# Workflow: Environment / Level Artist

> **Persona: Jordan** — only environment artist at a 6-person studio making a post-apocalyptic
> open-world survival game in Unreal Engine 5. Needs biome-specific assets at scale.

---

## What you'll generate

- Concept art for a new biome
- Seamless tileable PBR ground textures (albedo, normal, roughness)
- A 360° equirectangular HDRI sky for the scene
- Depth map from a reference photograph for terrain sculpting
- Inpainted fix for any texture seams

---

## Prerequisites

```bash
pip install "assgen[inference]"
assgen server status   # confirm GPU is visible
```

---

## Biome workflow: overgrown highway

### 1 — Concept art for art direction

Before generating any textures, lock down the visual language with a concept:

```bash
assgen gen visual concept generate \
  --prompt "overgrown highway, post-apocalyptic, foggy morning, cracked asphalt, vines, desolate" \
  --wait
```

Pin this image somewhere visible during the rest of the session.
Adjust the prompt until the palette and mood match your target biome.

---

### 2 — Seamless tileable ground texture

```bash
# Cracked asphalt — primary road surface
assgen gen visual texture generate \
  --prompt "cracked asphalt, post-apocalyptic, seamless tile, 4K, PBR" \
  --resolution 2048 \
  --wait

# Overgrown verge
assgen gen visual texture generate \
  --prompt "cracked concrete with weeds, seamless tile, 4K, PBR" \
  --resolution 2048 \
  --wait
```

!!! tip "Always include 'seamless tile' in your prompt"
    The SDXL model responds well to this phrase.  If you still see edges,
    use the inpaint step below to fix them.

---

### 3 — Fix seams with inpainting

If a generated texture has visible tiling artefacts:

1. Open the texture in any paint app and draw a **solid white mask** over the seam area
2. Export the mask as `seam_mask.png` (same resolution as the texture)
3. Run inpaint:

```bash
assgen gen visual texture inpaint \
  --input asphalt_texture.png \
  --mask seam_mask.png \
  --prompt "cracked asphalt, seamless, match surrounding texture" \
  --wait
```

Repeat with a smaller mask if the first pass is still visible.

---

### 4 — HDRI sky generation

```bash
assgen gen scene lighting hdri \
  --prompt "stormy industrial skyline at dusk, post-apocalyptic, heavy clouds, orange haze" \
  --wait
```

Output: `hdri_<id>.exr` — a 16-bit equirectangular HDR image.

**Import into Unreal Engine 5:**

1. Drag `hdri_<id>.exr` into your Content Browser
2. In World Settings → Sky Light: set **Source Type → SLS Specified Cubemap**
3. Set the **Cubemap** to your imported `.exr`
4. Adjust **Intensity** and **Sky Distance Threshold** to taste

!!! note "Equirectangular = Unreal-ready"
    assgen outputs standard equirectangular `.exr`.  No conversion or
    `HDRIBackdrop` plugin required — UE5 consumes it natively.

---

### 5 — Depth map from a reference photo

If you have a reference photo of a real location and want to sculpt terrain from it:

```bash
assgen gen scene depth estimate \
  --input reference_highway.jpg \
  --wait
```

Output: `depth_<id>.png` — a 16-bit greyscale depth map.

**Use in Unreal to sculpt terrain:**

1. In Landscape Mode → Import → **Heightmap**: point at `depth_<id>.png`
2. Set Import Scale to match your world scale
3. Sculpt on top of the generated base

---

## Batch-generating texture variants

For biome-wide coverage, generate a family of related textures in one go:

```bash
#!/bin/bash
PROMPTS=(
  "cracked asphalt, post-apocalyptic, seamless, 4K PBR"
  "concrete rubble, post-apocalyptic, seamless, 4K PBR"
  "dried mud with tire tracks, post-apocalyptic, seamless, 4K PBR"
  "rusted metal grating, post-apocalyptic, seamless, 4K PBR"
  "dead grass and gravel, post-apocalyptic, seamless, 4K PBR"
)

for PROMPT in "${PROMPTS[@]}"; do
  assgen gen visual texture generate --prompt "$PROMPT" --resolution 2048 &
done
wait
echo "✓ All variants queued — check: assgen jobs list"
```

This submits all jobs concurrently.  The server processes them serially (one GPU),
but you get the output as each finishes without babysitting.

---

## Known limitations

| Gap | Status | Workaround |
|---|---|---|
| LOD generation | **Not ML** — algorithmic only | Use UE5 built-in automatic LOD (nanite or static mesh reduction) |
| Texture super-resolution | Planned | Use Real-ESRGAN standalone for 2K→4K upscaling |
| Normal / roughness separation | Albedo only from SDXL | Use Materialize (free) to derive normal/roughness from albedo |

---

## Tips

- **Iterative prompting**: generate 4–6 concept variants at low resolution (`--resolution 512`)
  first to find the right look, then re-run at 2048 for the keeper.
- **Consistent palette**: add a colour note to every prompt in a biome —
  `orange haze, desaturated greens` — to keep assets cohesive across the set.
- **Source image**: `--input photo.jpg` on concept generation gives the model a
  colour and composition anchor that purely text prompts lack.

---

## Next steps

- [Configuration](configuration.md) — set `output_dir` to your UE5 content folder
- [Server Setup](server-setup.md) — run the server on your GPU workstation and submit from your laptop
- [CLI Reference](cli-reference.md) — full flag reference
