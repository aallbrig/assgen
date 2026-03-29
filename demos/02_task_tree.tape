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

Type "FORCE_COLOR=1 assgen tasks --domain visual | less -R"
Sleep 300ms
Enter
Sleep 2s

PageDown
Sleep 2s

PageDown
Sleep 2s

Type "q"
Sleep 1s

Type "assgen tasks --domain audio"
Sleep 300ms
Enter
Sleep 4s

Sleep 500ms
