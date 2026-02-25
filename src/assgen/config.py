"""OS-agnostic configuration and path management for assgen.

Config directory follows the XDG Base Directory spec on Linux/macOS
and %APPDATA% on Windows, via platformdirs.

Layout inside the config dir:
  client.yaml      — client configuration (server URL, defaults)
  server.yaml      — server configuration (host, port, workers, device)
  models.yaml      — user model catalog overrides (merged with built-in catalog)
  assgen.db        — SQLite database (jobs, model usage, etc.)
  server.pid       — local server PID + URL (runtime, not committed)
  outputs/         — default output directory for generated assets
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from platformdirs import user_config_dir, user_data_dir

APP_NAME = "assgen"
APP_AUTHOR = "assgen"


def get_config_dir() -> Path:
    """Return (and create) the OS-appropriate config directory."""
    path = Path(user_config_dir(APP_NAME, APP_AUTHOR))
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_data_dir() -> Path:
    """Return (and create) the OS-appropriate data directory (models cache, outputs)."""
    path = Path(user_data_dir(APP_NAME, APP_AUTHOR))
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_db_path() -> Path:
    return get_config_dir() / "assgen.db"


def get_outputs_dir() -> Path:
    d = get_data_dir() / "outputs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_models_cache_dir() -> Path:
    d = get_data_dir() / "models"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# Config file helpers
# ---------------------------------------------------------------------------

def _load_yaml(path: Path) -> dict[str, Any]:
    if path.exists():
        with path.open() as f:
            return yaml.safe_load(f) or {}
    return {}


def _save_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)


# ---------------------------------------------------------------------------
# Client configuration
# ---------------------------------------------------------------------------

_CLIENT_DEFAULTS: dict[str, Any] = {
    "server_url": None,          # None → auto-start local server
    "default_wait": False,       # --wait default
    "default_timeout": 300,      # seconds before giving up on --wait
    "poll_interval": 2.0,        # seconds between status polls
}


def load_client_config() -> dict[str, Any]:
    path = get_config_dir() / "client.yaml"
    data = {**_CLIENT_DEFAULTS, **_load_yaml(path)}
    # Allow env-var override
    if url := os.environ.get("ASSGEN_SERVER_URL"):
        data["server_url"] = url
    return data


def save_client_config(updates: dict[str, Any]) -> None:
    path = get_config_dir() / "client.yaml"
    data = {**_CLIENT_DEFAULTS, **_load_yaml(path), **updates}
    _save_yaml(path, data)


# ---------------------------------------------------------------------------
# Server configuration
# ---------------------------------------------------------------------------

_SERVER_DEFAULTS: dict[str, Any] = {
    "host": "127.0.0.1",
    "port": 8432,
    "workers": 1,
    "device": "auto",            # "auto" | "cuda" | "cpu"
    "log_level": "info",
    "model_load_timeout": 120,   # seconds to wait for a model to load
    "job_retention_days": 30,    # days to keep completed jobs in DB
}


def load_server_config() -> dict[str, Any]:
    path = get_config_dir() / "server.yaml"
    data = {**_SERVER_DEFAULTS, **_load_yaml(path)}
    # Allow env-var overrides
    if host := os.environ.get("ASSGEN_HOST"):
        data["host"] = host
    if port := os.environ.get("ASSGEN_PORT"):
        data["port"] = int(port)
    if device := os.environ.get("ASSGEN_DEVICE"):
        data["device"] = device
    return data


def save_server_config(updates: dict[str, Any]) -> None:
    path = get_config_dir() / "server.yaml"
    data = {**_SERVER_DEFAULTS, **_load_yaml(path), **updates}
    _save_yaml(path, data)


# ---------------------------------------------------------------------------
# PID file helpers (local server auto-start)
# ---------------------------------------------------------------------------

def get_pid_file() -> Path:
    return get_config_dir() / "server.pid"


def write_pid_file(pid: int, url: str) -> None:
    _save_yaml(get_pid_file(), {"pid": pid, "url": url})


def read_pid_file() -> tuple[int, str] | None:
    data = _load_yaml(get_pid_file())
    if "pid" in data and "url" in data:
        return int(data["pid"]), str(data["url"])
    return None


def remove_pid_file() -> None:
    p = get_pid_file()
    if p.exists():
        p.unlink()
