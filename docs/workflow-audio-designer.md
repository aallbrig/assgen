# Workflow: Game Audio Designer

> **Persona: Sam** — sole audio designer at a 30-person studio shipping a sci-fi shooter.
> Needs hundreds of SFX variants, adaptive music stems, ambient loops, and VO scratch tracks.

---

## What you'll generate

- Weapon SFX variants (20 in bulk)
- Combat music loop (adaptive stem)
- Ambient space station soundscape
- VO scratch track for a villain line
- Voice clone for ADR from a reference recording

---

## Prerequisites

```bash
pip install "assgen[inference]"
assgen server status   # confirm CUDA device, confirm audio models are available
assgen tasks --domain audio   # see all audio tasks and assigned models
```

---

## Sound effects

### Single SFX

```bash
assgen gen audio sfx generate \
  --prompt "plasma rifle shot, sci-fi, sharp crack, with energy tail" \
  --duration 2.0 \
  --wait
```

Output: `sfx_<id>.wav` — 44.1 kHz stereo WAV.

### Batch SFX variants (20 in parallel)

Generating weapon variant sets is the most common audio task.
Submit all at once and let the server process the queue:

```bash
#!/bin/bash
VARIANTS=(
  "plasma rifle shot, sci-fi, sharp crack"
  "plasma rifle shot, sci-fi, deep resonant boom"
  "plasma rifle shot, sci-fi, high pitched whine"
  "plasma rifle charged shot, sci-fi, building energy release"
  "plasma rifle near-miss, sci-fi, Doppler whoosh"
  "plasma rifle dry fire, sci-fi, click and hiss"
  "plasma rifle overheat, sci-fi, sizzle and steam"
  "plasma rifle reload mechanism, sci-fi, metallic clicks"
  "plasma rifle impact on metal, sci-fi, ricochet"
  "plasma rifle impact on flesh, sci-fi, wet thud"
)

for VARIANT in "${VARIANTS[@]}"; do
  assgen gen audio sfx generate \
    --prompt "$VARIANT" \
    --duration 2.0 &
done
wait
echo "✓ Queued $(assgen jobs list | grep pending | wc -l) jobs"
echo "   Monitor: assgen jobs list"
```

!!! tip "Duration guidance"
    - Impact/hit sounds: 0.5–1.0 s
    - Gunshots: 1.0–2.0 s
    - Ambience stingers: 3.0–5.0 s
    - AudioLDM2 works best under 10 seconds; longer clips may lose coherence.

---

## Music

### Combat loop (single stem)

```bash
assgen gen audio music loop \
  --prompt "tense sci-fi combat music, electronic drums, 120bpm, driving bass, minor key, loopable" \
  --duration 30 \
  --wait
```

Output: `music_<id>.wav`

### Adaptive music stems

For a reactive music system, generate stems that share BPM and key so they blend at runtime:

```bash
SHARED="120bpm, D minor, sci-fi electronic, adaptive game music stem"

# Low-intensity: ambient underscore
assgen gen audio music loop \
  --prompt "quiet ambient exploration, no drums, $SHARED" \
  --duration 60 &

# Mid-intensity: tension ramp
assgen gen audio music loop \
  --prompt "building tension, light percussion, $SHARED" \
  --duration 60 &

# High-intensity: full combat
assgen gen audio music loop \
  --prompt "full combat, heavy drums, aggressive bass, $SHARED" \
  --duration 60 &

wait
```

!!! tip "BPM and key consistency"
    Always include the same BPM and key string across all stems.
    MusicGen conditions on these tokens — matching them across prompts
    is the best way to get stems that blend without pitch or timing drift.

!!! tip "Loopless click check"
    Open the output in Audacity, select 0.5 s around the loop point (end→start),
    and listen for a click.  If present, trim 10–20 ms from each end with a
    fade-in/fade-out of 5 ms.

---

## Ambient audio

```bash
assgen gen audio ambient generate \
  --prompt "deep space station ambience, low mechanical hum, distant metallic resonance, pressurised atmosphere" \
  --duration 60 \
  --wait
```

Output: `ambient_<id>.wav`

Ambient loops benefit from longer durations (60–120 s) to avoid audible repetition.
Generate 2–3 variants and crossfade between them at runtime.

---

## Voice and VO

### TTS scratch track

```bash
assgen gen audio voice tts \
  "Your species ends today." \
  --voice villain \
  --wait
```

Output: `tts_<id>.wav` — Bark-generated speech.

!!! note "Scratch track quality"
    Bark is excellent for scratch VO and placeholder audio.
    **It is not suitable for final VO** — the prosody can be robotic and
    the speaker identity is not stable across lines.
    Use it to block out timing; replace with a voice actor for ship.

### Batch NPC dialogue

```bash
# dialog.json
# [
#   {"character": "guard", "line": "Halt! Who goes there?"},
#   {"character": "guard", "line": "Move along, citizen."},
#   {"character": "scientist", "line": "The readings are off the charts!"}
# ]

assgen gen audio voice dialog dialog.json \
  --voice npcs.yaml \
  --wait
```

### Voice clone (ADR / scratch replacement)

When a director has recorded a temp track and you need consistent voice identity:

```bash
assgen gen audio voice clone \
  --input director_reference.wav \
  --text "We need to retreat now. Fall back to the extraction point." \
  --wait
```

Output: `clone_<id>.wav`

!!! warning "Voice clone quality"
    Clone output is suitable for **internal scratch and ADR reference only**.
    It is not production-quality and must not be used as final shipped audio
    without the voice actor's explicit consent.

---

## Organising your audio output

Rename and organise generated files before importing into your audio middleware:

```bash
mkdir -p sfx/weapons music/combat music/ambient voice/villain

# Rename to something meaningful
mv sfx_abc12345.wav sfx/weapons/plasma_rifle_shot_v01.wav
mv music_def67890.wav music/combat/combat_full_120bpm.wav
```

In Wwise or FMOD: import the WAVs, set loop points on music and ambient files,
and build your adaptive music container with the stems as blend tracks.

---

## Known limitations

| Gap | Status | Notes |
|---|---|---|
| Longer SFX (> 10 s) | Works with degradation | AudioLDM2 quality drops past 10 s; stitch two clips if needed |
| Adaptive stem key detection | Manual | Include key in prompt; no auto-detection yet |
| Spatial audio (ambisonics) | Not in catalog | Convert stereo → ambisonics in Reaper/SPARTA post-generation |
| Final-quality TTS | Not in scope | Bark is scratch-only; use a professional voice actor for ship |

---

## Next steps

- [CLI Reference](cli-reference.md) — `sfx generate`, `music loop`, `voice tts`, `voice clone` flags
- [Configuration](configuration.md) — swap in a larger MusicGen model or a different AudioLDM2 variant for higher quality
- [Server Setup](server-setup.md) — run inference on a dedicated machine, submit from your DAW workstation
