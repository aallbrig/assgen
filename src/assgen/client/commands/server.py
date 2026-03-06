"""assgen server — manage the local assgen-server process from the client CLI.

  assgen server start               [--daemon]
  assgen server stop
  assgen server status
  assgen server config show         server runtime settings (host, port, device…)
  assgen server config set          update a runtime setting key/value
  assgen server config models       task → model catalog (same as assgen config)
"""
from __future__ import annotations

from typing import Optional

import typer

from assgen.client.output import console
from assgen.config import (
    get_config_dir,
    load_server_config,
    read_pid_file,
    save_client_config,
)

app = typer.Typer(help="Manage the local assgen-server process.", no_args_is_help=True)

# ── server config sub-group ───────────────────────────────────────────────────
_config_app = typer.Typer(
    help="View and update assgen-server runtime configuration.",
    no_args_is_help=True,
)
app.add_typer(_config_app, name="config")


@app.command("start")
def server_start(
    daemon: bool = typer.Option(True, "--daemon/--foreground", help="Run as background daemon"),
    host: Optional[str] = typer.Option(None, help="Override server host"),
    port: Optional[int] = typer.Option(None, help="Override server port"),
) -> None:
    """Start a local assgen-server."""
    import subprocess
    import sys
    import os
    import shutil

    srv_cfg = load_server_config()
    _host = host or srv_cfg.get("host", "127.0.0.1")
    _port = port or srv_cfg.get("port", 8432)

    exe = shutil.which("assgen-server") or shutil.which("assgen_server")
    if not exe:
        bin_dir = os.path.dirname(sys.executable)
        candidate = os.path.join(bin_dir, "assgen-server")
        exe = candidate if os.path.isfile(candidate) else None
    if not exe:
        console.print("[red]Error:[/red] Could not find assgen-server executable.")
        raise typer.Exit(1)
    cmd = [exe, "start", "--host", _host, "--port", str(_port)]
    if daemon:
        cmd.append("--daemon")

    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise typer.Exit(result.returncode)


@app.command("stop")
def server_stop() -> None:
    """Stop the local assgen-server."""
    import subprocess
    from assgen.client.auto_server import find_server_executable
    try:
        exe = find_server_executable()
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    result = subprocess.run([exe, "stop"])
    raise typer.Exit(result.returncode)


@app.command("status")
def server_status() -> None:
    """Show whether a local assgen-server is running."""
    import os

    info = read_pid_file()
    if not info:
        console.print("[dim]No local server running.[/dim]")
        return

    pid, url = info
    try:
        os.kill(pid, 0)
        alive = True
    except ProcessLookupError:
        alive = False

    if alive:
        # Also try a health check
        try:
            import httpx
            r = httpx.get(f"{url}/health", timeout=2.0)
            healthy = r.status_code == 200
            version = r.json().get("version", "?") if healthy else "?"
        except Exception:
            healthy = False
            version = "?"
        status_str = "[green]Running[/green]" if healthy else "[yellow]Running (unreachable)[/yellow]"
        console.print(f"Status:  {status_str}")
        console.print(f"PID:     {pid}")
        console.print(f"URL:     {url}")
        if healthy:
            console.print(f"Version: {version}")
    else:
        console.print(f"[yellow]Stale PID file (process {pid} not running)[/yellow]")


@_config_app.command("show")
def server_config_show() -> None:
    """Show the resolved assgen-server runtime configuration."""
    srv = load_server_config()
    cfg_dir = get_config_dir()

    console.print(f"\n[bold]Config directory:[/bold] {cfg_dir}")
    console.print("\n[bold]Server runtime settings:[/bold]")
    _DESCRIPTIONS = {
        "host":                  "Bind address",
        "port":                  "Listen port",
        "workers":               "Concurrent worker threads",
        "device":                "Inference device (auto / cuda / cpu)",
        "log_level":             "Logging verbosity",
        "model_load_timeout":    "Max seconds to wait for a model download",
        "job_retention_days":    "Days to keep completed jobs in DB",
        "allow_list":            "Allowed model IDs ([] = all allowed)",
        "skip_model_validation": "Bypass HF pipeline_tag compatibility checks",
    }
    for k, v in srv.items():
        desc = _DESCRIPTIONS.get(k, "")
        desc_str = f"  [dim]{desc}[/dim]" if desc else ""
        console.print(f"  [cyan]{k}[/cyan] = {v}{desc_str}")

    console.print()
    console.print(
        "[dim]Override any setting via environment variable: "
        "ASSGEN_SERVER_HOST, ASSGEN_SERVER_PORT, ASSGEN_SERVER_DEVICE, …[/dim]"
    )
    console.print("[dim]Update a setting: assgen server config set <key> <value>[/dim]")
    console.print("[dim]Task → model map: assgen server config models[/dim]")


@_config_app.command("set")
def server_config_set(
    key: str = typer.Argument(..., help="Config key, e.g. device or port"),
    value: str = typer.Argument(..., help="New value"),
) -> None:
    """Persist a server configuration setting to ~/.config/assgen/server.yaml.

    Changes take effect on next server start.

    Examples:
      assgen server config set device cuda
      assgen server config set port 9000
      assgen server config set log_level debug
    """
    from assgen.config import get_config_dir
    import yaml

    cfg_dir = get_config_dir()
    server_yaml = cfg_dir / "server.yaml"

    # Load existing file (if any) or start fresh
    existing: dict = {}
    if server_yaml.exists():
        with open(server_yaml) as f:
            existing = yaml.safe_load(f) or {}

    # Type-coerce common keys
    _INT_KEYS = {"port", "workers", "job_retention_days", "model_load_timeout"}
    _BOOL_KEYS = {"skip_model_validation"}
    _LIST_KEYS = {"allow_list"}
    coerced: object = value
    if key in _INT_KEYS:
        try:
            coerced = int(value)
        except ValueError:
            console.print(f"[red]Error:[/red] '{key}' must be an integer, got {value!r}")
            raise typer.Exit(1)
    elif key in _BOOL_KEYS:
        coerced = value.lower() in {"true", "1", "yes"}
    elif key in _LIST_KEYS:
        import json
        try:
            parsed = json.loads(value)
            if not isinstance(parsed, list):
                raise ValueError("must be a JSON array")
            coerced = parsed
        except (ValueError, json.JSONDecodeError):
            # Treat comma-separated string as list
            coerced = [v.strip() for v in value.split(",") if v.strip()]

    old = existing.get(key, "[not set]")
    existing[key] = coerced

    server_yaml.parent.mkdir(parents=True, exist_ok=True)
    with open(server_yaml, "w") as f:
        yaml.safe_dump(existing, f)

    console.print(
        f"[green]✓[/green]  [cyan]{key}[/cyan]: {old!r} → {coerced!r}\n"
        f"[dim]Saved to {server_yaml}\n"
        f"Restart the server for changes to take effect.[/dim]"
    )


@_config_app.command("models")
def server_config_models(
    domain: Optional[str] = typer.Option(
        None, "--domain", "-d", help="Filter by domain (visual, audio, scene…)"
    ),
) -> None:
    """Show and manage the task → model catalog used by the server.

    This is the same as running `assgen config list` but surfaced here
    so it's discoverable under server configuration.

    To add / change a model:
      assgen server config models --domain visual
      assgen config set <job-type> [--model-id <id>]
    """
    from assgen.client.commands.config import config_list
    # Delegate to the top-level config list command
    config_list(domain=domain, installed=False)


@app.command("use")
def server_use(
    url: str = typer.Argument(..., help="Server URL, e.g. http://192.168.1.100:8432"),
) -> None:
    """Point the client at a specific server URL. (Alias for: assgen client config set-server)"""
    save_client_config({"server_url": url})
    console.print(f"[green]Client will now use server:[/green] {url}")
    console.print("[dim]Full client config: assgen client config show[/dim]")


@app.command("unset")
def server_unset() -> None:
    """Remove the configured server URL — revert to auto-start mode. (Alias for: assgen client config unset-server)"""
    save_client_config({"server_url": None})
    console.print("[green]Cleared server_url — will auto-start local server.[/green]")
