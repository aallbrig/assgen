"""Global CLI context flags.

Set by the root CLI callback; consumed by :func:`assgen.client.commands.submit.submit_job`
and the output helpers so that every command automatically honours ``--json`` and
``--variants`` without each leaf command needing to declare them.

Thread-safety note: these are process-global singletons.  The CLI is single-threaded
on the client side so this is safe.
"""
from __future__ import annotations

_json_mode: bool = False
_variants: int = 1


def set_json_mode(enabled: bool) -> None:
    """Enable or disable JSON output mode (``--json`` flag)."""
    global _json_mode
    _json_mode = bool(enabled)


def is_json_mode() -> bool:
    """Return True when ``--json`` was passed on the command line."""
    return _json_mode


def set_variants(n: int) -> None:
    """Set the number of job copies to submit (``--variants N`` flag)."""
    global _variants
    _variants = max(1, int(n))


def get_variants() -> int:
    """Return the current variants count (default: 1)."""
    return _variants


def reset() -> None:
    """Reset all context flags to defaults.  Used in tests."""
    global _json_mode, _variants
    _json_mode = False
    _variants = 1
