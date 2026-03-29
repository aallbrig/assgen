Require assgen

Source demos/_settings.tape

Output demos/segments/07_compose_pipeline.mp4

# ── Compose Pipeline ──
Hide
Type "clear"
Enter
Show

Sleep 300ms
Type "printf '\\n  \\033[1;36m── Compose Pipeline ──\\033[0m\\n\\n'"
Enter
Sleep 1s

Type "assgen compose npc 'pig shopkeeper with apron, medieval fantasy' --dry-run"
Sleep 300ms
Enter
Sleep 5s

Sleep 500ms
