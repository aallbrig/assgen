"""assgen — root CLI entry point.

Command hierarchy (post-restructure)::

    assgen gen visual      → concept, blockout, model, uv, texture, rig, animate, vfx, ui
    assgen gen audio       → sfx, music, voice
    assgen gen scene       → physics, lighting
    assgen gen pipeline    → workflow, batch, integrate
    assgen gen support     → narrative, data
    assgen gen qa          → validate, perf, style, report
    assgen tasks           → full task tree with configured models
    assgen jobs            → list, status, wait, cancel, clean
    assgen models          → list, status, install
    assgen server          → start, stop, status, config
    assgen client          → config (show/set-server/unset-server)
    assgen config          → list, show, set, remove, search
    assgen upgrade         → check for and install latest release
    assgen version         → print version info
"""
from __future__ import annotations

import logging

import typer
from rich.console import Console

from assgen.client import context as _ctx
from assgen.client.commands.client_cmd import app as client_app
from assgen.client.commands.config     import app as config_app
from assgen.client.commands.gen        import app as gen_app
from assgen.client.commands.jobs       import app as jobs_app
from assgen.client.commands.models     import app as models_app
from assgen.client.commands.server     import app as server_app
from assgen.client.commands.tasks      import app as tasks_app
from assgen.client.commands.upgrade    import app as upgrade_app

console = Console(highlight=False)

app = typer.Typer(
    name="assgen",
    help="AI-driven game asset generation pipeline.",
    no_args_is_help=True,
    add_completion=True,
    rich_markup_mode="rich",
)

app.add_typer(gen_app,     name="gen",     help="Generate assets: visual · audio · scene · pipeline · support · qa")
app.add_typer(tasks_app,   name="tasks",   help="Browse all game dev tasks and their configured models")
app.add_typer(jobs_app,    name="jobs",    help="Job queue management")
app.add_typer(models_app,  name="models",  help="Model catalog and installation")
app.add_typer(server_app,  name="server",  help="Local server process management")
app.add_typer(client_app,  name="client",  help="Client configuration: server targeting and connection settings")
app.add_typer(config_app,  name="config",  help="Configure job-type → model mappings")
app.add_typer(upgrade_app, name="upgrade", help="Check for and install the latest assgen release")


def _version_callback(value: bool) -> None:
    if value:
        from assgen.version import format_version_string
        typer.echo(format_version_string("assgen"))
        raise typer.Exit()


@app.callback()
def _root_callback(
    verbose: bool = typer.Option(
        False, "--verbose", "-v",
        help="Enable debug logging (shows server communication, model resolution, etc.)",
        is_eager=True,
    ),
    version: bool = typer.Option(  # noqa: ARG001
        None, "--version", "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
    json_output: bool = typer.Option(
        False, "--json",
        help="Emit machine-readable JSON to stdout.  Disables progress bars. "
             "Ideal for CI pipelines and scripting.",
    ),
    yaml_output: bool = typer.Option(
        False, "--yaml",
        help="Emit machine-readable YAML to stdout.  Disables progress bars. "
             "Human-friendly alternative to --json.",
    ),
    variants: int = typer.Option(
        1, "--variants", "-n",
        min=1,
        help="Submit N identical jobs (batch generation).  "
             "Use with --wait to collect all outputs.",
    ),
    quality: str = typer.Option(
        "standard", "--quality", "-q",
        help="Model quality tier: draft (fastest/smallest), standard, high (best/largest).  "
             "Maps to model size variants where available.",
    ),
    from_job: str | None = typer.Option(
        None, "--from-job",
        help="Chain from a completed job's outputs.  Pass the upstream job ID; "
             "its output files are forwarded as inputs to this job.",
    ),
    context: list[str] = typer.Option(
        [], "--context",
        help="Named context from a prior job: 'key=job_id'.  Repeatable.  "
             "Loads that job's primary text output into params['context_map']['key'] "
             "so handlers can incorporate prior narrative/lore content.",
    ),
) -> None:
    """AI-driven game asset generation pipeline."""
    if json_output:
        _ctx.set_json_mode(True)
    if yaml_output:
        _ctx.set_yaml_mode(True)
    if variants > 1:
        _ctx.set_variants(variants)
    if quality != "standard":
        _ctx.set_quality(quality)
    if from_job:
        _ctx.set_from_job(from_job)
    if context:
        _ctx.set_context_map(context)
    if verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
            datefmt="%H:%M:%S",
        )
        # Quiet down extremely chatty libraries even in verbose mode
        for noisy in ("httpcore", "httpx", "urllib3", "hpack"):
            logging.getLogger(noisy).setLevel(logging.WARNING)
    else:
        logging.disable(logging.CRITICAL)


@app.command("version")
def version_cmd() -> None:
    """Print version information and exit."""
    from assgen.version import format_version_string
    console.print(format_version_string("assgen"))
