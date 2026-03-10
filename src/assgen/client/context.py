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
_yaml_mode: bool = False
_variants: int = 1
_quality: str = "standard"
_from_job: str | None = None
_context_map: dict[str, str] = {}  # key=job_id pairs from --context flags


def set_json_mode(enabled: bool) -> None:
    """Enable or disable JSON output mode (``--json`` flag)."""
    global _json_mode
    _json_mode = bool(enabled)


def is_json_mode() -> bool:
    """Return True when ``--json`` was passed on the command line."""
    return _json_mode


def set_yaml_mode(enabled: bool) -> None:
    """Enable or disable YAML output mode (``--yaml`` flag)."""
    global _yaml_mode
    _yaml_mode = bool(enabled)


def is_yaml_mode() -> bool:
    """Return True when ``--yaml`` was passed on the command line."""
    return _yaml_mode


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


def set_context_map(entries: list[str]) -> None:
    """Parse and store ``key=job_id`` strings from ``--context`` flags.

    Args:
        entries: List of ``"key=job_id"`` strings.  Each key names the context
                 slot; each job_id will be resolved to file content at submit time.

    Raises:
        ValueError: If any entry is not in ``key=job_id`` form.
    """
    global _context_map
    _context_map = {}
    for entry in entries:
        if "=" not in entry:
            raise ValueError(
                f"--context entries must be in 'key=job_id' form, got: {entry!r}"
            )
        key, _, job_id = entry.partition("=")
        _context_map[key.strip()] = job_id.strip()


def get_context_map() -> dict[str, str]:
    """Return the pending context map (key → job_id, not yet resolved to text)."""
    return dict(_context_map)


def reset() -> None:
    """Reset all context flags to defaults.  Used in tests."""
    global _json_mode, _variants, _quality, _from_job, _context_map
    _json_mode = False
    _yaml_mode = False
    _variants = 1
    _quality = "standard"
    _from_job = None
    _context_map = {}
