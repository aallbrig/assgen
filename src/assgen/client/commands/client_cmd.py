"""assgen client — client-side configuration.

  assgen client config show          display active client settings + resolved server
  assgen client config set-server    point the client at a specific server URL
  assgen client config unset-server  revert to auto-start-local-server mode
"""
from __future__ import annotations


import typer

from assgen.client.output import console
from assgen.config import (
    get_config_dir,
    load_client_config,
    read_pid_file,
    save_client_config,
)

app = typer.Typer(
    help="Client configuration: server targeting and connection settings.",
    no_args_is_help=True,
)

_config_app = typer.Typer(
    help="View and update client configuration.",
    no_args_is_help=True,
)
app.add_typer(_config_app, name="config")


@_config_app.command("show")
def client_config_show() -> None:
    """Show active client configuration and the server this client will use."""
    import os
    cfg = load_client_config()
    cfg_dir = get_config_dir()

    console.print(f"\n[bold]Config directory:[/bold] {cfg_dir}")
    console.print()
    console.print("[bold]Client settings:[/bold]")
    for k, v in cfg.items():
        console.print(f"  {k}: {v}")

    console.print()
    console.print("[bold]Resolved server:[/bold]")

    explicit_url = cfg.get("server_url")
    if explicit_url:
        console.print("  mode:  [cyan]remote (configured)[/cyan]")
        console.print(f"  url:   {explicit_url}")
        _print_health(explicit_url)
    else:
        info = read_pid_file()
        if info:
            pid, url = info
            try:
                os.kill(pid, 0)
                alive = True
            except (ProcessLookupError, PermissionError):
                alive = False
            if alive:
                console.print("  mode:  [yellow]local (auto-started, running)[/yellow]")
                console.print(f"  url:   {url}")
                console.print(f"  pid:   {pid}")
                _print_health(url)
            else:
                console.print("  mode:  [dim]local (auto-start — not running yet)[/dim]")
                console.print("  url:   http://127.0.0.1:8432  [dim](default)[/dim]")
        else:
            console.print("  mode:  [dim]local (auto-start — will launch on first request)[/dim]")
            console.print("  url:   http://127.0.0.1:8432  [dim](default)[/dim]")

    console.print()
    console.print("[dim]Set a remote server:  assgen client config set-server <url>[/dim]")
    console.print("[dim]Clear remote server:  assgen client config unset-server[/dim]")


@_config_app.command("set-server")
def client_set_server(
    url: str = typer.Argument(
        ...,
        help="Server base URL, e.g. http://192.168.1.50:8432",
    ),
) -> None:
    """Point the client at a specific assgen-server (local or remote).

    Once set, all job submissions and queries go to this server rather
    than auto-starting a local one.  Ideal for targeting your desktop GPU.

    Example:
      assgen client config set-server http://192.168.1.50:8432
    """
    if not url.startswith(("http://", "https://")):
        console.print("[red]Error:[/red] URL must start with http:// or https://")
        raise typer.Exit(1)

    save_client_config({"server_url": url})
    console.print(f"[green]✓ Client will now send all requests to:[/green] {url}")
    console.print("[dim]Verify with: assgen client config show[/dim]")

    # Quick health check so the user knows if it's reachable right now
    _print_health(url)


@_config_app.command("unset-server")
def client_unset_server() -> None:
    """Remove the configured server URL (revert to auto-start local server mode).

    After this, running any asset command will automatically start a local
    assgen-server if one is not already running.
    """
    save_client_config({"server_url": None})
    console.print("[green]✓ Cleared server_url[/green] — will auto-start local server on next request.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _print_health(url: str) -> None:
    try:
        import httpx
        r = httpx.get(f"{url.rstrip('/')}/health", timeout=3.0)
        if r.status_code == 200:
            data = r.json()
            console.print(
                f"  health:[green] reachable[/green]  "
                f"version={data.get('version', '?')}"
            )
        else:
            console.print(f"  health:[yellow] HTTP {r.status_code}[/yellow]")
    except Exception as exc:
        console.print(f"  health:[red] unreachable[/red]  ({exc})")
