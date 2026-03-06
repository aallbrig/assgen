"""Tests for assgen.version — version string formatting."""
from __future__ import annotations


def test_format_version_string_contains_name() -> None:
    from assgen.version import format_version_string

    s = format_version_string("assgen")
    assert "assgen" in s


def test_format_version_string_contains_python() -> None:
    from assgen.version import format_version_string

    s = format_version_string("assgen")
    assert "python:" in s


def test_format_version_string_for_server() -> None:
    from assgen.version import format_version_string

    s = format_version_string("assgen-server")
    assert "assgen-server" in s


def test_get_version_returns_string() -> None:
    from assgen.version import get_version_info

    info = get_version_info()
    assert isinstance(info, dict)
    assert "version" in info
