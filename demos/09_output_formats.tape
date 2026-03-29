Require assgen

Source demos/_settings.tape

Output demos/segments/09_output_formats.mp4

# ── Output Formats ──
Hide
Type "clear"
Enter
Show

Sleep 300ms
Type "printf '\\n  \\033[1;36m── Output Formats ──\\033[0m\\n\\n'"
Enter
Sleep 1s

Type "assgen tasks --domain qa --json"
Sleep 300ms
Enter
Sleep 4s

Type "assgen --yaml server config show"
Sleep 300ms
Enter
Sleep 3s

Sleep 500ms
