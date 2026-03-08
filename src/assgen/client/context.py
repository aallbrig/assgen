"""Global CLI context flags.

Set by the root CLI callback; consumed by :func:`assgen.client.commands.submit.submit_job`
and the output helpers so that every command automatically honours ``--json``,
``--variants``, ``--quality``, and ``--from-job`` without each leaf command
needing to declare them.

Thread-safety note: these are process-global singletons.  The CLI is single-threaded
on the client side so this is safe.
"""
from __future__ import annotations

_json_mode: bool = False
_variants: int = 1
_quality: str = "standard"
_from_job: str | None = None


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


def set_quality(tier: str) -> None:
    """Set the quality tier: draft | standard | high."""
    global _quality
    tier = tier.lower()
    if tier not in {"draft", "standard", "high"}:
        raise ValueError(f"Invalid quality tier '{tier}'. Use: draft, standard, high.")
    _quality = tier


def get_quality() -> str:
    """Return the current quality tier (default: 'standard')."""
    return _quality


def set_from_job(job_id: str | None) -> None:
    """Set the upstream job ID for chaining (``--from-job`` flag)."""
    global _from_job
    _from_job = job_id


def get_from_job() -> str | None:
    """Return the upstream job ID, or None if not set."""
    return _from_job


def reset() -> None:
    """Reset all context flags to defaults.  Used in tests."""
    global _json_mode, _variants, _quality, _from_job
    _json_mode = False
    _variants = 1
    _quality = "standard"
    _from_job = None
