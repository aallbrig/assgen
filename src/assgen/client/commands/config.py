"""assgen config — view and manage the model catalog.

Maps job types (e.g. visual.model.create) to HuggingFace models.

  assgen config list    [--domain DOMAIN]     show all job-type → model mappings
  assgen config show    <job-type>            detail view + HF link
  assgen config set     [job-type]            add / update a mapping (interactive)
  assgen config remove  <job-type>            remove a user override
  assgen config search  [query]              search HuggingFace for models

When required arguments are omitted, each command prompts interactively.
`config set` opens a HuggingFace model search when no --model-id is given.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table

from assgen.catalog import all_job_types, load_catalog
from assgen.config import get_config_dir

app = typer.Typer(
    help="View and manage job-type → model mappings.",
    no_args_is_help=True,
)

console = Console()
err = Console(stderr=True)

# ---------------------------------------------------------------------------
# HuggingFace task tags associated with each job-type domain.
# Used to pre-filter HF search results for relevant models.
# ---------------------------------------------------------------------------
_JOB_TYPE_TO_HF_TASK: dict[str, str | None] = {
    "visual.concept.generate":    "text-to-image",
    "visual.concept.ref":         "text-to-image",
    "visual.concept.style":       "text-to-image",
    "visual.blockout.create":     "text-to-image",
    "visual.model.create":        "image-to-3d",
    "visual.model.highpoly":      "image-to-3d",
    "visual.model.retopo":        "image-to-3d",
    "visual.model.splat":         "image-to-3d",
    "visual.model.edit":          "image-to-3d",
    "visual.model.optimize":      "image-to-3d",
    "visual.uv.auto":             "image-to-3d",
    "visual.texture.generate":    "text-to-image",
    "visual.texture.apply":       "image-to-image",
    "visual.texture.bake":        "image-to-3d",
    "visual.texture.pbr":         "text-to-image",
    "visual.rig.auto":            "image-to-3d",
    "visual.rig.skin":            "image-to-3d",
    "visual.rig.retarget":        "image-to-3d",
    "visual.animate.keyframe":    "text-to-video",
    "visual.animate.mocap":       "video-classification",
    "visual.animate.blend":       "text-to-video",
    "visual.animate.retarget":    "text-to-video",
    "visual.vfx.particle":        "text-to-image",
    "visual.vfx.decal":           "text-to-image",
    "visual.vfx.sim":             "text-to-video",
    "visual.ui.icon":             "text-to-image",
    "visual.ui.hud":              "text-to-image",
    "visual.ui.overlay":          "text-to-image",
    "audio.sfx.generate":         "text-to-audio",
    "audio.sfx.edit":             "audio-to-audio",
    "audio.music.compose":        "text-to-audio",
    "audio.music.loop":           "text-to-audio",
    "audio.music.adaptive":       "text-to-audio",
    "audio.voice.tts":            "text-to-speech",
    "audio.voice.clone":          "text-to-speech",
    "audio.voice.dialog":         "text-to-speech",
    "scene.physics.collider":     "image-to-3d",
    "scene.physics.rigid":        "image-to-3d",
    "scene.physics.cloth":        "image-to-3d",
    "scene.physics.export":       None,
    "scene.lighting.hdri":        "text-to-image",
    "scene.lighting.probes":      "image-to-3d",
    "scene.lighting.volumetrics": "text-to-image",
    "scene.lighting.bake":        "image-to-3d",
    "pipeline.integrate.export":  None,
    "pipeline.integrate.prefab":  None,
    "pipeline.integrate.script":  None,
    "support.narrative.dialog":   "text-generation",
    "support.narrative.lore":     "text-generation",
    "support.data.lightmap":      "image-to-3d",
    "support.data.proc":          "text-generation",
}

# Human-readable label for each HF pipeline_tag shown in tables
_HF_TASK_LABEL: dict[str, str] = {
    "text-to-image":     "text→image",
    "image-to-3d":       "image→3D",
    "text-to-video":     "text→video",
    "text-to-audio":     "text→audio",
    "text-to-speech":    "text→speech",
    "audio-to-audio":    "audio→audio",
    "image-to-image":    "image→image",
    "video-classification": "video class.",
    "text-generation":   "text gen",
}


# ---------------------------------------------------------------------------
# User catalog helpers
# ---------------------------------------------------------------------------

def _user_catalog_path() -> Path:
    return get_config_dir() / "models.yaml"


def _load_user_catalog() -> dict[str, Any]:
    p = _user_catalog_path()
    if p.exists():
        with p.open() as f:
            return (yaml.safe_load(f) or {}).get("catalog", {})
    return {}


def _save_user_catalog(catalog: dict[str, Any]) -> None:
    p = _user_catalog_path()
    existing: dict[str, Any] = {}
    if p.exists():
        with p.open() as f:
            existing = yaml.safe_load(f) or {}
    existing["catalog"] = catalog
    with p.open("w") as f:
        yaml.safe_dump(existing, f, default_flow_style=False, sort_keys=True)


def _builtin_catalog() -> dict[str, Any]:
    """Return only the shipped catalog without user overrides."""
    from assgen.catalog import _BUILTIN_CATALOG
    with _BUILTIN_CATALOG.open() as f:
        return (yaml.safe_load(f) or {}).get("catalog", {})


def _source(job_type: str, user_catalog: dict[str, Any]) -> str:
    return "[cyan]user[/cyan]" if job_type in user_catalog else "[dim]built-in[/dim]"


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@app.command("list")
def config_list(
    domain: Optional[str] = typer.Option(
        None, "--domain", "-d",
        help="Filter by domain prefix, e.g. visual, audio, scene, pipeline",
    ),
    installed: bool = typer.Option(False, "--installed", help="Only show installed models"),
) -> None:
    """List all job-type → model mappings with source and HF task info."""
    catalog = load_catalog()
    user_cat = _load_user_catalog()

    # Optionally filter installed models from DB
    installed_ids: set[str] = set()
    if installed:
        try:
            from assgen.db import init_db
            conn = init_db()
            rows = conn.execute(
                "SELECT model_id FROM models WHERE local_path IS NOT NULL"
            ).fetchall()
            installed_ids = {r["model_id"] for r in rows}
        except Exception:
            pass

    table = Table(
        title="Model Catalog",
        show_lines=True,
        header_style="bold cyan",
        expand=True,
    )
    table.add_column("Job Type",   min_width=28)
    table.add_column("HF Task",    width=12)
    table.add_column("Model ID",   min_width=32)
    table.add_column("Name",       min_width=18)
    table.add_column("Source",     width=10)
    table.add_column("Inst.",      width=5)

    prev_domain = None
    for jt in sorted(catalog.keys()):
        if domain and not jt.startswith(domain):
            continue
        entry = catalog[jt]
        mid = entry.get("model_id") or "–"
        if installed and mid not in installed_ids:
            continue

        # Section separator when domain changes
        current_domain = jt.split(".")[0]
        if current_domain != prev_domain:
            prev_domain = current_domain

        hf_task  = _JOB_TYPE_TO_HF_TASK.get(jt)
        task_lbl = _HF_TASK_LABEL.get(hf_task or "", hf_task or "–")
        inst_str = "[green]✓[/green]" if mid in installed_ids else "–"

        table.add_row(
            jt,
            task_lbl,
            mid,
            entry.get("name") or "–",
            _source(jt, user_cat),
            inst_str,
        )

    console.print(table)
    console.print(
        f"\n[dim]User overrides: {_user_catalog_path()}[/dim]\n"
        "[dim]Edit with: assgen config set <job-type>[/dim]"
    )


@app.command("show")
def config_show(
    job_type: Optional[str] = typer.Argument(None, help="Job type to inspect"),
) -> None:
    """Show the full configuration for a single job type."""
    if not job_type:
        job_type = _prompt_job_type("Job type to inspect")

    catalog = load_catalog()
    if job_type not in catalog:
        err.print(f"[red]Unknown job type:[/red] {job_type!r}")
        err.print("[dim]Run: assgen config list[/dim]")
        raise typer.Exit(1)

    entry = catalog[job_type]
    user_cat = _load_user_catalog()
    hf_task  = _JOB_TYPE_TO_HF_TASK.get(job_type)
    mid      = entry.get("model_id")

    lines = [
        f"[bold]Job type:[/bold]  {job_type}",
        f"[bold]HF task:[/bold]   {_HF_TASK_LABEL.get(hf_task or '', hf_task or '(none)')}  [dim]({hf_task or 'n/a'})[/dim]",
        f"[bold]Model ID:[/bold]  {mid or '(none)'}",
        f"[bold]Name:[/bold]      {entry.get('name') or '–'}",
        f"[bold]Source:[/bold]    {_source(job_type, user_cat)}",
    ]
    if entry.get("notes"):
        lines.append(f"[bold]Notes:[/bold]     {entry['notes']}")
    if mid:
        lines.append(f"\n[bold]HuggingFace:[/bold] https://huggingface.co/{mid}")
        lines.append("[bold]Search more:[/bold] assgen config search "
                     f"--job-type {job_type}")

    # Check install status
    try:
        from assgen.db import init_db
        conn = init_db()
        row = conn.execute(
            "SELECT local_path, installed_at, last_used_at, size_bytes FROM models WHERE model_id = ?",
            (mid,),
        ).fetchone()
        if row and row["local_path"]:
            lines.append(f"\n[green]Installed[/green]  {row['local_path']}")
            lines.append(f"[dim]Installed at: {(row['installed_at'] or '')[:19]}[/dim]")
        else:
            lines.append("\n[yellow]Not installed[/yellow]  (run: assgen models install)")
    except Exception:
        pass

    console.print(Panel("\n".join(lines), title=f"[bold cyan]{job_type}[/bold cyan]", expand=False))


@app.command("set")
def config_set(
    job_type: Optional[str] = typer.Argument(None, help="Job type to configure"),
    model_id: Optional[str] = typer.Option(None, "--model-id", "-m",
                                           help="HuggingFace model ID (org/repo)"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Display name"),
    notes: Optional[str] = typer.Option(None, "--notes", help="Optional notes"),
    task: Optional[str] = typer.Option(None, "--task", "-t",
                                       help="Override HF pipeline_tag for search"),
) -> None:
    """Add or update the model mapping for a job type.

    If arguments are omitted, each field is prompted interactively.
    When no --model-id is given, an interactive HuggingFace search is offered.
    """
    # ── 1. Job type ──────────────────────────────────────────────────────────
    if not job_type:
        job_type = _prompt_job_type("Job type to configure")

    catalog    = load_catalog()
    user_cat   = _load_user_catalog()
    existing   = catalog.get(job_type, {})
    hf_task    = task or _JOB_TYPE_TO_HF_TASK.get(job_type)

    console.print(f"\nConfiguring [bold cyan]{job_type}[/bold cyan]")
    if existing:
        console.print(f"  Current model: [dim]{existing.get('model_id', '(none)')}[/dim]")
    if hf_task:
        console.print(f"  HuggingFace task: [dim]{hf_task}[/dim]")
    console.print()

    # ── 2. Model ID ──────────────────────────────────────────────────────────
    if not model_id:
        choice = Prompt.ask(
            "[bold]Model ID[/bold]  (HuggingFace org/repo, or press [cyan]Enter[/cyan] to search)",
            default="",
        ).strip()

        if choice:
            model_id = choice
        else:
            # Interactive HF search
            model_id = _interactive_hf_search(job_type, hf_task)
            if not model_id:
                err.print("[yellow]No model selected — aborted.[/yellow]")
                raise typer.Exit(0)

    # ── 3. Display name ──────────────────────────────────────────────────────
    default_name = name or existing.get("name") or model_id.split("/")[-1]
    if not name:
        name = Prompt.ask("[bold]Display name[/bold]", default=default_name).strip() or default_name

    # ── 4. Notes ─────────────────────────────────────────────────────────────
    if notes is None:
        notes_input = Prompt.ask(
            "[bold]Notes[/bold]  (optional, press Enter to skip)",
            default="",
        ).strip()
        notes = notes_input or existing.get("notes")

    # ── 5. Confirm ───────────────────────────────────────────────────────────
    console.print()
    console.print(Panel(
        f"[bold]Job type:[/bold]  {job_type}\n"
        f"[bold]Model ID:[/bold]  {model_id}\n"
        f"[bold]Name:[/bold]      {name}\n"
        f"[bold]Notes:[/bold]     {notes or '–'}",
        title="[bold]Confirm new mapping[/bold]",
        expand=False,
    ))

    if not Confirm.ask("Save this mapping?", default=True):
        console.print("[dim]Aborted.[/dim]")
        raise typer.Exit(0)

    # ── 6. Save ──────────────────────────────────────────────────────────────
    user_cat[job_type] = {
        "model_id": model_id,
        "name": name,
        "task": hf_task or existing.get("task"),
        **({"notes": notes} if notes else {}),
    }
    _save_user_catalog(user_cat)

    console.print(f"\n[green]✓ Saved[/green] → {_user_catalog_path()}")
    console.print(f"[dim]Install the model with: assgen models install {model_id}[/dim]")


@app.command("remove")
def config_remove(
    job_type: Optional[str] = typer.Argument(None, help="Job type to remove override for"),
) -> None:
    """Remove a user override, reverting to the built-in default."""
    if not job_type:
        user_cat = _load_user_catalog()
        if not user_cat:
            console.print("[dim]No user overrides to remove.[/dim]")
            raise typer.Exit(0)
        job_type = _prompt_choice(
            "Job type to remove override for",
            sorted(user_cat.keys()),
        )

    user_cat = _load_user_catalog()
    if job_type not in user_cat:
        err.print(f"[yellow]{job_type!r} has no user override — nothing to remove.[/yellow]")
        builtin = _builtin_catalog().get(job_type)
        if builtin:
            err.print(f"[dim]Built-in default: {builtin.get('model_id')}[/dim]")
        raise typer.Exit(0)

    entry = user_cat[job_type]
    console.print(
        f"Remove override for [cyan]{job_type}[/cyan]  "
        f"([dim]{entry.get('model_id')}[/dim])?",
    )
    builtin = _builtin_catalog().get(job_type)
    if builtin:
        console.print(f"[dim]Will revert to built-in: {builtin.get('model_id')}[/dim]")

    if not Confirm.ask("Remove?", default=False):
        console.print("[dim]Aborted.[/dim]")
        raise typer.Exit(0)

    del user_cat[job_type]
    _save_user_catalog(user_cat)
    console.print(f"[green]✓ Removed[/green] override for {job_type}")


@app.command("search")
def config_search(
    query: Optional[str] = typer.Argument(None, help="Search term (model name or keyword)"),
    job_type: Optional[str] = typer.Option(
        None, "--job-type", "-j",
        help="Job type to pre-filter by HF task (e.g. visual.model.create)",
    ),
    task: Optional[str] = typer.Option(
        None, "--task", "-t",
        help="HuggingFace pipeline_tag filter (e.g. text-to-image, image-to-3d)",
    ),
    limit: int = typer.Option(10, "--limit", "-n", help="Max results to show"),
    apply: bool = typer.Option(
        False, "--apply", "-a",
        help="Interactively pick a result and apply it to the job type",
    ),
) -> None:
    """Search HuggingFace Hub for models relevant to a game-dev task.

    Examples:
      assgen config search triposr --job-type visual.model.create
      assgen config search musicgen --task text-to-audio
      assgen config search sdxl --apply --job-type visual.texture.generate
    """
    # Resolve task filter
    hf_task = task
    if not hf_task and job_type:
        hf_task = _JOB_TYPE_TO_HF_TASK.get(job_type)

    if not query:
        query = Prompt.ask("[bold]Search HuggingFace[/bold]  (keyword or model name)").strip()
        if not query:
            err.print("[yellow]No query provided — aborted.[/yellow]")
            raise typer.Exit(0)

    results = _hf_search(query, hf_task, limit)

    if not results:
        console.print(f"[yellow]No results for {query!r}"
                      + (f" (task: {hf_task})" if hf_task else "") + "[/yellow]")
        raise typer.Exit(0)

    _print_search_results(results, hf_task)

    if apply:
        if not job_type:
            job_type = _prompt_job_type("Apply result to job type")

        idx = IntPrompt.ask(
            f"\nSelect model [bold](1-{len(results)})[/bold]",
            default=1,
        )
        if not 1 <= idx <= len(results):
            err.print("[red]Invalid selection.[/red]")
            raise typer.Exit(1)
        chosen = results[idx - 1]
        mid    = chosen["id"]

        # Delegate to config_set logic
        console.print(f"\n[dim]Selected: {mid}[/dim]")
        config_set(
            job_type=job_type,
            model_id=mid,
            name=None,
            notes=None,
            task=hf_task,
        )


# ---------------------------------------------------------------------------
# Interactive helpers
# ---------------------------------------------------------------------------

def _prompt_job_type(prompt_text: str) -> str:
    """Prompt the user to pick a job type, with autocomplete-style numbered list."""
    known = all_job_types()

    console.print(f"\n[bold]{prompt_text}[/bold]  (type a number or job-type string)\n")

    table = Table(show_header=True, header_style="bold cyan", show_lines=False, box=None)
    table.add_column("#",        width=4,  style="dim")
    table.add_column("Job type", min_width=30)
    table.add_column("HF task",  min_width=14, style="dim")

    for i, jt in enumerate(known, start=1):
        task_label = _HF_TASK_LABEL.get(_JOB_TYPE_TO_HF_TASK.get(jt) or "", "–")
        table.add_row(str(i), jt, task_label)

    console.print(table)
    console.print()

    raw = Prompt.ask("[bold]Job type[/bold]  (number or full name)").strip()

    # Accept number
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(known):
            return known[idx]
        err.print(f"[red]Invalid number: {raw}[/red]")
        raise typer.Exit(1)

    # Accept partial prefix match
    matches = [jt for jt in known if jt.startswith(raw)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        err.print(f"[yellow]Ambiguous: {raw!r} matches {matches}[/yellow]")
        raise typer.Exit(1)

    # Accept exact unknown type (user wants to add a new mapping)
    if "." in raw:
        console.print(f"[dim]Adding new job type: {raw}[/dim]")
        return raw

    err.print(f"[red]Unknown job type: {raw!r}[/red]")
    raise typer.Exit(1)


def _prompt_choice(prompt_text: str, choices: list[str]) -> str:
    """Show a numbered list and return the selected item."""
    for i, c in enumerate(choices, 1):
        console.print(f"  [dim]{i:>3}.[/dim]  {c}")
    raw = Prompt.ask(f"\n[bold]{prompt_text}[/bold]  (number or name)").strip()
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(choices):
            return choices[idx]
    if raw in choices:
        return raw
    err.print(f"[red]Invalid selection: {raw!r}[/red]")
    raise typer.Exit(1)


def _interactive_hf_search(job_type: str, hf_task: str | None) -> str | None:
    """Run an interactive HF model search loop; return chosen model_id or None."""
    console.print(
        "\n[bold]Searching HuggingFace Hub[/bold]"
        + (f"  [dim](task filter: {hf_task})[/dim]" if hf_task else "")
    )

    while True:
        query = Prompt.ask(
            "[bold]Search query[/bold]  (model name or keyword, or [cyan]Enter[/cyan] to skip)",
            default="",
        ).strip()

        if not query:
            return None

        results = _hf_search(query, hf_task, limit=10)

        if not results:
            console.print(
                f"[yellow]No results for {query!r}"
                + (f" with task={hf_task}" if hf_task else "")
                + "[/yellow]"
            )
            if not Confirm.ask("Try another search?", default=True):
                return None
            # On retry without task filter
            if hf_task and Confirm.ask(
                f"Search again without task filter [dim]({hf_task})[/dim]?",
                default=True,
            ):
                hf_task = None
            continue

        _print_search_results(results, hf_task)

        raw = Prompt.ask(
            f"\n[bold]Select model[/bold]  ([cyan]1-{len(results)}[/cyan], "
            "[cyan]s[/cyan]=search again, [cyan]q[/cyan]=quit)",
            default="q",
        ).strip().lower()

        if raw == "q":
            return None
        if raw == "s":
            continue
        if raw.isdigit() and 1 <= int(raw) <= len(results):
            return results[int(raw) - 1]["id"]

        err.print(f"[yellow]Invalid choice: {raw!r}[/yellow]")


def _hf_search(query: str, hf_task: str | None, limit: int) -> list[dict[str, Any]]:
    """Query HuggingFace Hub and return a list of result dicts."""
    try:
        from huggingface_hub import list_models as hf_list_models
    except ImportError:
        err.print("[red]huggingface_hub not installed.[/red]")
        return []

    console.print(f"[dim]Searching '{query}'"
                  + (f" (task: {hf_task})" if hf_task else "") + "…[/dim]")
    try:
        kwargs: dict[str, Any] = {"search": query, "limit": limit, "sort": "downloads"}
        if hf_task:
            kwargs["pipeline_tag"] = hf_task
        models = list(hf_list_models(**kwargs))
    except Exception as exc:
        err.print(f"[red]HuggingFace search error:[/red] {exc}")
        return []

    return [
        {
            "id":          m.id,
            "pipeline_tag": getattr(m, "pipeline_tag", None) or "–",
            "downloads":   getattr(m, "downloads", 0) or 0,
            "likes":       getattr(m, "likes", 0) or 0,
            "private":     getattr(m, "private", False),
            "gated":       getattr(m, "gated", False),
        }
        for m in models
    ]


def _print_search_results(results: list[dict[str, Any]], hf_task: str | None) -> None:
    task_label = _HF_TASK_LABEL.get(hf_task or "", hf_task or "any task")
    table = Table(
        title=f"HuggingFace results  [dim](task: {task_label})[/dim]",
        show_lines=True,
        header_style="bold cyan",
    )
    table.add_column("#",          width=4,  style="dim")
    table.add_column("Model ID",   min_width=35)
    table.add_column("Task",       width=14)
    table.add_column("Downloads",  width=11, justify="right")
    table.add_column("Likes",      width=7,  justify="right")
    table.add_column("Flags",      width=10)

    for i, m in enumerate(results, 1):
        flags = []
        if m["gated"]:
            flags.append("[yellow]gated[/yellow]")
        if m["private"]:
            flags.append("[dim]private[/dim]")
        dl = m["downloads"]
        dl_str = f"{dl:,}" if dl else "–"
        lk_str = str(m["likes"]) if m["likes"] else "–"
        task_str = _HF_TASK_LABEL.get(m["pipeline_tag"], m["pipeline_tag"])

        table.add_row(
            str(i),
            m["id"],
            task_str,
            dl_str,
            lk_str,
            "  ".join(flags) if flags else "[dim]–[/dim]",
        )

    console.print(table)
    console.print(
        "[dim]View a model: https://huggingface.co/<model-id>[/dim]"
    )
