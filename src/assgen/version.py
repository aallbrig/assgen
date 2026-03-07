"""Version introspection for assgen.

Canonical approach:
  1. ``importlib.metadata.version("assgen")`` is the *installed* version —
     the single source of truth.  hatch-vcs writes this from the git tag at
     ``pip install`` / ``pip install -e .`` time.
  2. ``git describe --tags --long --dirty`` surfaces the *current source state*
     so you can tell whether the working tree has changed since the install.
  3. The ``--version`` / ``-V`` flag on both CLIs combines these two pieces so
     you always know exactly what code is running.

Version string examples
-----------------------
* Production install from a tagged release wheel::

      assgen 0.1.0

* Editable install from a clean dev checkout (16 commits after v0.0.1)::

      assgen 0.0.2.dev16+gc9ee176
        source  v0.0.1-16-gc9ee176 (clean)
        python  3.12.2

* Editable install with uncommitted changes in the working tree::

      assgen 0.0.2.dev16+gc9ee176
        source  v0.0.1-16-gc9ee176-dirty  ⚠  uncommitted changes
        python  3.12.2
"""
from __future__ import annotations

import subprocess
import sys
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def get_version_info() -> dict[str, str | None]:
    """Return a dict with ``version``, ``git_describe``, ``dirty``, and ``python`` fields.

    * ``version``      — installed package version from :mod:`importlib.metadata`.
    * ``git_describe`` — output of ``git describe --tags --long --dirty``, or *None*
                         when git is unavailable (e.g. running from a wheel install).
    * ``dirty``        — ``True`` if the git working tree has uncommitted changes.
    * ``python``       — Python version string.
    """
    version = _installed_version()
    git_desc = _git_describe()
    dirty = git_desc.endswith("-dirty") if git_desc else False
    return {
        "version": version,
        "git_describe": git_desc,
        "dirty": dirty,
        "python": sys.version.split()[0],
    }


def format_version_string(name: str = "assgen") -> str:
    """Return a human-readable version string for ``--version`` output."""
    info = get_version_info()
    ver = info["version"] or "0.0.0.dev"
    lines = [f"{name} {ver}"]

    git_desc = info.get("git_describe")
    if git_desc:
        dirty_note = "  ⚠  uncommitted changes" if info["dirty"] else " (clean)"
        lines.append(f"  source  {git_desc}{dirty_note}")

    lines.append(f"  python  {info['python']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _installed_version() -> str:
    """Read the version from installed package metadata (canonical source).

    hatch-vcs writes this from the git tag at install time.  Works for both
    regular and editable installs as long as the package is installed in the
    active Python environment.
    """
    try:
        from importlib.metadata import version, PackageNotFoundError
        return version("assgen")
    except Exception:
        pass

    # Last-resort: read the build-generated _version.py written by hatch-vcs
    try:
        from assgen._version import __version__  # type: ignore[import]
        if __version__ and __version__ not in ("0+unknown", ""):
            return __version__
    except ImportError:
        pass

    return "0.0.0.dev"


def _git_describe() -> str | None:
    """Run ``git describe --tags --long --dirty`` and return the output.

    Returns *None* when:
    - git is not installed
    - the current directory is not inside a git repository (e.g. wheel install)
    - the repo has no tags yet
    """
    repo_root = Path(__file__).resolve().parents[2]
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "describe", "--tags", "--long", "--dirty"],
            capture_output=True,
            text=True,
            timeout=3,
            stdin=subprocess.DEVNULL,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return None

