# Contributing

## Development Setup

```bash
git clone https://github.com/aallbrig/assgen.git
cd assgen
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,docs]"
```

Run tests:

```bash
pytest -v
```

Run linter:

```bash
ruff check src tests
```

---

## Adding a New Inference Handler

Handlers live under `src/assgen/server/handlers/`.  Each handler is a module
that exposes a single async function:

```python
async def run(params: dict, model_path: str, device: str) -> dict:
    """Run inference and return output paths/data."""
    ...
```

Steps:

1. Create `src/assgen/server/handlers/my_task.py` implementing `run()`.
2. Add an entry to `src/assgen/catalog.yaml`:
   ```yaml
   catalog:
     my.domain.task:
       model_id: "org/repo"
       name: "My Model"
       task: "text-to-image"   # HF pipeline_tag category
       notes: "Optional notes"
   ```
3. Add the task to `src/assgen/tasks.py` in the appropriate domain.
4. Add a client sub-command under `src/assgen/client/commands/`.
5. Wire the sub-command into the parent Typer app.
6. Add compatibility tags in `TASK_COMPATIBLE_TAGS`
   (`src/assgen/server/validation.py`) if introducing a new task category.
7. Write tests in `tests/`.

### Google-style Docstrings

All public functions should use Google-style docstrings so that
`mkdocstrings` can render them correctly in the API reference:

```python
def my_function(model_id: str, params: dict) -> Path:
    """One-line summary.

    Longer description if needed.

    Args:
        model_id: HuggingFace model identifier in ``org/repo`` format.
        params: Arbitrary key/value pairs passed by the client.

    Returns:
        Local path to the generated output file.

    Raises:
        ValueError: If ``model_id`` is not compatible with this task.

    Example:
        >>> path = my_function("stabilityai/TripoSR", {"prompt": "sword"})
    """
```

---

## Docs

Build the docs site locally:

```bash
pip install -e ".[docs]"
mkdocs serve          # live-reload at http://127.0.0.1:8000
```

The docs are auto-deployed to GitHub Pages on every push to `main` and on
every version tag via the CI workflows in `.github/workflows/`.

---

## Release Process

1. Ensure all tests pass on `main`.
2. Tag a version: `git tag v0.x.y && git push --tags`
3. The `release.yml` workflow builds the wheel, runs tests, builds docs, and
   creates a GitHub Release with all assets attached automatically.
