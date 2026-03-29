Require assgen

Source demos/_settings.tape

Output demos/segments/05_server.mp4

# ── Server Management ──
Hide
Type "clear"
Enter
Show

Sleep 300ms
Type "printf '\\n  \\033[1;36m── Server Management ──\\033[0m\\n\\n'"
Enter
Sleep 1s

Type "assgen server status"
Sleep 300ms
Enter
Sleep 3s

Type "assgen server config show"
Sleep 300ms
Enter
Sleep 3s

Sleep 500ms
