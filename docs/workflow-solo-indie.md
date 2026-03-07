# Workflow: Solo Indie Dev

> **Persona: Alex** — building a 3D dungeon-crawler in Godot on an RTX 3060, solo, in spare time.
> Goal: generate a prop, texture, and music loop in a single lunch break.

---

## What you'll build

In about 30 minutes you'll go from a text prompt to:

- A game-ready `.glb` prop (brazier, sword, chest — whatever you need)
- A PBR texture set baked onto it
- A 30-second looping dungeon music track

No cloud, no monthly fees, no leaving your terminal.

---

## Prerequisites

```bash
# Install assgen with GPU inference support
pip install "assgen[inference]"

# Verify your server starts and your GPU is visible
assgen server status
# ⚡ No server detected — starting local assgen-server on http://127.0.0.1:8432
# ✓ Server ready
# device  cuda (NVIDIA GeForce RTX 3060)
```

!!! tip "First run downloads the model"
    The first `--wait` command for each task type downloads the HuggingFace model
    (~1–4 GB). Subsequent runs use the local cache and are much faster.

---

## Step 1 — Concept sketch (10 seconds)

Generate a reference image to guide the 3D step:

```bash
assgen gen visual concept generate \
  --prompt "rusty iron brazier, medieval, top-down view, white background" \
  --wait
```

Output: `concept_<id>.png` in your current directory.
Open it, check the silhouette looks right, then move on.

---

## Step 2 — Image-to-3D mesh (~3 minutes)

Pipe the concept image directly into TripoSR:

```bash
assgen gen visual model create \
  --input concept_<id>.png \
  --wait
```

!!! tip "Image input beats text-only for props"
    `--input` almost always produces a better mesh than `--prompt` alone.
    Text-to-3D works best for simple primitive-like shapes (cube, sphere, barrel).

Output: `model_<id>.glb` — a single mesh with auto-UV, ready for texturing.

---

## Step 3 — PBR texture set (~4 minutes)

```bash
assgen gen visual texture generate \
  --input model_<id>.glb \
  --prompt "rusty iron, dark soot, medieval forge, PBR diffuse" \
  --wait
```

Output: `texture_<id>.glb` — the mesh with albedo, normal, and roughness maps baked in.

!!! warning "Tiling artefacts on organic shapes"
    If you see seams, run the inpaint command on the problem area:
    ```bash
    assgen gen visual texture inpaint \
      --input texture_<id>.glb \
      --mask seam_mask.png \
      --wait
    ```

---

## Step 4 — Looping dungeon music (~2 minutes)

```bash
assgen gen audio music loop \
  --prompt "dark dungeon ambience, low strings, eerie, minor key, loopable" \
  --duration 30 \
  --wait
```

Output: `music_<id>.wav` — a 30-second clip designed to loop at the endpoint.

!!! tip "Getting seamless loops"
    Include the word `loopable` or `seamless loop` in your prompt.
    MusicGen is trained on loop-aware conditioning.
    Preview in Audacity: zoom into the end→start join to check for a click.

---

## Step 5 — Import into Godot

assgen outputs `.glb` by default — Godot's native format for 3D scenes.

1. **Drag** `texture_<id>.glb` into `res://assets/props/`
2. Godot auto-imports it as a `GLTFDocument` — no conversion needed
3. The embedded PBR materials map directly to Godot's `StandardMaterial3D`

```gdscript
# Instantiate at runtime
var brazier = load("res://assets/props/texture_<id>.glb").instantiate()
add_child(brazier)
```

For audio:

1. Drag `music_<id>.wav` into `res://assets/audio/`
2. In the Import dock: set **Loop Mode → Forward**, click **Reimport**
3. Attach an `AudioStreamPlayer` with `stream = preload("res://assets/audio/music_<id>.wav")`

---

## Full session in one script

```bash
#!/bin/bash
set -e
PROMPT="rusty iron brazier, medieval"

CONCEPT=$(assgen gen visual concept generate --prompt "$PROMPT, top-down, white bg" --wait --json | jq -r '.output_path')
MESH=$(assgen gen visual model create --input "$CONCEPT" --wait --json | jq -r '.output_path')
TEXTURED=$(assgen gen visual texture generate --input "$MESH" --prompt "$PROMPT, PBR diffuse" --wait --json | jq -r '.output_path')
MUSIC=$(assgen gen audio music loop --prompt "dark dungeon ambience, eerie, loopable" --duration 30 --wait --json | jq -r '.output_path')

echo "✓ Prop:  $TEXTURED"
echo "✓ Music: $MUSIC"
```

!!! note "`--json` flag"
    `--json` is on the roadmap and will emit structured output for scripting.
    Until then, check `assgen jobs list` for output paths.

---

## Tips for your GPU

| Model | VRAM needed | Approx. time (RTX 3060) |
|---|---|---|
| TripoSR (3D mesh) | ~6 GB | 2–3 min |
| SDXL (concept/texture) | ~8 GB | 1–2 min |
| MusicGen medium (music) | ~4 GB | 1–2 min |

If you hit OOM errors, reduce texture resolution:

```bash
assgen gen visual texture generate --input mesh.glb --resolution 1024 --wait
```

---

## Next steps

- [CLI Reference](cli-reference.md) — every flag for every command
- [Configuration](configuration.md) — override a model, change output dir
- [Server Setup](server-setup.md) — run the server as a daemon between sessions
