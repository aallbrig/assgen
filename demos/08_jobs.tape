Require assgen

Source demos/_settings.tape

Output demos/segments/08_jobs.mp4

# ── Job Management ──
Hide
Type "clear"
Enter
Show

Sleep 300ms
Type "printf '\\n  \\033[1;36m── Job Management ──\\033[0m\\n\\n'"
Enter
Sleep 1s

Type "assgen jobs list --limit 5"
Sleep 300ms
Enter
Sleep 4s

Sleep 500ms
