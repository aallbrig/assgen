"""Handler for pipeline.asset.rename — batch rename assets to a naming convention.

Renames files in a directory to snake_case, PascalCase, or kebab-case.
Supports optional prefix/suffix and a dry-run mode.

Outputs:
    rename_plan.json — (dry-run) list of {from, to} pairs
    rename_report.json — (live) list of {from, to, status}

Params:
    directory  (str):   directory containing files to rename
    convention (str):   "snake_case" | "PascalCase" | "kebab-case" (default "snake_case")
    prefix     (str):   optional prefix to prepend (default "")
    suffix     (str):   optional suffix to insert before extension (default "")
    dry_run    (bool):  if true, only plan renames without executing (default true)
"""
from __future__ import annotations

import re
from pathlib import Path

_AVAILABLE = True  # pure Python


def _to_words(name: str) -> list[str]:
    """Split a filename stem into words, handling camel/pascal/snake/kebab."""
    # Insert spaces before uppercase letters following lowercase letters
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)
    # Replace separators with spaces
    s = re.sub(r"[-_ ]+", " ", s)
    return [w for w in s.strip().split(" ") if w]


def _snake_case(words: list[str]) -> str:
    return "_".join(w.lower() for w in words)


def _pascal_case(words: list[str]) -> str:
    return "".join(w.capitalize() for w in words)


def _kebab_case(words: list[str]) -> str:
    return "-".join(w.lower() for w in words)


_CONVERTERS = {
    "snake_case": _snake_case,
    "PascalCase": _pascal_case,
    "kebab-case": _kebab_case,
}


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Batch rename files to a naming convention."""
    import json

    directory = params.get("directory", "")
    if not directory:
        raise ValueError("'directory' parameter is required")
    dir_path = Path(directory)
    if not dir_path.is_dir():
        raise ValueError(f"Directory not found: {directory}")

    convention: str = params.get("convention", "snake_case")
    prefix: str = params.get("prefix", "") or ""
    suffix_str: str = params.get("suffix", "") or ""
    dry_run: bool = str(params.get("dry_run", "true")).lower() not in ("false", "0", "no")

    converter = _CONVERTERS.get(convention)
    if converter is None:
        raise ValueError(f"Unknown convention '{convention}'. Use: {list(_CONVERTERS)}")

    files = [f for f in dir_path.iterdir() if f.is_file()]
    plan: list[dict] = []

    progress_cb(0.0, f"Planning renames for {len(files)} files")

    for i, f in enumerate(files):
        stem = f.stem
        ext = f.suffix
        words = _to_words(stem)
        new_stem = prefix + converter(words) + suffix_str
        new_name = new_stem + ext
        plan.append({"from": f.name, "to": new_name, "status": "planned"})
        progress_cb(0.1 + 0.6 * (i + 1) / len(files), "")

    if dry_run:
        out_path = Path(output_dir) / "rename_plan.json"
        out_path.write_text(json.dumps({"dry_run": True, "renames": plan}, indent=2))
        progress_cb(1.0, "Dry-run complete")
        return {
            "files": [str(out_path)],
            "metadata": {"dry_run": True, "file_count": len(plan)},
        }

    # Execute renames
    progress_cb(0.7, "Executing renames")
    report: list[dict] = []
    seen: dict[str, int] = {}
    for entry in plan:
        src = dir_path / entry["from"]
        new_name = entry["to"]
        # Handle collisions
        key = new_name.lower()
        if key in seen:
            seen[key] += 1
            stem, ext2 = Path(new_name).stem, Path(new_name).suffix
            new_name = f"{stem}_{seen[key]}{ext2}"
        else:
            seen[key] = 0
        dst = dir_path / new_name
        try:
            src.rename(dst)
            report.append({"from": entry["from"], "to": new_name, "status": "renamed"})
        except Exception as exc:
            report.append({"from": entry["from"], "to": new_name, "status": f"error: {exc}"})

    out_path = Path(output_dir) / "rename_report.json"
    out_path.write_text(json.dumps({"dry_run": False, "renames": report}, indent=2))

    progress_cb(1.0, "Done")
    return {
        "files": [str(out_path)],
        "metadata": {"dry_run": False, "file_count": len(report)},
    }
