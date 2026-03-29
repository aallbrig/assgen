Require assgen

Source demos/_settings.tape

Output demos/segments/02_task_tree.mp4

# ── Task Tree ──
Hide
Type "clear"
Enter
Show

Sleep 300ms
Type "printf '\\n  \\033[1;36m── Task Tree ──\\033[0m\\n\\n'"
Enter
Sleep 1s

Type "assgen tasks --domain visual"
Sleep 300ms
Enter
Sleep 5s

Type "assgen tasks --domain audio"
Sleep 300ms
Enter
Sleep 4s

Sleep 500ms
