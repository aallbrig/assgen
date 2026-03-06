"""Auto-server lifecycle management.

When the client has no server_url configured, assgen will transparently
start a local assgen-server process and use it for the duration of the
session.  The server persists across CLI invocations (using a PID file)
so that multiple `assgen` commands in quick succession don't each spin up
a new server.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import time

import httpx

from assgen.config import (
    load_client_config,
    load_server_config,
    read_pid_file,
    remove_pid_file,
    write_pid_file,
)

logger = logging.getLogger(__name__)

_STARTUP_TIMEOUT = 15   # seconds to wait for server to become healthy
_STARTUP_POLL    = 0.5  # seconds between health check polls


def get_or_start_server() -> str:
    """Return the server base URL, starting a local server if needed."""
    cfg = load_client_config()

    # 1. Explicit server URL configured (remote server or manual local)
    if cfg.get("server_url"):
        return str(cfg["server_url"])

    # 2. Check for a running local server via PID file
    info = read_pid_file()
    if info:
        pid, url = info
        if _is_process_alive(pid) and _is_server_healthy(url):
            return url
        # Stale PID file
        logger.debug("Stale PID file found — removing")
        remove_pid_file()

    # 3. Start a new local server
    return _start_local_server()


def _start_local_server() -> str:
    from rich.console import Console
    _console = Console(stderr=True)

    srv_cfg = load_server_config()
    host = srv_cfg.get("host", "127.0.0.1")
    port = srv_cfg.get("port", 8432)
    url = f"http://{host}:{port}"

    _console.print(
        f"\n[yellow]⚡ No server detected — starting local assgen-server on {url}[/yellow]\n"
        "[dim]  (It will stay running between commands. Stop with: assgen server stop)[/dim]\n"
    )

    # Find the assgen-server executable in the same Python environment
    server_exe = find_server_executable()

    # On Windows use DETACHED_PROCESS so the server gets its own console and
    # is not killed when the parent terminal closes.  On Unix, start_new_session
    # achieves the same effect via setsid().
    popen_kwargs: dict = dict(
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = (
            subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        )
    else:
        popen_kwargs["start_new_session"] = True

    proc = subprocess.Popen(
        [server_exe, "start", "--host", host, "--port", str(port)],
        **popen_kwargs,
    )

    write_pid_file(proc.pid, url)

    # Wait for the server to become healthy
    deadline = time.monotonic() + _STARTUP_TIMEOUT
    while time.monotonic() < deadline:
        if _is_server_healthy(url):
            _console.print("[green]✓ Server ready[/green]\n")
            return url
        time.sleep(_STARTUP_POLL)

    raise RuntimeError(
        f"Local assgen-server did not become healthy within {_STARTUP_TIMEOUT}s.\n"
        f"Check logs or run `assgen-server start` manually to see errors."
    )


def _is_process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False
    except OSError:
        # Windows raises a bare OSError when the process is not found
        return False


def _is_server_healthy(url: str) -> bool:
    try:
        r = httpx.get(f"{url}/health", timeout=2.0)
        return r.status_code == 200
    except Exception:
        return False


def find_server_executable() -> str:
    """Find assgen-server in PATH or the same venv as the current interpreter.

    Works on Linux, macOS, and Windows (handles ``.exe`` extension).
    """
    import shutil
    if exe := shutil.which("assgen-server"):
        return exe
    # Fallback: same bin/Scripts directory as the current Python interpreter.
    # Windows puts scripts in Scripts\; Linux/macOS use bin/.
    bin_dir = os.path.dirname(sys.executable)
    for name in ("assgen-server.exe", "assgen-server"):
        candidate = os.path.join(bin_dir, name)
        if os.path.isfile(candidate):
            return candidate
    raise FileNotFoundError(
        "Could not find assgen-server. Make sure it is installed: pip install assgen"
    )
