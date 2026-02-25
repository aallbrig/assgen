"""Version introspection for assgen.

At build time, hatch-vcs writes version info into _version.py.
At development time (editable installs), we fall back to querying git directly.
"""
from __future__ import annotations

import subprocess
import sys
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def get_version_info() -> dict[str, str | None]:
    """Return a dict with version, commit, tag, and python fields."""
    version, commit, tag = _resolve_version()
    return {
        "version": version,
        "commit": commit,
        "tag": tag,
        "python": sys.version.split()[0],
    }


def format_version_string(name: str = "assgen") -> str:
    """Return a human-readable version string suitable for --version output."""
    info = get_version_info()
    parts = [f"{name} {info['version']}"]
    details = []
    if info["commit"]:
        details.append(f"commit: {info['commit'][:8]}")
    if info["tag"]:
        details.append(f"tag: {info['tag']}")
    details.append(f"python: {info['python']}")
    if details:
        parts.append(f"({', '.join(details)})")
    return " ".join(parts)


def _resolve_version() -> tuple[str, str | None, str | None]:
    """Try _version.py first, then git, then a safe fallback."""
    # 1. Try the build-generated _version.py
    try:
        from assgen._version import __version__  # type: ignore[import]
        if __version__ and __version__ != "0+unknown":
            commit = _git_commit()
            tag = _git_tag()
            return __version__, commit, tag
    except ImportError:
        pass

    # 2. Try git directly (works in an editable / source checkout)
    commit = _git_commit()
    tag = _git_tag()
    version = tag.lstrip("v") if tag else (f"0.0.0.dev+{commit[:8]}" if commit else "0.0.0.dev")
    return version, commit, tag


def _run_git(*args: str) -> str | None:
    """Run a git command from the repo root; return stdout or None on failure."""
    repo_root = Path(__file__).resolve().parents[3]  # src/assgen → repo root (4 levels up)
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            text=True,
            timeout=3,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


def _git_commit() -> str | None:
    return _run_git("rev-parse", "--short", "HEAD")


def _git_tag() -> str | None:
    """Return the most recent tag that points at HEAD, or None."""
    return _run_git("describe", "--tags", "--exact-match", "--abbrev=0")
