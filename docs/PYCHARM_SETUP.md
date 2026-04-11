# PyCharm IDE Setup Guide for assgen

This guide explains how to use the preconfigured PyCharm run configurations for faster development.

## Quick Start

1. **Open the project** in PyCharm: `File > Open` → select `/path/to/assgen`
2. **Configure Python interpreter** (if needed): `Settings > Project > Python Interpreter` → Select or add Python 3.11+
3. **Select a run configuration** from the Run dropdown (top-right toolbar)
4. **Click Run** (▶ button) or press Shift+F10

## Available Run Configurations

### 1. **assgen (CLI)**
- **What it does:** Runs the `assgen` client CLI directly
- **Use case:** Test CLI commands during development (e.g., `assgen version`, `assgen models list`)
- **How to run:** Select "assgen (CLI)" from Run dropdown, then add command arguments in the Run Parameters field
- **Keyboard shortcut:** Shift+F10 (after selecting this config)

### 2. **assgen-server start**
- **What it does:** Starts the `assgen-server` locally with the debugger attached
- **Use case:** Debug server-side issues; hit breakpoints in FastAPI handlers
- **How to run:** Select "assgen-server start" and click Run. The server will start on the configured host/port (default: http://localhost:8000)
- **Stop the server:** Press Ctrl+C or click the Stop button (red square)

### 3. **pytest: all tests**
- **What it does:** Runs all pytest tests, skipping integration tests (marked with `@pytest.mark.integration`)
- **Use case:** Quick feedback loop during development
- **How to run:** Select "pytest: all tests" and click Run
- **Parameters:** `-m "not integration"` (skips HuggingFace API calls)

### 4. **pytest: watch mode**
- **What it does:** Runs tests continuously in watch mode — re-runs tests whenever you save a file
- **Use case:** TDD-style development; see test results instantly as you code
- **How to run:** Select "pytest: watch mode" and click Run. Tests will re-run automatically
- **Requirements:** pytest-watch package must be installed (`pip install pytest-watch`)
- **Stop watching:** Press Ctrl+C or click the Stop button

### 5. **pytest: debug mode**
- **What it does:** Runs tests with the PyCharm debugger enabled and `-s` flag (show print statements)
- **Use case:** Debug test failures; set breakpoints in test code or production code
- **How to run:** Select "pytest: debug mode" and click Run
- **Debugging:**
  - Click in the left margin of a line to set a breakpoint
  - When execution reaches the breakpoint, the debugger will pause and show variables
  - Use the Debug toolbar to step through code (F10 step over, F11 step into)

### 6. **pytest: with profiling**
- **What it does:** Runs tests with performance profiling enabled (`--profile --profile-svg`)
- **Use case:** Identify performance bottlenecks; generate flamegraph SVG reports
- **How to run:** Select "pytest: with profiling" and click Run
- **Output:** Profiling data is saved to `.pytest-prof/` directory in the project root
- **View results:** Open the `.svg` files in a browser to see the flamegraph
- **Requirements:** pytest-benchmark or similar profiling plugin (optional, may require: `pip install pytest-benchmark`)

## Common Workflows

### Workflow 1: Test-Driven Development (TDD)
1. Write a failing test in `tests/`
2. Select **pytest: watch mode**
3. Click Run
4. Watch tests re-run automatically as you modify code
5. When tests pass, you're done!

### Workflow 2: Debug a Failing Test
1. Select **pytest: debug mode**
2. Click in the left margin next to the line you want to pause on (set breakpoint)
3. Click Run
4. When execution hits the breakpoint, inspect variables in the Variables panel
5. Use F10 (step over) or F11 (step into) to navigate
6. Press Shift+F9 to continue execution

### Workflow 3: Debug the Server
1. Select **assgen-server start**
2. Set breakpoints in server code (e.g., `src/assgen/server/app.py`, `src/assgen/server/routes/`)
3. Click Run
4. In another terminal or with the assgen CLI, make requests to the server
5. Breakpoints will trigger, and you can inspect server state

### Workflow 4: Performance Profile Tests
1. Select **pytest: with profiling**
2. Click Run
3. Tests run with profiling enabled
4. After completion, check `.pytest-prof/*.svg` for flamegraphs
5. Open SVGs in a browser to identify slow functions

## Configuration Files

The `.idea/` directory contains the following shared configurations (version-controlled):

| File | Purpose |
|------|---------|
| `.idea/.gitignore` | Allow-list for versioned configs (ignore workspace.xml, keep runConfigurations/*.xml) |
| `.idea/misc.xml` | Python interpreter and code style settings |
| `.idea/modules.xml` | Project module structure |
| `.idea/vcs.xml` | Git repository mapping |
| `.idea/runConfigurations/` | All 6 run configurations (XML format) |
| `.idea/inspectionProfiles/` | Code inspection and linter rules |

**Note:** `workspace.xml` is **not** versioned (contains user session state like window layout).

## Troubleshooting

### "Python interpreter not found"
- Go to `Settings > Project > Python Interpreter`
- Click "Add Interpreter" and select your Python 3.11+ installation or `.venv/bin/python`

### "Module 'assgen' not found"
- Ensure the project root is marked as a source root: `Right-click project folder > Mark Directory as > Sources Root`
- Or configure the Python path: `Settings > Project > Python Interpreter > Show All > Edit > Add paths to `.../assgen/src`

### Tests won't run
- Ensure pytest is installed: `pip install pytest pytest-asyncio`
- Check that `tests/` folder exists and contains `__init__.py` and test files

### Watch mode doesn't restart tests
- Ensure pytest-watch is installed: `pip install pytest-watch`
- Check file system watcher limit: `cat /proc/sys/fs/inotify/max_user_watches` (should be high, e.g., 524288)

### Debugger doesn't pause at breakpoints
- Ensure the breakpoint is set (red dot in the left margin)
- Ensure you're using the correct run configuration (not the standard "Run" button)
- Try restarting PyCharm

## Next Steps

- **Explore the code:** Start in `src/assgen/client/cli.py` (client CLI) or `src/assgen/server/app.py` (server FastAPI app)
- **Read docs:** Check `docs/` directory for architecture and API documentation
- **Run tests:** Try `pytest: all tests` to see the project structure through test cases
- **Start contributing:** Pick a test or feature, use these run configs to develop faster!

---

**Questions?** Check the [main README](../../README.md) or [full docs](../../docs/).
