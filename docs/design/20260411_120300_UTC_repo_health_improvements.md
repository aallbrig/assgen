# Repository Health Improvements — Actionable Checklist

_Generated: 2026-04-11 12:03:00 UTC_

This document lists cheap, high-impact improvements to the assgen repo. Each item is
self-contained — an implementing agent can execute it without reading the rest.
Items are ordered by impact-to-effort ratio.

---

## Priority 0 — Blockers (required before HuggingFace Spaces can go live)

### 0.1 Add PyPI publish step to `release.yml`

**Problem:** `release.yml` builds the wheel/sdist with `hatch build` and attaches them to the
GitHub Release, but **never uploads to PyPI**. The release notes in the same file already
advertise `pip install assgen==<version>` — but that command fails for users.
Homebrew, Chocolatey, Docker, and PyInstaller binaries all work. PyPI does not.

This is a blocker for HuggingFace Spaces: each Space's `requirements.txt` needs
`assgen[spaces]==<version>` from PyPI. Without a published package, Spaces cannot install.

**Fix:** In `.github/workflows/release.yml`, add one step to the `release` job
**after** the `Build distribution packages` step and **before** `Build docs site`:

```yaml
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          skip-existing: true
```

The `id-token: write` permission is already present. This uses OIDC Trusted Publishing
— no `PYPI_API_TOKEN` secret needed.

**One-time manual PyPI setup (do before merging this change):**
1. pypi.org → Account Settings → Publishing → Add a new pending publisher
2. Owner: `aallbrig` | Repository: `assgen` | Workflow: `release.yml` | Environment: (blank)
3. The project name `assgen` must match `[project] name` in `pyproject.toml` exactly

**Full spec:** See `20260411_120400_UTC_hf_spaces_packaging_and_sdk.md` Section 1.

### 0.2 Add `[spaces]` extra to `pyproject.toml`

**Problem:** The `[inference]` extra covers torch/transformers/diffusers/trimesh/Pillow but
misses packages that several handlers require: pydub, scipy, matplotlib, pyfqmr, xatlas, TTS,
basicsr, realesrgan. HF Spaces need a single installable extra that covers all of these.

**Fix:** Add to `pyproject.toml` under `[project.optional-dependencies]`:
```toml
spaces = [
    "transformers>=4.40",
    "torch>=2.3",
    "diffusers>=0.28",
    "accelerate>=0.30",
    "trimesh>=3.21",
    "Pillow>=10.0",
    "pydub>=0.25",
    "pyloudnorm>=0.1",
    "scipy>=1.13",
    "matplotlib>=3.8",
    "pyfqmr>=0.2",
    "xatlas>=0.0.9",
    "TTS>=0.22",
    "basicsr>=1.4.2",
    "realesrgan>=0.3.0",
]
```

**Note:** `audiocraft` cannot be included (not on PyPI). Spaces that need it add it via git
install in their generated `requirements.txt`. See `sync_spaces.py` in Section 5 of
`20260411_120400_UTC_hf_spaces_packaging_and_sdk.md`.

### 0.3 Create `assgen.sdk` module

**Problem:** No public Python API exists for calling handlers programmatically. HF Spaces
would have to import from `assgen.server.worker` (an internal module) and know the full
handler calling convention. This needs a stable, public entry point.

**Fix:** Create `src/assgen/sdk.py` per the spec in Section 2 of
`20260411_120400_UTC_hf_spaces_packaging_and_sdk.md`. (~85 lines)

---

## Priority 1 — Quick Wins (< 15 minutes each)

### 1.1 Add "Development Setup" section to README.md

**Problem:** The README explains how to `pip install assgen` (user install) but gives zero
instructions for contributors or anyone who cloned the repo and wants to run from source.
There is a `.venv/` directory in the repo, implying this is the expected workflow, but it is
never mentioned. First-time contributors will be confused.

**Fix:** Insert the following section into README.md **before** the "CLI Command Tree" section
(after the Quick Start section, around line 80):

```markdown
## Development Setup

Clone and run from source:

```bash
git clone https://github.com/aallbrig/assgen.git
cd assgen

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows PowerShell

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# For GPU inference (optional — needs CUDA-capable GPU):
pip install -e ".[dev,inference]"

# Verify the install
assgen version
assgen-server --help
```

Run tests:

```bash
pytest -v
```

Run the linter:

```bash
ruff check src/ tests/
```

Build the docs locally:

```bash
pip install -e ".[docs]"
mkdocs serve          # opens http://localhost:8000
```

> **Version note:** assgen uses `hatch-vcs` to derive its version from git tags.
> If you install without a git tag (fresh clone, no tags), the version will appear as `0.1.dev0`.
> Run `git tag v0.1.0` to set a version, or ignore the warning — it does not affect functionality.
```

---

### 1.2 Add `.python-version` file

**Problem:** The project targets Python 3.11+ (per pyproject.toml), but there is no `.python-version`
file. Developers using `pyenv`, `asdf`, or `uv` will not get automatic Python version selection.

**Fix:** Create `/home/aallbright/src/assgen/.python-version` with this exact content:
```
3.11
```

---

### 1.3 Add `Makefile` with common dev commands

**Problem:** Contributors have to remember multiple commands (`pytest`, `ruff check src/ tests/`,
`mkdocs serve`). A Makefile lowers the friction to contribution.

**Fix:** Create `/home/aallbright/src/assgen/Makefile` with the following content:

```makefile
.PHONY: dev test lint docs clean

# Install in editable mode with all dev dependencies
dev:
	pip install -e ".[dev,inference]"

# Run the full test suite
test:
	pytest -v

# Run the full test suite with coverage
test-cov:
	pytest -v --cov=src/assgen --cov-report=term-missing --cov-report=html

# Lint and auto-fix
lint:
	ruff check --fix src/ tests/

# Lint without auto-fix (CI mode)
lint-check:
	ruff check src/ tests/

# Build and serve docs locally
docs:
	pip install -e ".[docs]"
	mkdocs serve

# Build docs static site
docs-build:
	mkdocs build

# Run the server locally (foreground, auto-device)
serve:
	assgen-server start --log-level debug

# Remove build artifacts and caches
clean:
	rm -rf dist/ build/ .pytest_cache/ htmlcov/ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
```

---

### 1.4 Add `pytest-cov` to dev dependencies and coverage config

**Problem:** `pyproject.toml` does not include `pytest-cov` as a dev dependency, and there is no
coverage configuration. Running `pytest --cov` will fail for new contributors.

**Fix:** In `pyproject.toml`, add `pytest-cov>=5.0` to the `[dev]` optional dependencies list,
and add a `[tool.coverage.run]` section:

Find this block in pyproject.toml:
```toml
[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.23",
    "ruff>=0.4",
    "httpx>=0.27",
]
```

Change it to:
```toml
[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
    "ruff>=0.4",
    "httpx>=0.27",
]
```

Then add at the end of `pyproject.toml`:
```toml
[tool.coverage.run]
source = ["src/assgen"]
omit = ["*/tests/*", "*/_version.py"]

[tool.coverage.report]
show_missing = true
skip_covered = false
```

---

### 1.5 Document the `assgen-server` vs `assgen server` distinction in README

**Problem:** The README Quick Start uses `assgen-server start --daemon`, but the CLI tree
shows `assgen server` as a subcommand. These are two different things:
- `assgen-server` — the standalone server entry point (direct process)
- `assgen server` — client-side commands to manage a server process (start/stop/status via the client)

This is confusing. The README should clarify this.

**Fix:** Add this note below the Quick Start code block in README.md:

```markdown
> **`assgen-server` vs `assgen server`:**
> - `assgen-server start` — runs the inference server directly (the process itself)
> - `assgen server start` — tells the client to launch a local `assgen-server` process for you
> - `assgen server status` / `assgen server stop` — manage the locally auto-started server
>
> For a remote GPU machine, run `assgen-server start --daemon` there, then on your laptop:
> `assgen client config set-server http://<gpu-machine>:8432`
```

---

### 1.6 Document Swagger UI access in README

**Problem:** The server exposes `/docs` (Swagger UI) and `/redoc` for API exploration, but
this is nowhere mentioned in the README or Quick Start. New users trying the server won't
know they can explore the API interactively.

**Fix:** Add to the README Quick Start, after the server start line:
```markdown
# Once the server is running, explore the REST API interactively:
# http://127.0.0.1:8432/docs      (Swagger UI)
# http://127.0.0.1:8432/redoc     (ReDoc)
# http://127.0.0.1:8432/health    (health check)
```

---

## Priority 2 — Medium Effort (< 30 minutes each)

### 2.1 Add GitHub Issue Templates

**Problem:** Issues filed against the repo have no structured format. Bug reports don't include
hardware info, Python version, or error output. Feature requests don't have context.

**Fix:** Create `.github/ISSUE_TEMPLATE/bug_report.md`:
```markdown
---
name: Bug report
about: Something isn't working
labels: bug
---

**Describe the bug**
A clear description of what went wrong.

**To Reproduce**
```bash
# exact command that failed
assgen gen audio sfx generate "example prompt"
```

**Expected behavior**
What you expected to happen.

**Error output**
```
paste full error / traceback here
```

**Environment**
- OS: [e.g. Ubuntu 22.04]
- Python: [e.g. 3.11.9]
- assgen version: [output of `assgen version`]
- Install type: [pip / source / docker]
- GPU: [e.g. RTX 4070 12 GB, or "CPU only"]
- CUDA version (if GPU): [e.g. 12.4]
```

Create `.github/ISSUE_TEMPLATE/feature_request.md`:
```markdown
---
name: Feature request
about: Suggest a new generation command or capability
labels: enhancement
---

**What asset type or workflow would this enable?**

**Describe the proposed command**
```bash
assgen gen <domain> <command> --example-flag value
```

**What model or algorithm would power it?**
Link to the HuggingFace model or algorithm paper if applicable.

**Are you willing to contribute this?**
[ ] Yes, I'd like to implement this
[ ] No, requesting for someone else to pick up
```

---

### 2.2 Add `CHANGELOG.md` stub

**Problem:** There is no changelog. Contributors and users cannot see what changed between versions.

**Fix:** Create `/home/aallbright/src/assgen/CHANGELOG.md`:
```markdown
# Changelog

All notable changes to assgen are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- (entries go here as features are developed)

### Changed

### Fixed

---

_Older entries will be added as the project matures._
```

---

### 2.3 Add `ruff` config section to `pyproject.toml`

**Problem:** `ruff check src/ tests/` runs with default settings. There is no explicit ruff
configuration in `pyproject.toml`, which means linting rules may change unexpectedly when
ruff updates. Additionally, the default ruff rules may be too strict or too lenient for this project.

**Fix:** Add to `pyproject.toml`:
```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "B",    # flake8-bugbear
    "UP",   # pyupgrade
]
ignore = [
    "E501",  # line too long (handled by formatter)
    "B008",  # do not perform function calls in default arguments
]

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["S101"]  # allow assert in tests
```

---

### 2.4 Add `pytest` config section to `pyproject.toml`

**Problem:** `pytest` configuration is not in `pyproject.toml`. Without it, test discovery
settings, markers, and asyncio mode must be specified per-run or may use unexpected defaults.

**Fix:** Add to `pyproject.toml`:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "-v --tb=short"
markers = [
    "slow: tests that run real model inference (skip with -m 'not slow')",
    "gpu: tests that require a CUDA GPU",
]
```

---

### 2.5 Clarify the `[inference]` extra in README

**Problem:** The README shows `pip install "assgen[inference]"` but doesn't explain what it adds
or when you need it. A user might install without it and be surprised that generation commands
return stubs.

**Fix:** Below the Installation section, add:
```markdown
> **`[inference]` extra:** Installs `torch`, `transformers`, `diffusers`, `accelerate`, and
> `trimesh` for local GPU inference. Without it, assgen is a fully functional client that can
> talk to a remote `assgen-server`, but a local server will return stub outputs instead of
> running real models.
>
> For CI environments or machines without a GPU, `pip install assgen` (without `[inference]`)
> is the right choice.
```

---

## Priority 3 — Larger Improvements (1–2 hours each)

### 3.1 Add `mypy` or `pyright` type checking

**Problem:** The codebase uses type annotations throughout, but there is no static type checker
configured. Type errors can slip through ruff linting.

**Fix:**
1. Add `mypy>=1.10` to dev dependencies.
2. Add to `pyproject.toml`:
   ```toml
   [tool.mypy]
   python_version = "3.11"
   strict = false
   ignore_missing_imports = true
   check_untyped_defs = true
   warn_redundant_casts = true
   warn_unused_ignores = true
   ```
3. Add `make typecheck` target to Makefile:
   ```makefile
   typecheck:
       mypy src/assgen/
   ```
4. Optionally add `mypy` to the CI workflow after ruff passes.

---

### 3.2 Add CI badge for test coverage and set a minimum threshold

**Problem:** There are no coverage metrics visible on the README or enforced in CI.

**Fix:**
1. In `.github/workflows/ci.yml`, add a coverage step:
   ```yaml
   - name: Run tests with coverage
     run: pytest -v --cov=src/assgen --cov-report=xml --cov-fail-under=60
   ```
2. Upload to codecov.io (free for open source) or use the GitHub Actions summary.
3. Add a coverage badge to README.md.
4. The `--cov-fail-under=60` threshold is a reasonable starting point given the stub handlers.
   Increase incrementally as real inference coverage grows.

---

### 3.3 Add pre-commit configuration

**Problem:** Contributors may not run `ruff check` before committing, leading to lint failures
in CI that slow down the review process.

**Fix:** Create `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.4
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

Add to README.md Contributing section:
```bash
# Install pre-commit hooks (one-time setup)
pip install pre-commit
pre-commit install
```

---

### 3.4 Add Docker Compose for local development

**Problem:** The `docker/` directory exists but its purpose and usage are not documented.
Contributors wanting to run the full stack (client + server + GPU) locally need guidance.

**Fix:**
1. Read the existing `docker/` directory contents to understand current state.
2. Create `docker/docker-compose.yml` with a `server` service and a `client` service.
3. Document in README.md under a "Docker" section how to run:
   ```bash
   docker compose -f docker/docker-compose.yml up server
   # then in another terminal:
   assgen client config set-server http://localhost:8432
   assgen audio sfx generate "test sound"
   ```

---

## Summary Table

| # | Item | Effort | Impact |
|---|------|--------|--------|
| 1.1 | Dev setup in README | 10 min | 🔥 High |
| 1.2 | `.python-version` file | 1 min | Medium |
| 1.3 | Makefile | 10 min | 🔥 High |
| 1.4 | pytest-cov + coverage config | 5 min | Medium |
| 1.5 | Document server vs server-cmd | 5 min | Medium |
| 1.6 | Document Swagger UI | 2 min | Medium |
| 2.1 | GitHub Issue Templates | 20 min | Medium |
| 2.2 | CHANGELOG.md stub | 5 min | Low |
| 2.3 | ruff config in pyproject.toml | 10 min | Medium |
| 2.4 | pytest config in pyproject.toml | 5 min | Medium |
| 2.5 | Clarify `[inference]` extra | 5 min | Medium |
| 3.1 | mypy / pyright | 1 hr | Medium |
| 3.2 | CI coverage badge | 30 min | Low |
| 3.3 | pre-commit | 15 min | Medium |
| 3.4 | Docker Compose docs | 1.5 hr | Low |

**Recommended execution order for a single agent pass:**
1.1 → 1.3 → 1.2 → 2.3 → 2.4 → 1.4 → 1.5 → 1.6 → 2.5 → 2.2 → 2.1 → stop.

Items 3.x can wait until after the HF Spaces work is done.
