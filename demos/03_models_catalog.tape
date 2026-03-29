Require assgen

Source demos/_settings.tape

Output demos/segments/03_models_catalog.mp4

# ── Model Catalog ──
Hide
Type "clear"
Enter
Show

Sleep 300ms
Type "printf '\\n  \\033[1;36m── Model Catalog ──\\033[0m\\n\\n'"
Enter
Sleep 1s

Type "FORCE_COLOR=1 assgen models list | less -R"
Sleep 300ms
Enter
Sleep 2s

PageDown
Sleep 2s

PageDown
Sleep 2s

Type "q"
Sleep 500ms
