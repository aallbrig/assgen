Require assgen

Source demos/_settings.tape

Output demos/segments/06_gen_procedural.mp4

# ── Procedural Generation ──
Hide
Type "clear"
Enter
Show

Sleep 300ms
Type "printf '\\n  \\033[1;36m── Procedural Generation ──\\033[0m\\n\\n'"
Enter
Sleep 1s

Type "assgen gen procedural terrain heightmap --type fractal --width 256 --height 256 --wait"
Sleep 300ms
Enter
Sleep 5s

Sleep 500ms
