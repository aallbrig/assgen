"""Structured logging for assgen-server.

Outputs JSON lines compatible with systemd/journald when running as a service,
and falls back to a human-readable format for interactive terminals.

journalctl tips:
  journalctl -u assgen-server -f                    # follow
  journalctl -u assgen-server -o json               # raw JSON
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone


class _JournaldFormatter(logging.Formatter):
    """Emit one JSON object per line — journald SYSLOG_IDENTIFIER is set by
    the systemd unit; we include all interesting fields as structured data
    so `journalctl -o json` exposes them for querying."""

    def format(self, record: logging.LogRecord) -> str:
        now = datetime.now(timezone.utc).isoformat()
        obj: dict = {
            "timestamp": now,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            obj["exception"] = self.formatException(record.exc_info)
        # Merge any extra fields passed via `extra=` kwarg
        for k, v in record.__dict__.items():
            if k not in (
                "args", "asctime", "created", "exc_info", "exc_text",
                "filename", "funcName", "id", "levelname", "levelno",
                "lineno", "message", "module", "msecs", "msg", "name",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "taskName", "thread", "threadName",
            ):
                obj[k] = v
        return json.dumps(obj, default=str)


class _HumanFormatter(logging.Formatter):
    COLORS = {
        "DEBUG":    "\033[36m",   # cyan
        "INFO":     "\033[32m",   # green
        "WARNING":  "\033[33m",   # yellow
        "ERROR":    "\033[31m",   # red
        "CRITICAL": "\033[35m",   # magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        color = self.COLORS.get(record.levelname, "")
        msg = record.getMessage()
        line = f"{ts}  {color}{record.levelname:<8}{self.RESET}  {record.name}  {msg}"
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


def setup_logging(level: str = "info", force_json: bool = False) -> None:
    """Configure root logger for assgen-server.

    Uses JSON output when:
      - ``force_json=True``
      - ``JOURNAL_STREAM`` env var is set (systemd sets this)
      - stdout is not a TTY (piped / redirected)
    """
    numeric = getattr(logging, level.upper(), logging.INFO)

    use_json = (
        force_json
        or bool(os.environ.get("JOURNAL_STREAM"))
        or not sys.stdout.isatty()
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JournaldFormatter() if use_json else _HumanFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(numeric)

    # Quiet noisy third-party loggers
    for name in ("uvicorn.access", "httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)
