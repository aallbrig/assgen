"""Handler for narrative.i18n.extract — extract localisation string keys.

Recursively scans JSON files, extracts the values of a configurable key field,
and outputs an i18n template JSON and CSV.

Outputs:
    i18n_template.json — {"strings": [{"key": "...", "source_file": "...", "value": "..."}]}
    i18n_template.csv  — key,value,source_file

Params:
    directory (str):   root directory to scan
    pattern   (str):   glob pattern for files (default "**/*.json")
    key_field (str):   JSON field to extract as translatable string (default "text")
"""
from __future__ import annotations

_AVAILABLE = True  # pure Python stdlib


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Extract localisation keys from JSON files."""
    import csv
    import json
    from pathlib import Path

    directory = params.get("directory", "")
    if not directory:
        raise ValueError("'directory' parameter is required")
    dir_path = Path(directory)
    if not dir_path.is_dir():
        raise ValueError(f"Directory not found: {directory}")

    pattern: str = params.get("pattern", "**/*.json")
    key_field: str = params.get("key_field", "text")

    files = sorted(dir_path.glob(pattern))
    progress_cb(0.0, f"Scanning {len(files)} files for key '{key_field}'")

    strings: list[dict] = []
    seen_values: dict[str, int] = {}  # value → index, for dedup tracking

    def _extract(obj, source_rel: str) -> None:
        """Recursively walk obj and collect key_field values."""
        if isinstance(obj, dict):
            if key_field in obj and isinstance(obj[key_field], str):
                val = obj[key_field]
                # Generate a stable key from value hash
                import hashlib
                short_hash = hashlib.md5(val.encode()).hexdigest()[:8]
                strings.append({
                    "key": f"str_{short_hash}",
                    "value": val,
                    "source_file": source_rel,
                })
            for v in obj.values():
                _extract(v, source_rel)
        elif isinstance(obj, list):
            for item in obj:
                _extract(item, source_rel)

    for i, f in enumerate(files):
        rel = str(f.relative_to(dir_path))
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            _extract(data, rel)
        except Exception:
            pass
        progress_cb(0.1 + 0.7 * (i + 1) / max(1, len(files)), "")

    progress_cb(0.85, "Writing template files")
    json_path = Path(output_dir) / "i18n_template.json"
    csv_path = Path(output_dir) / "i18n_template.csv"

    json_path.write_text(json.dumps({"strings": strings}, indent=2))

    with csv_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["key", "value", "source_file"])
        writer.writeheader()
        writer.writerows(strings)

    progress_cb(1.0, "Done")
    return {
        "files": [str(json_path), str(csv_path)],
        "metadata": {
            "string_count": len(strings),
            "file_count": len(files),
            "key_field": key_field,
        },
    }
