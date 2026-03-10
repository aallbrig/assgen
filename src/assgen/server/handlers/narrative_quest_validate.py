"""Handler for narrative.quest.validate — check a quest JSON graph for issues.

Validates a quest graph for:
  - Cycles (infinite loops)
  - Unreachable nodes from the start
  - Missing required keys (id, title/description)

Expected quest format:
  {"nodes": [{"id": "...", "title": "...", "next": ["id1", "id2"]}], "start": "node_id"}

Uses networkx if available; falls back to a pure-Python DFS.

Outputs:
    validation_report.json — {errors: [...], warnings: [...], node_count: N}

Params:
    input (str): path to quest JSON file
"""
from __future__ import annotations

_AVAILABLE = True  # pure Python (networkx optional)


def run(job_type, params, model_id, model_path, device, progress_cb, output_dir):
    """Validate a quest JSON graph."""
    import json
    from pathlib import Path

    input_path = params.get("input", "")
    if not input_path:
        raise ValueError("'input' parameter (quest JSON path) is required")
    if not Path(input_path).exists():
        raise ValueError(f"Input file not found: {input_path}")

    progress_cb(0.0, "Loading quest JSON")
    try:
        data = json.loads(Path(input_path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc

    errors: list[str] = []
    warnings: list[str] = []

    nodes_raw = data.get("nodes")
    if not nodes_raw or not isinstance(nodes_raw, list):
        errors.append("Top-level key 'nodes' is missing or empty")
        return _result(errors, warnings, 0, output_dir)

    start_id: str = data.get("start", "")
    graph: dict[str, list[str]] = {}
    defined_ids: set[str] = set()

    for idx, node in enumerate(nodes_raw):
        if not isinstance(node, dict):
            errors.append(f"Node #{idx} is not an object")
            continue
        node_id = node.get("id")
        if not node_id:
            errors.append(f"Node #{idx} missing required key 'id'")
            node_id = f"<unnamed_{idx}>"
        if "title" not in node and "description" not in node:
            errors.append(f"Node '{node_id}' missing 'title' or 'description'")
        defined_ids.add(node_id)
        nexts = node.get("next", [])
        if isinstance(nexts, str):
            nexts = [nexts]
        graph[node_id] = list(nexts)

    if start_id and start_id not in defined_ids:
        errors.append(f"Start node '{start_id}' not found in nodes list")
        start_id = ""
    if not start_id and defined_ids:
        start_id = next(iter(defined_ids))
        warnings.append(f"No 'start' key — assuming first node '{start_id}' as start")

    # Check for missing next references
    for nid, nexts in graph.items():
        for nxt in nexts:
            if nxt not in defined_ids:
                errors.append(f"Node '{nid}' references undefined next node '{nxt}'")

    progress_cb(0.4, "Checking reachability and cycles")

    try:
        import networkx as nx  # type: ignore
        G = nx.DiGraph()
        for nid, nexts in graph.items():
            for nxt in nexts:
                G.add_edge(nid, nxt)
        for nid in defined_ids:
            G.add_node(nid)

        reachable = nx.descendants(G, start_id) | {start_id} if start_id else set()
        unreachable = defined_ids - reachable
        for uid in sorted(unreachable):
            warnings.append(f"Node '{uid}' is unreachable from start")

        try:
            cycle = nx.find_cycle(G)
            cycle_nodes = " → ".join(f"{u}→{v}" for u, v in cycle)
            errors.append(f"Cycle detected: {cycle_nodes}")
        except nx.NetworkXNoCycle:
            pass

    except ImportError:
        # Pure-Python DFS
        visited: set[str] = set()
        rec_stack: set[str] = set()
        has_cycle = [False]
        cycle_info: list[str] = []

        def dfs(node: str) -> None:
            visited.add(node)
            rec_stack.add(node)
            for nxt in graph.get(node, []):
                if nxt in rec_stack:
                    has_cycle[0] = True
                    cycle_info.append(f"{node}→{nxt}")
                elif nxt not in visited:
                    dfs(nxt)
            rec_stack.discard(node)

        if start_id:
            dfs(start_id)

        unreachable = defined_ids - visited
        for uid in sorted(unreachable):
            warnings.append(f"Node '{uid}' is unreachable from start")
        if has_cycle[0]:
            errors.append(f"Cycle detected: {', '.join(cycle_info)}")

    return _result(errors, warnings, len(nodes_raw), output_dir)


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
