Require assgen

Source demos/_settings.tape

Output demos/segments/10_upgrade.mp4

# ── Upgrade Check ──
Hide
Type "clear"
Enter
Show

Sleep 300ms
Type "printf '\\n  \\033[1;36m── Upgrade Check ──\\033[0m\\n\\n'"
Enter
Sleep 1s

Type "assgen upgrade --check"
Sleep 300ms
Enter
Sleep 4s

Sleep 500ms
