"""Auto-generate per-domain command reference pages at mkdocs build time.

This script is executed by the ``gen-files`` mkdocs plugin.  It walks every
``assgen gen <domain> ...`` leaf command, extracts help text / params / examples,
looks up the catalog model assignment, and writes one Markdown page per domain
under ``docs/commands/``.

Adding documentation for a command is as simple as adding an ``Examples:``
section to its Typer command function docstring::

    @app.command("generate")
    def my_cmd(prompt: str = typer.Argument(...)):
        \"\"\"Generate something from a prompt.

        Examples:
            assgen gen domain sub generate "my prompt"
            assgen gen domain sub generate "my prompt" --wait
        \"\"\"
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterator

# Make the assgen package importable when running via mkdocs-gen-files
_src = Path(__file__).parent.parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

import click
import mkdocs_gen_files
import typer
import yaml

# ---------------------------------------------------------------------------
# Catalog helpers
# ---------------------------------------------------------------------------

def _load_catalog() -> dict:
    catalog_path = Path(__file__).parent.parent / "src" / "assgen" / "catalog.yaml"
    try:
        with open(catalog_path) as f:
            data = yaml.safe_load(f)
        return data.get("catalog", {})
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# CLI introspection helpers
# ---------------------------------------------------------------------------

def _extract_examples(callback) -> list[str]:
    """Return lines from the ``Examples:`` section of *callback*'s docstring."""
    if not callback or not callback.__doc__:
        return []
    lines = callback.__doc__.splitlines()
    examples: list[str] = []
    in_section = False
    for line in lines:
        stripped = line.strip()
        if re.match(r"[Ee]xamples?:\s*$", stripped):
            in_section = True
            continue
        if in_section:
            # un-indented non-empty line → new docstring section, stop
            if stripped and not line[:1] in (" ", "\t"):
                break
            if stripped:
                examples.append(stripped)
    return examples


def _type_name(param: click.Parameter) -> str:
    t = param.type
    if hasattr(t, "name"):
        return t.name.upper()
    return type(t).__name__


def _param_info(param: click.Parameter) -> dict:
    return {
        "name": param.name or "",
        "is_option": isinstance(param, click.Option),
        "type_name": _type_name(param),
        "default": param.default,
        "required": param.required,
        "help": getattr(param, "help", "") or "",
    }


def _iter_leaf_commands(
    group: click.Group,
    prefix: list[str],
    max_depth: int = 6,
) -> Iterator[tuple[list[str], click.Command]]:
    try:
        ctx = click.Context(group)
        names = group.list_commands(ctx)
    except Exception:
        return
    for name in names:
        try:
            cmd = group.get_command(ctx, name)
        except Exception:
            continue
        if cmd is None:
            continue
        path = prefix + [name]
        if isinstance(cmd, click.Group) and max_depth > 0:
            yield from _iter_leaf_commands(cmd, path, max_depth - 1)
        else:
            yield path, cmd


# ---------------------------------------------------------------------------
# Markdown page builders
# ---------------------------------------------------------------------------

_DOMAIN_TITLES = {
    "visual":      "🎨 Visual Assets",
    "audio":       "🔊 Audio",
    "scene":       "🌍 Scene",
    "pipeline":    "⚙️ Pipeline",
    "support":     "📖 Support & Narrative",
    "qa":          "🔬 QA & Validation",
    "procedural":  "🎲 Procedural Generation",
}

_DOMAIN_DESCRIPTIONS = {
    "visual": (
        "Concept art, 3D models, UV unwrapping, textures, rigging, animation, "
        "VFX sprites, LOD generation, and UI icons — all driven by open AI models."
    ),
    "audio": (
        "Sound effects (AudioGen), background music & loops (MusicGen), "
        "and expressive NPC voice synthesis (Bark)."
    ),
    "scene": (
        "Physics collision shape generation, panoramic HDRI sky creation, "
        "and monocular depth estimation from images."
    ),
    "pipeline": (
        "Batch job management, format conversion and engine export, "
        "prefab integration helpers, and workflow chaining."
    ),
    "support": (
        "NPC dialogue trees, lore codex entries, quest outlines — all powered "
        "by Phi-3.5 Mini Instruct for fast, private, offline narrative generation."
    ),
    "qa": (
        "Asset integrity validation, polygon-budget performance checks, "
        "style guide enforcement, and consolidated QA reports."
    ),
    "procedural": (
        "Algorithmic terrain heightmaps, BSP dungeon layouts, foliage placement, "
        "weather systems, noise fields, UV packing, and name generation — "
        "no AI model required for any of these."
    ),
}


def _model_cell(cat: dict) -> str:
    model_id = cat.get("model_id")
    if model_id:
        return f"[{model_id.split('/')[-1]}](https://huggingface.co/{model_id})"
    if cat:
        return "*(algorithmic)*"
    return "—"


def _build_domain_page(domain: str, commands: list[dict], catalog: dict) -> str:
    title = _DOMAIN_TITLES.get(domain, domain.title())
    desc = _DOMAIN_DESCRIPTIONS.get(domain, "")

    lines: list[str] = [f"# {title}", ""]
    if desc:
        lines += [desc, ""]

    # Quick-reference table
    lines += ["## Quick Reference", ""]
    lines += ["| Command | Description | Model |", "|---------|-------------|-------|"]
    for c in commands:
        cmd_str = c["cmd_str"]
        short = (c.get("help") or "").split("\n")[0][:80].rstrip(".")
        cat = catalog.get(c.get("job_type"), {})
        anchor = cmd_str.replace(" ", "-").lower()
        lines.append(f"| [`{cmd_str}`](#{anchor}) | {short} | {_model_cell(cat)} |")
    lines += ["", "---", ""]

    # Per-command sections
    for c in commands:
        cmd_str = c["cmd_str"]
        anchor = cmd_str.replace(" ", "-").lower()
        lines.append(f'## `{cmd_str}` {{#{anchor}}}')
        lines.append("")

        if c.get("help"):
            lines.append(c["help"].strip())
            lines.append("")

        cat = catalog.get(c.get("job_type"), {})
        if cat:
            model_id = cat.get("model_id")
            name = cat.get("name", c.get("job_type") or "")
            if model_id:
                lines.append('!!! info "AI Model"')
                lines.append(f"    **[{name}](https://huggingface.co/{model_id})**")
                lines.append(f"    `{model_id}`")
                if cat.get("notes"):
                    lines.append("")
                    lines.append(f"    {cat['notes']}")
            else:
                lines.append('!!! note "Algorithmic — no AI model required"')
                lines.append(
                    "    This command uses CPU-based algorithms. "
                    "No model download or GPU required."
                )
            lines.append("")

        params = [p for p in c.get("params", []) if p["name"] != "help"]
        if params:
            lines += ["**Parameters**", ""]
            lines += [
                "| Parameter | Type | Default | Description |",
                "|-----------|------|---------|-------------|",
            ]
            for p in params:
                pname = (
                    f'`--{p["name"].replace("_", "-")}`'
                    if p["is_option"]
                    else f'`{p["name"].upper()}`'
                )
                req = " *(required)*" if p["required"] and not p["is_option"] else ""
                default = str(p["default"]) if p["default"] is not None else "—"
                help_text = (p["help"] or "").replace("|", "\\|").replace("\n", " ")
                lines.append(
                    f"| {pname}{req} | `{p['type_name']}` | `{default}` | {help_text} |"
                )
            lines.append("")

        examples = c.get("examples", [])
        if examples:
            lines += ["**Examples**", "", "```bash"] + examples + ["```", ""]
        else:
            lines.append(
                "<!-- TODO: add `Examples:` section to this command's docstring -->"
            )
            lines.append("")

        lines += ["---", ""]

    return "\n".join(lines)


def _build_index_page(domain_summaries: dict[str, list[dict]], catalog: dict) -> str:
    lines = [
        "# Command Reference",
        "",
        "All `assgen gen` commands — auto-generated from source code annotations.",
        "Parameters, model assignments, and examples are pulled directly from the CLI.",
        "",
        "---",
        "",
    ]
    for domain, cmds in domain_summaries.items():
        title = _DOMAIN_TITLES.get(domain, domain.title())
        desc = _DOMAIN_DESCRIPTIONS.get(domain, "")
        lines += [f"## {title}", ""]
        if desc:
            lines += [desc, ""]
        lines += [
            "| Command | Description | Model |",
            "|---------|-------------|-------|",
        ]
        for c in cmds:
            cmd_str = c["cmd_str"]
            short = (c.get("help") or "").split("\n")[0][:60].rstrip(".")
            cat = catalog.get(c.get("job_type"), {})
            anchor = cmd_str.replace(" ", "-").lower()
            lines.append(
                f"| [`{cmd_str}`]({domain}.md#{anchor}) | {short} | {_model_cell(cat)} |"
            )
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    from assgen.client.cli import app as root_typer_app  # noqa: PLC0415

    catalog = _load_catalog()
    root_click = typer.main.get_command(root_typer_app)

    gen_ctx = click.Context(root_click)  # type: ignore[arg-type]
    gen_group = root_click.get_command(gen_ctx, "gen")  # type: ignore[arg-type]
    if gen_group is None or not isinstance(gen_group, click.Group):
        return

    domain_commands: dict[str, list[dict]] = {}
    gen_inner_ctx = click.Context(gen_group)

    for domain_name in gen_group.list_commands(gen_inner_ctx):
        domain_cmd = gen_group.get_command(gen_inner_ctx, domain_name)
        if domain_cmd is None or not isinstance(domain_cmd, click.Group):
            continue

        cmds_for_domain: list[dict] = []
        for path, leaf in _iter_leaf_commands(
            domain_cmd, ["assgen", "gen", domain_name]
        ):
            # path = ["assgen", "gen", "visual", "concept", "generate"]
            # job_type = "visual.concept.generate"
            sub_parts = path[3:]
            job_type = f"{domain_name}.{'.'.join(sub_parts)}"
            cmds_for_domain.append(
                {
                    "cmd_str": " ".join(path),
                    "help": leaf.help or "",
                    "params": [_param_info(p) for p in leaf.params],
                    "examples": _extract_examples(leaf.callback),
                    "job_type": job_type,
                }
            )

        if cmds_for_domain:
            domain_commands[domain_name] = cmds_for_domain

    # Write per-domain pages
    for domain, cmds in domain_commands.items():
        content = _build_domain_page(domain, cmds, catalog)
        with mkdocs_gen_files.open(f"commands/{domain}.md", "w") as f:
            f.write(content)

    # Write overview index
    index_content = _build_index_page(domain_commands, catalog)
    with mkdocs_gen_files.open("commands/index.md", "w") as f:
        f.write(index_content)


main()
