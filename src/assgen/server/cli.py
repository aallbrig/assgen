"""assgen-server — entry point CLI.

Usage:
  assgen-server start              # start the server (foreground)
  assgen-server start --daemon     # detach and write PID file
  assgen-server stop               # send SIGTERM to local server
  assgen-server status             # show server status
  assgen-server version            # print version and exit
"""
from __future__ import annotations

import os
import signal
import sys
from typing import Optional

import typer
import uvicorn

from assgen.config import (
    get_config_dir,
    load_server_config,
    read_pid_file,
    remove_pid_file,
    write_pid_file,
)
from assgen.server.logging_setup import setup_logging
from assgen.version import format_version_string

app = typer.Typer(
    name="assgen-server",
    help="assgen asset generation server — processes job requests from assgen clients.",
    no_args_is_help=True,
    add_completion=False,
)


@app.command()
def start(
    host: Optional[str] = typer.Option(None, help="Bind host (default from config)"),
    port: Optional[int] = typer.Option(None, help="Bind port (default from config)"),
    workers: Optional[int] = typer.Option(None, help="Number of uvicorn workers"),
    device: Optional[str] = typer.Option(None, help="Inference device: auto|cuda|cpu"),
    log_level: str = typer.Option("info", help="Log level: debug|info|warning|error"),
    json_logs: bool = typer.Option(False, "--json-logs", help="Force JSON log output"),
    daemon: bool = typer.Option(False, "--daemon", help="Detach and run as daemon"),
) -> None:
    """Start the assgen-server."""
    setup_logging(log_level, force_json=json_logs)

    cfg = load_server_config()
    if host:
        cfg["host"] = host
    if port:
        cfg["port"] = port
    if workers:
        cfg["workers"] = workers
    if device:
        cfg["device"] = device

    _host = cfg["host"]
    _port = cfg["port"]
    url = f"http://{_host}:{_port}"

    if daemon:
        _daemonise(cfg, log_level, json_logs)
        return

    write_pid_file(os.getpid(), url)
    try:
        from assgen.server.app import create_app
        uvicorn.run(
            create_app(cfg),
            host=_host,
            port=_port,
            log_level=log_level,
            access_log=False,  # we handle access logging ourselves
        )
    finally:
        remove_pid_file()


@app.command()
def stop() -> None:
    """Stop a locally running assgen-server."""
    info = read_pid_file()
    if not info:
        typer.echo("No local server PID file found.", err=True)
        raise typer.Exit(1)
    pid, url = info
    try:
        os.kill(pid, signal.SIGTERM)
        remove_pid_file()
        typer.echo(f"Sent SIGTERM to pid {pid} ({url})")
    except ProcessLookupError:
        typer.echo(f"Process {pid} not found — removing stale PID file.", err=True)
        remove_pid_file()
        raise typer.Exit(1)


@app.command()
def status() -> None:
    """Show whether a local assgen-server is running."""
    info = read_pid_file()
    if not info:
        typer.echo("No local server running (no PID file).")
        return
    pid, url = info
    try:
        os.kill(pid, 0)  # no-op signal: raises if process doesn't exist
        typer.echo(f"Running  pid={pid}  url={url}")
    except ProcessLookupError:
        typer.echo(f"Stale PID file — process {pid} is not running.", err=True)
        remove_pid_file()
        raise typer.Exit(1)


@app.command(name="version")
def version_cmd() -> None:
    """Print version information and exit."""
    typer.echo(format_version_string("assgen-server"))


# ---------------------------------------------------------------------------
# Daemon helper
# ---------------------------------------------------------------------------

def _daemonise(cfg: dict, log_level: str, json_logs: bool) -> None:
    """Fork and start the server in the background, writing a PID file."""
    _host = cfg["host"]
    _port = cfg["port"]
    url = f"http://{_host}:{_port}"

    pid = os.fork()  # type: ignore[attr-defined]
    if pid > 0:
        # Parent: write PID file and exit
        write_pid_file(pid, url)
        typer.echo(f"Server started: pid={pid}  url={url}")
        typer.echo(f"Config dir: {get_config_dir()}")
        return

    # Child: detach and start uvicorn
    os.setsid()  # type: ignore[attr-defined]
    setup_logging(log_level, force_json=json_logs)
    from assgen.server.app import create_app
    write_pid_file(os.getpid(), url)
    uvicorn.run(create_app(cfg), host=_host, port=_port, log_level=log_level, access_log=False)
    remove_pid_file()
    sys.exit(0)
