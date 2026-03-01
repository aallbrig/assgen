"""assgen server — manage the local assgen-server process from the client CLI.

  assgen server start    [--daemon]
  assgen server stop
  assgen server status
  assgen server config   show active config
"""
from __future__ import annotations

from typing import Optional

import typer

from assgen.client.output import console
from assgen.config import (
    get_config_dir,
    load_client_config,
    load_server_config,
    read_pid_file,
    save_client_config,
)

app = typer.Typer(help="Manage the local assgen-server process.", no_args_is_help=True)


@app.command("start")
def server_start(
    daemon: bool = typer.Option(True, "--daemon/--foreground", help="Run as background daemon"),
    host: Optional[str] = typer.Option(None, help="Override server host"),
    port: Optional[int] = typer.Option(None, help="Override server port"),
) -> None:
    """Start a local assgen-server."""
    import subprocess, sys, os, shutil
    from assgen.config import write_pid_file

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
    import os
    import shutil
    import subprocess
    import sys
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


@app.command("config")
def server_config_show() -> None:
    """Show the resolved server and client configuration."""
    srv = load_server_config()
    cli = load_client_config()
    cfg_dir = get_config_dir()

    console.print(f"\n[bold]Config directory:[/bold] {cfg_dir}")
    console.print("\n[bold]Server config:[/bold]")
    for k, v in srv.items():
        console.print(f"  {k}: {v}")
    console.print("\n[bold]Client config:[/bold]")
    for k, v in cli.items():
        console.print(f"  {k}: {v}")


@app.command("use")
def server_use(
    url: str = typer.Argument(..., help="Server URL, e.g. http://192.168.1.100:8432"),
) -> None:
    """Point the client at a specific server URL."""
    save_client_config({"server_url": url})
    console.print(f"[green]Client will now use server:[/green] {url}")


@app.command("unset")
def server_unset() -> None:
    """Remove the configured server URL (revert to auto-start local server)."""
    save_client_config({"server_url": None})
    console.print("[green]Cleared server_url — will auto-start local server.[/green]")
