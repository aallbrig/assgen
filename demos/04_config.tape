Require assgen

Source demos/_settings.tape

Output demos/segments/04_config.mp4

# ── Configuration ──
Hide
Type "clear"
Enter
Show

Sleep 300ms
Type "printf '\\n  \\033[1;36m── Configuration ──\\033[0m\\n\\n'"
Enter
Sleep 1s

Type "assgen config list --domain visual"
Sleep 300ms
Enter
Sleep 4s

Type "assgen config show visual.concept.generate"
Sleep 300ms
Enter
Sleep 3s

Sleep 500ms
