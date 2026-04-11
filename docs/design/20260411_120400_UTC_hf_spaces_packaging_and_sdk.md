# HuggingFace Spaces — Packaging, SDK, and CI/CD Decisions

_Generated: 2026-04-11 12:04:00 UTC_

This document records the technical decisions that enable HuggingFace Spaces to use assgen
as a dependency rather than duplicating inference logic. Read this before touching the
Tier 1 or Tier 2/3 spec documents.

---

## 1. The PyPI Gap — Fix Required Before Any Space Goes Live

### Finding

`release.yml` correctly builds the Python wheel and sdist using `hatch build`, and attaches
those artifacts to the GitHub Release. However, there is **no step that publishes to PyPI**.

The release notes in `release.yml` already read `pip install assgen==<version>` — but without
a publish step, that command fails for users unless someone manually uploaded an artifact
previously.

Homebrew, Chocolatey, Docker, and PyInstaller binaries all work on tag. PyPI does not.

### Fix — add to `release.yml` in the `release` job, after `hatch build`

```yaml
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          # Uses Trusted Publishing (OIDC) — no API token needed.
          # One-time setup: go to pypi.org → your project → Publishing → add GitHub publisher:
          #   Owner: aallbrig   Repo: assgen   Workflow: release.yml   Environment: (leave blank)
          skip-existing: true
```

This must appear **after** the `Build distribution packages` step and **before** `Build docs site`
in the `release` job. The `id-token: write` permission is already present in the workflow's
`permissions` block.

**One-time manual setup (do this before merging):**
1. Log into pypi.org → Manage → Your projects → `assgen` (create it if it doesn't exist) →
   Publishing → Add a new publisher
2. Set: Owner=`aallbrig`, Repository=`assgen`, Workflow=`release.yml`, Environment=(blank)
3. Trusted Publishing (OIDC) means no `PYPI_API_TOKEN` secret is needed

### Why PyPI is a prerequisite for Spaces

HuggingFace Spaces build their Python environment from `requirements.txt` at Space startup.
If assgen is not on PyPI, the Space has two bad alternatives:
- `assgen @ git+https://github.com/aallbrig/assgen.git` — slow, fragile (pulls main HEAD)
- Bundling all handler code directly — duplicates logic, defeats the purpose

Once the PyPI step is merged, every Space's `requirements.txt` is simply:
```
assgen[spaces]
```

---

## 2. `assgen.sdk` — The Clean Python API for Spaces

### Why this module needs to exist

The handlers in `assgen.server.handlers.*` already contain all the inference logic.
The `_load_handler(job_type)` function in `worker.py` already does dynamic dispatch.
But both are internal APIs tied to the server context.

HuggingFace Spaces (and any other programmatic consumer) should not have to:
- Import from `assgen.server.worker` (internal module)
- Know the handler calling convention (`job_type, params, model_id, model_path, device, progress_cb, output_dir`)
- Manage output directories manually
- Deal with the stub handler silently returning a placeholder

`assgen.sdk` is a **25-line public wrapper** that exposes exactly what Spaces need.

### Module location and spec

**File to create:** `src/assgen/sdk.py`

```python
"""
assgen.sdk — public Python API for running assgen generation without the server.

Intended for HuggingFace Spaces, notebooks, and any programmatic consumer that
wants inference without the client-server HTTP stack.

Example::

    from assgen.sdk import run
    result = run("audio.sfx.generate", {"prompt": "sword clash", "duration": 2.0})
    print(result["files"])   # ['/tmp/abc123/sfx.wav']
"""
from __future__ import annotations

import importlib
import tempfile
from pathlib import Path
from typing import Any


def run(
    job_type: str,
    params: dict[str, Any],
    device: str = "auto",
    output_dir: Path | str | None = None,
    model_id: str | None = None,
) -> dict[str, Any]:
    """Run any assgen generation task as a pure Python call.

    No server process, no SQLite, no HTTP. Loads models on demand via HuggingFace Hub.

    Parameters
    ----------
    job_type:
        Dot-separated task identifier, e.g. ``"audio.sfx.generate"``,
        ``"visual.texture.generate"``, ``"narrative.dialogue.npc"``.
        Must match a key in ``catalog.yaml`` and a handler module in
        ``assgen.server.handlers``.
    params:
        Task-specific parameter dict. Keys match what the CLI passes internally.
        See the handler module's docstring for the full parameter spec.
    device:
        ``"auto"`` (default) resolves to ``"cuda"`` if a GPU is available, else ``"cpu"``.
        Pass ``"cuda"`` or ``"cpu"`` to override.
    output_dir:
        Directory to write output files into.  A temporary directory is created if not
        provided.  The directory persists after the call — the caller is responsible for
        cleanup (or use ``tempfile.TemporaryDirectory`` as a context manager).
    model_id:
        Override the catalog-default model ID. ``None`` = use catalog default.

    Returns
    -------
    dict
        ``"files"``: list of absolute path strings for every output file written.
        ``"metadata"``: handler-specific metadata dict.
        Additional keys may be present depending on the handler.

    Raises
    ------
    NotImplementedError
        If no handler module exists for *job_type*.
    RuntimeError
        If the handler raises (e.g. missing inference dependency).
    """
    # Resolve device
    if device == "auto":
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            device = "cpu"

    # Prepare output directory
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp())
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    # Resolve model_id from catalog if not overridden
    if model_id is None:
        try:
            # get_catalog() does not exist — use get_model_for_job() instead.
            from assgen.catalog import get_model_for_job
            entry = get_model_for_job(job_type) or {}
            model_id = entry.get("model_id")
        except Exception:
            model_id = None

    # Dispatch to handler
    handler = _load_handler(job_type)
    result = handler(
        job_type=job_type,
        params=params,
        model_id=model_id,
        model_path=None,   # handlers download from HF Hub cache themselves
        device=device,
        progress_cb=lambda p, msg: None,   # no-op; Spaces use gr.Progress instead
        output_dir=output_dir,
    )

    # Normalise relative filenames to absolute paths
    result["files"] = [
        str((output_dir / f).resolve()) if not Path(str(f)).is_absolute() else str(f)
        for f in result.get("files", [])
    ]
    return result


def _load_handler(job_type: str):
    """Import and return the run() callable for *job_type*.

    Unlike the server's ``_load_handler``, this raises ``NotImplementedError``
    rather than silently returning a stub — callers should know if a handler is missing.
    """
    module_name = "assgen.server.handlers." + job_type.replace(".", "_")
    try:
        mod = importlib.import_module(module_name)
        return mod.run  # type: ignore[attr-defined]
    except ModuleNotFoundError:
        raise NotImplementedError(
            f"No handler found for job_type '{job_type}'. "
            f"Expected module: {module_name}"
        )
```

### Surface area decision: `run()` only

The SDK exposes a single function. There are no per-task convenience wrappers
(`generate_sfx`, `compose_music`, etc.) — those would create maintenance burden
and duplicate the catalog. A Space that needs `generate_sfx` behavior just calls
`run("audio.sfx.generate", {...})`. The job_type string IS the API.

### Export from package root (optional but nice)

Add to `src/assgen/__init__.py`:
```python
from assgen.sdk import run as generate  # noqa: F401
```
This lets power users do `from assgen import generate` but is not required for Spaces.

---

## 3. The `[spaces]` Extra for `pyproject.toml`

The current `[inference]` extra is intentionally minimal (torch, transformers, diffusers,
accelerate, trimesh, Pillow). It does not cover several packages that handlers use.

Add a `[spaces]` extra that covers everything pip-installable that any Space handler needs:

```toml
[project.optional-dependencies]
spaces = [
    # Core inference (same as [inference])
    "transformers>=4.40",
    "torch>=2.3",
    "diffusers>=0.28",
    "accelerate>=0.30",
    "trimesh>=3.21",
    "Pillow>=10.0",
    # Audio processing
    "pydub>=0.25",
    "pyloudnorm>=0.1",
    "scipy>=1.13",
    # Visualization
    "matplotlib>=3.8",
    # Mesh utilities
    "pyfqmr>=0.2",
    "xatlas>=0.0.9",
    # Voice cloning
    "TTS>=0.22",
    # Upscaling
    "basicsr>=1.4.2",
    "realesrgan>=0.3.0",
]
```

**Why not call it `inference`?** The existing `[inference]` extra is already documented and
used in the README for GPU server setup. Changing it would be a breaking change.
`[spaces]` is additive.

### audiocraft — the pip gap

`audiocraft` (AudioGen, MusicGen, MusicGen Stereo) is **not on PyPI**. Meta distributes it
only via git. This means three Spaces — `assgen.audio.sfx.generate`,
`assgen.audio.music.compose`, `assgen.audio.ambient.generate`, `assgen.audio.music.loop` —
cannot rely solely on `assgen[spaces]`.

Their `requirements.txt` needs an additional line:
```
audiocraft @ git+https://github.com/facebookresearch/audiocraft.git
```

This is unavoidable until Meta publishes to PyPI. All other Spaces use `assgen[spaces]` only.

---

## 4. `spaces/` Directory in this Repo

### Decision: yes, keep Space source in this repo

Each Space is a ~35-line Gradio `app.py` that calls `assgen.sdk.run()` + a `README.md`
Space card. These belong in the assgen repo because:
- The `app.py` UI code is tested alongside the handlers it wraps
- A single `git tag vX.Y.Z` triggers both PyPI publish AND Space sync
- The Space always tracks the same version as the published package

### Directory layout

```
spaces/
├── _template/
│   ├── app.py            # Template for new Spaces (copy and modify)
│   └── README.md         # Template for HF Space card
├── assgen.audio.sfx.generate/
│   ├── app.py
│   └── README.md
├── assgen.audio.music.compose/
│   ├── app.py
│   └── README.md
├── assgen.audio.voice.tts/
│   ├── app.py
│   └── README.md
├── assgen.concept.generate/
│   ├── app.py
│   └── README.md
... (one directory per Space)
```

Each Space directory contains **exactly two files**:
- `app.py` — the Gradio UI (≤60 lines)
- `README.md` — the HF Space card YAML frontmatter + description

There is **no `requirements.txt` per Space directory**. Requirements are generated
dynamically by the sync workflow (see Section 5) because they differ by Space hardware tier.

### `spaces/_template/app.py`

```python
"""
assgen.<domain>.<command> — HuggingFace Space
<one-line description>

CLI equivalent: assgen gen <domain> <command> [args]
"""
from __future__ import annotations

import spaces
import gradio as gr
from assgen.sdk import run

JOB_TYPE = "domain.subdomain.command"   # ← change this


@spaces.GPU   # ← remove this decorator for CPU-only Spaces
def _run(param1: str, param2: float) -> str:
    result = run(JOB_TYPE, {"param1": param1, "param2": param2})
    return result["files"][0]   # or result["files"] for multiple outputs


with gr.Blocks(title="assgen · <Title>") as demo:
    gr.Markdown(
        "# assgen · <Title>\n"
        "<Short description of what this Space demonstrates.>\n"
        "Part of the [assgen](https://github.com/aallbrig/assgen) pipeline."
    )
    with gr.Row():
        with gr.Column():
            input1 = gr.Textbox(label="Input 1")
            input2 = gr.Slider(minimum=1, maximum=10, value=3, label="Input 2")
            btn = gr.Button("Generate", variant="primary")
        with gr.Column():
            output = gr.Audio(label="Output")   # ← change component type as needed

    btn.click(fn=_run, inputs=[input1, input2], outputs=output)

demo.launch()
```

### `spaces/_template/README.md`

```markdown
---
title: "assgen · <Title>"
emoji: 🎮
colorFrom: purple
colorTo: blue
sdk: gradio
sdk_version: "4.44.0"
app_file: app.py
pinned: false
license: apache-2.0
hardware: zero-gpu        # or: cpu-basic
tags:
  - game-assets
  - assgen
short_description: <One-line description>
---

# assgen · <Title>

<Description of what this Space does.>

Part of the [assgen](https://github.com/aallbrig/assgen) game asset generation pipeline.

**Model:** [model-org/model-name](https://huggingface.co/model-org/model-name)
**CLI equivalent:** `assgen gen <domain> <command>`
```

---

## 5. CI/CD — Space Sync on Release

### New workflow: `.github/workflows/spaces-sync.yml`

Triggers on the same semver tags as `release.yml`, but runs **after** the PyPI publish
step completes (via `workflow_run` trigger or by being a dependent job in `release.yml`).

**Add as a new job at the bottom of `release.yml`** (after the `release` job succeeds):

```yaml
  # ---------------------------------------------------------------------------
  # Sync HuggingFace Spaces on stable releases (not pre-releases)
  # ---------------------------------------------------------------------------
  spaces-sync:
    name: Sync HuggingFace Spaces
    runs-on: ubuntu-latest
    needs: release          # wait for PyPI publish to complete first
    if: ${{ !contains(github.ref_name, '-') }}   # skip pre-releases

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip

      - name: Install HF CLI
        run: pip install huggingface_hub[cli]>=0.23

      - name: Authenticate HF CLI
        env:
          HF_TOKEN: ${{ secrets.HF_TOKEN }}
        run: hf login --token "$HF_TOKEN"

      - name: Sync all Spaces
        env:
          VERSION: ${{ github.ref_name }}
        run: python scripts/sync_spaces.py --version "$VERSION"
```

**Required secret:** `HF_TOKEN` — a HuggingFace write token for your account.
Generate at: huggingface.co → Settings → Access Tokens → New token (role: Write).

### `scripts/sync_spaces.py`

```python
#!/usr/bin/env python3
"""
Sync all spaces/ subdirectories to HuggingFace Hub.
Generates requirements.txt for each Space before uploading.
"""
from __future__ import annotations

import argparse
import tempfile
import shutil
from pathlib import Path

from huggingface_hub import HfApi

REPO_ROOT = Path(__file__).parent.parent
SPACES_DIR = REPO_ROOT / "spaces"

# Spaces that need audiocraft (not on PyPI — requires git install)
AUDIOCRAFT_SPACES = {
    "assgen.audio.sfx.generate",
    "assgen.audio.music.compose",
    "assgen.audio.music.loop",
    "assgen.audio.ambient.generate",
}

# Spaces that are CPU-only (no ZeroGPU needed)
CPU_SPACES = {
    "assgen.procedural.terrain.heightmap",
    "assgen.mesh.validate",
    "assgen.mesh.convert",
    "assgen.mesh.bounds",
    "assgen.mesh.center",
    "assgen.mesh.scale",
    "assgen.mesh.flipnormals",
    "assgen.mesh.weld",
    "assgen.texture.pbr",
    "assgen.texture.channel_pack",
    "assgen.texture.atlas_pack",
    "assgen.texture.mipmap",
    "assgen.texture.normalmap_convert",
    "assgen.texture.seamless",
    "assgen.texture.resize",
    "assgen.texture.report",
    "assgen.audio.process.normalize",
    "assgen.audio.process.trim_silence",
    "assgen.audio.process.convert",
    "assgen.audio.process.downmix",
    "assgen.audio.process.resample",
    "assgen.audio.process.loop_optimize",
    "assgen.audio.process.waveform",
    "assgen.procedural.level.dungeon",
    "assgen.procedural.texture.noise",
    "assgen.procedural.level.voronoi",
    "assgen.procedural.foliage.scatter",
    "assgen.procedural.plant.lsystem",
    "assgen.procedural.tileset.wfc",
    "assgen.scene.physics.collider",
    "assgen.lod.generate",
    "assgen.uv.auto",
    "assgen.sprite.pack",
}


def make_requirements(space_name: str, version: str) -> str:
    """Generate requirements.txt content for a Space."""
    lines = [f"assgen[spaces]=={version}"]
    if space_name in AUDIOCRAFT_SPACES:
        lines.append(
            "audiocraft @ git+https://github.com/facebookresearch/audiocraft.git"
        )
    return "\n".join(lines) + "\n"


def make_packages_txt(space_name: str) -> str | None:
    """Generate packages.txt for apt dependencies (if needed)."""
    audio_process_spaces = {s for s in CPU_SPACES if "audio.process" in s}
    if space_name in audio_process_spaces:
        return "ffmpeg\n"
    return None


def sync_space(space_name: str, version: str) -> None:
    space_dir = SPACES_DIR / space_name
    if not space_dir.exists():
        print(f"  SKIP  {space_name} (directory not found)")
        return

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Copy app.py and README.md
        shutil.copy(space_dir / "app.py", tmp_path / "app.py")
        shutil.copy(space_dir / "README.md", tmp_path / "README.md")

        # Generate requirements.txt
        (tmp_path / "requirements.txt").write_text(
            make_requirements(space_name, version)
        )

        # Generate packages.txt if needed
        pkgs = make_packages_txt(space_name)
        if pkgs:
            (tmp_path / "packages.txt").write_text(pkgs)

        # Push to HF Hub via stable Python API (not subprocess hf CLI,
        # which fails silently when the CLI argument format changes).
        api = HfApi()
        try:
            api.upload_folder(
                folder_path=str(tmp_path),
                repo_id=space_name,
                repo_type="space",
                commit_message=f"assgen {version}",
            )
            print(f"  OK    {space_name}")
        except Exception as exc:
            print(f"  ERROR {space_name}: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True, help="assgen version tag, e.g. v0.2.0")
    parser.add_argument("--space", help="sync only this space (for manual use)")
    args = parser.parse_args()

    version = args.version.lstrip("v")  # strip leading 'v' for pip version

    if args.space:
        spaces = [args.space]
    else:
        spaces = sorted(
            d.name for d in SPACES_DIR.iterdir()
            if d.is_dir() and not d.name.startswith("_")
        )

    print(f"Syncing {len(spaces)} space(s) — assgen {version}")
    for space_name in spaces:
        sync_space(space_name, version)

    print("Done.")


if __name__ == "__main__":
    main()
```

**Manual sync (for testing before a full release):**
```bash
# Push a single Space without a tag
python scripts/sync_spaces.py --version 0.2.0 --space assgen.audio.sfx.generate
```

---

## 6. What Each Tier 1 Space `app.py` Now Looks Like

With `assgen.sdk.run()`, every Space `app.py` follows the same ~35-line pattern.
The Tier 1 spec (`20260411_120100_UTC_hf_spaces_spec_tier1.md`) is updated to reflect this.

Example — `assgen.audio.sfx.generate/app.py`:
```python
"""assgen.audio.sfx.generate — HuggingFace Space"""
from __future__ import annotations
import spaces
import gradio as gr
from assgen.sdk import run

@spaces.GPU
def generate_sfx(description: str, duration: float) -> str:
    result = run(
        "audio.sfx.generate",
        {"prompt": description, "duration": duration},
        device="cuda",
    )
    return result["files"][0]

with gr.Blocks(title="assgen · Audio SFX Generator") as demo:
    gr.Markdown(
        "# 🔊 assgen · Audio SFX Generator\n"
        "Generate game sound effects from text. "
        "Part of the [assgen](https://github.com/aallbrig/assgen) pipeline."
    )
    with gr.Row():
        with gr.Column():
            prompt = gr.Textbox(label="Sound Effect Description",
                                placeholder="sword clashing against armor")
            duration = gr.Slider(label="Duration (seconds)",
                                 minimum=0.5, maximum=10.0, value=3.0, step=0.5)
            btn = gr.Button("Generate SFX", variant="primary")
        with gr.Column():
            audio = gr.Audio(label="Generated Sound Effect", type="filepath")

    gr.Examples(
        [["sword clashing against armor", 2.0],
         ["footsteps on stone floor", 3.0],
         ["explosion with debris", 2.5]],
        inputs=[prompt, duration], cache_examples=False,
    )
    btn.click(fn=generate_sfx, inputs=[prompt, duration], outputs=audio)

demo.launch()
```

`requirements.txt` (generated by `sync_spaces.py`, not stored in repo):
```
assgen[spaces]==0.2.0
audiocraft @ git+https://github.com/facebookresearch/audiocraft.git
```

---

## 7. Summary of Implementation Tasks for the Agent

In order of dependency:

| # | Task | File(s) | Notes |
|---|------|---------|-------|
| 1 | Add PyPI publish step | `.github/workflows/release.yml` | After `hatch build`, before `Build docs site` |
| 2 | Create `assgen.sdk` module | `src/assgen/sdk.py` | ~85 lines per spec above |
| 3 | Add `[spaces]` extra | `pyproject.toml` | New optional-dependencies section |
| 4 | Create `spaces/` directory | `spaces/` | Copy template, then implement Tier 1 first |
| 5 | Create `scripts/sync_spaces.py` | `scripts/sync_spaces.py` | Per spec above |
| 6 | Add `spaces-sync` job | `.github/workflows/release.yml` | After `release` job |
| 7 | Add `HF_TOKEN` secret | GitHub repo Settings → Secrets | Manual — cannot be automated |
| 8 | Implement Tier 1 Spaces | `spaces/assgen.*/app.py` + `README.md` | Using SDK pattern |
| 9 | Test single Space sync | `python scripts/sync_spaces.py --space assgen.audio.sfx.generate` | Before full release |
| 10 | Tag and release | `git tag v0.X.Y && git push --tags` | Full release pipeline fires |

Tasks 1–3 are source changes that require tests and PR review before merging.
Tasks 4–10 build on top once main is green.
