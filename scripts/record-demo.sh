#!/usr/bin/env bash
set -euo pipefail

DEMOS_DIR="demos"
SEGMENTS_DIR="demos/segments"
OUTPUT="dist/demo.mp4"
KEEP_SEGMENTS=false

usage() {
  echo "Usage: $0 [--keep]"
  echo "  --keep   Retain intermediate segment MP4s in $SEGMENTS_DIR"
  exit 1
}

for arg in "$@"; do
  case "$arg" in
    --keep) KEEP_SEGMENTS=true ;;
    --help|-h) usage ;;
    *) echo "Unknown option: $arg"; usage ;;
  esac
done

# ── Preflight ──
for cmd in vhs ffmpeg assgen; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "error: '$cmd' is not installed or not on \$PATH" >&2
    exit 1
  fi
done

mkdir -p "$SEGMENTS_DIR" dist

# ── Step 1: Record each segment ──
for tape in "$DEMOS_DIR"/[0-9][0-9]_*.tape; do
  name=$(basename "$tape")
  echo "Recording: $name"
  vhs "$tape"
done

# ── Step 2: Build ffmpeg concat list ──
CONCAT_FILE=$(mktemp)
trap 'rm -f "$CONCAT_FILE"' EXIT

for seg in "$SEGMENTS_DIR"/[0-9][0-9]_*.mp4; do
  echo "file '$(realpath "$seg")'" >> "$CONCAT_FILE"
done

# ── Step 3: Concatenate ──
ffmpeg -y -f concat -safe 0 -i "$CONCAT_FILE" -c copy "$OUTPUT"

echo ""
echo "Demo video: $OUTPUT"

# ── Step 4: Optionally clean segments ──
if [ "$KEEP_SEGMENTS" = false ]; then
  rm -f "$SEGMENTS_DIR"/[0-9][0-9]_*.mp4
  echo "Segments cleaned.  Use --keep to retain them."
fi
