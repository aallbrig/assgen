"""Tests for assgen.client.commands.tasks — task tree completeness."""
from __future__ import annotations



def test_build_tree_returns_tree() -> None:
    from assgen.client.commands.tasks import _build_tree
    from rich.tree import Tree

    tree = _build_tree()
    assert isinstance(tree, Tree)


def test_build_tree_domain_filter() -> None:
    from assgen.client.commands.tasks import _build_tree
    from rich.tree import Tree

    for domain in ("visual", "audio", "scene", "pipeline", "support", "qa"):
        tree = _build_tree(domain)
        assert isinstance(tree, Tree)


def test_build_tree_unknown_domain_does_not_raise() -> None:
    from assgen.client.commands.tasks import _build_tree

    # Should print an error but not raise
    _build_tree("nonexistent_domain")


def test_all_catalog_job_types_have_descriptions() -> None:
    """Every job type in the default catalog should have a description entry."""
    from assgen.catalog import load_catalog
    from assgen.client.commands.tasks import _TASK_DESC

    catalog = load_catalog()
    missing = [jt for jt in catalog if jt not in _TASK_DESC]
    assert missing == [], f"Catalog job types missing task descriptions: {missing}"


def test_all_tree_job_types_covered() -> None:
    """Every leaf in _DOMAIN_TREE should have a description in _TASK_DESC."""
    from assgen.client.commands.tasks import _DOMAIN_TREE, _TASK_DESC

    missing = []
    for domain, dspec in _DOMAIN_TREE.items():
        for key, val in dspec.items():
            if key.startswith("_"):
                continue
            if key == "_tasks":
                break
            if isinstance(val, dict):
                for action in val.get("_tasks", []):
                    jt = f"{domain}.{key}.{action}"
                    if jt not in _TASK_DESC:
                        missing.append(jt)
        if "_tasks" in dspec:
            for action in dspec["_tasks"]:
                jt = f"{domain}.{action}"
                if jt not in _TASK_DESC:
                    missing.append(jt)

    assert missing == [], f"Task tree items missing descriptions: {missing}"


def test_domain_tree_has_icons_and_descs() -> None:
    from assgen.client.commands.tasks import _DOMAIN_TREE

    for domain, dspec in _DOMAIN_TREE.items():
        assert "_icon" in dspec, f"{domain}: missing _icon"
        assert "_desc" in dspec, f"{domain}: missing _desc"


def test_json_output_is_valid_list() -> None:
    """_build_tree doesn't test JSON — verify via the raw data structures."""
    from assgen.client.commands.tasks import _DOMAIN_TREE, _TASK_DESC
    from assgen.catalog import load_catalog

    catalog = load_catalog()
    out = []
    for domain_name, dspec in _DOMAIN_TREE.items():
        for key, val in dspec.items():
            if key.startswith("_"):
                continue
            if key == "_tasks":
                break
            for action in val.get("_tasks", []):
                jt = f"{domain_name}.{key}.{action}"
                entry = catalog.get(jt, {})
                out.append({
                    "job_type": jt,
                    "model_id": entry.get("model_id"),
                    "description": _TASK_DESC.get(jt, ""),
                })
        if "_tasks" in dspec:
            for action in dspec["_tasks"]:
                jt = f"{domain_name}.{action}"
                entry = catalog.get(jt, {})
                out.append({
                    "job_type": jt,
                    "model_id": entry.get("model_id"),
                    "description": _TASK_DESC.get(jt, ""),
                })

    assert len(out) > 40  # we have 50+ job types
    assert all("job_type" in item for item in out)
