"""Handler for narrative.dialogue.validate — lint assgen dialogue JSON format.

Checks a dialogue JSON for:
  - Orphan nodes (referenced but never defined)
  - Dead ends (no choices and no "exit" flag)
  - Missing required keys (id, text)

Expected dialogue format:
  {"nodes": [{"id": "...", "text": "...", "choices": [{"text": "...", "next": "..."}], "exit": bool}]}

Outputs:
    validation_report.json — {errors: [...], warnings: [...], node_count: N}

Params:
    input (str): path to dialogue JSON file
"""
from __future__ import annotations

_AVAILABLE = True  # pure Python


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Validate a dialogue JSON file."""
    import json
    from pathlib import Path

    input_path = params.get("input", "")
    if not input_path:
        raise ValueError("'input' parameter (dialogue JSON path) is required")
    if not Path(input_path).exists():
        raise ValueError(f"Input file not found: {input_path}")

    progress_cb(0.0, "Loading dialogue JSON")
    try:
        data = json.loads(Path(input_path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc

    errors: list[str] = []
    warnings: list[str] = []

    nodes = data.get("nodes")
    if nodes is None:
        errors.append("Top-level key 'nodes' is missing")
        return _result(errors, warnings, 0, output_dir)

    if not isinstance(nodes, list):
        errors.append("'nodes' must be a list")
        return _result(errors, warnings, 0, output_dir)

    progress_cb(0.2, f"Checking {len(nodes)} nodes")

    defined_ids: set[str] = set()
    referenced_ids: set[str] = set()
    start_ids: list[str] = []

    for idx, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(f"Node #{idx} is not an object")
            continue

        node_id = node.get("id")
        if not node_id:
            errors.append(f"Node #{idx} missing required key 'id'")
            node_id = f"<unnamed_{idx}>"
        if "text" not in node:
            errors.append(f"Node '{node_id}' missing required key 'text'")

        defined_ids.add(node_id)
        if idx == 0:
            start_ids.append(node_id)

        choices = node.get("choices", [])
        is_exit = bool(node.get("exit", False))

        if not choices and not is_exit:
            warnings.append(f"Node '{node_id}' is a dead end (no choices and no exit flag)")

        if not isinstance(choices, list):
            errors.append(f"Node '{node_id}'.choices must be a list")
        else:
            for ci, choice in enumerate(choices):
                if not isinstance(choice, dict):
                    errors.append(f"Node '{node_id}'.choices[{ci}] is not an object")
                    continue
                if "text" not in choice:
                    errors.append(f"Node '{node_id}'.choices[{ci}] missing 'text'")
                next_id = choice.get("next")
                if next_id:
                    referenced_ids.add(next_id)

    progress_cb(0.7, "Checking for orphan nodes")
    orphans = referenced_ids - defined_ids
    for oid in sorted(orphans):
        errors.append(f"Orphan node referenced but not defined: '{oid}'")

    unreachable = defined_ids - referenced_ids - set(start_ids)
    for uid in sorted(unreachable):
        warnings.append(f"Node '{uid}' is never referenced (possibly unreachable)")

    return _result(errors, warnings, len(nodes), output_dir)


def _result(errors, warnings, node_count, output_dir):
    import json
    from pathlib import Path

    report = {"errors": errors, "warnings": warnings, "node_count": node_count}
    out_path = Path(output_dir) / "validation_report.json"
    out_path.write_text(json.dumps(report, indent=2))
    return {
        "files": [str(out_path)],
        "metadata": {
            "error_count": len(errors),
            "warning_count": len(warnings),
            "node_count": node_count,
        },
    }
