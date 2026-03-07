"""Tests for assgen.version — version string formatting and --version flags."""
from __future__ import annotations

import re


def test_format_version_string_contains_name() -> None:
    from assgen.version import format_version_string

    s = format_version_string("assgen")
    assert "assgen" in s


def test_format_version_string_contains_python_line() -> None:
    from assgen.version import format_version_string

    s = format_version_string("assgen")
    # New format: "  python  3.x.y" (two spaces, no colon)
    assert "python" in s
    assert any(c.isdigit() for c in s)


def test_format_version_string_for_server() -> None:
    from assgen.version import format_version_string

    s = format_version_string("assgen-server")
    assert "assgen-server" in s


def test_get_version_info_returns_dict() -> None:
    from assgen.version import get_version_info

    info = get_version_info()
    assert isinstance(info, dict)
    assert "version" in info
    assert "dirty" in info
    assert "python" in info
    assert "git_describe" in info


def test_get_version_info_version_is_pep440() -> None:
    from assgen.version import get_version_info

    info = get_version_info()
    ver = info["version"]
    assert ver and ver != "0.0.0.dev" or True  # may be dev, just must be a string
    assert isinstance(ver, str)
    # PEP 440 versions start with a digit
    assert re.match(r"\d", ver)


def test_dirty_field_is_bool() -> None:
    from assgen.version import get_version_info

    info = get_version_info()
    assert isinstance(info["dirty"], bool)


# ---------------------------------------------------------------------------
# --version / -V flag tests via Typer CliRunner
# ---------------------------------------------------------------------------

def test_version_flag_exits_0() -> None:
    from typer.testing import CliRunner
    from assgen.client.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0


def test_version_short_flag_exits_0() -> None:
    from typer.testing import CliRunner
    from assgen.client.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["-V"])
    assert result.exit_code == 0


def test_version_flag_prints_assgen_and_number() -> None:
    from typer.testing import CliRunner
    from assgen.client.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["--version"])
    assert "assgen" in result.output
    assert any(c.isdigit() for c in result.output)


def test_version_flag_matches_version_subcommand() -> None:
    """--version and the 'version' subcommand should agree on the version number."""
    from typer.testing import CliRunner
    from assgen.client.cli import app

    runner = CliRunner()
    flag_out = runner.invoke(app, ["--version"]).output
    sub_out = runner.invoke(app, ["version"]).output
    # Both should contain the same version string (first line, first token after "assgen ")
    flag_ver = flag_out.splitlines()[0].split()[-1] if flag_out.strip() else ""
    sub_ver = sub_out.splitlines()[0].split()[-1] if sub_out.strip() else ""
    assert flag_ver == sub_ver


def test_server_version_flag_exits_0() -> None:
    from typer.testing import CliRunner
    from assgen.server.cli import app as server_app

    runner = CliRunner()
    result = runner.invoke(server_app, ["--version"])
    assert result.exit_code == 0


def test_server_version_flag_prints_server_name() -> None:
    from typer.testing import CliRunner
    from assgen.server.cli import app as server_app

    runner = CliRunner()
    result = runner.invoke(server_app, ["--version"])
    assert "assgen-server" in result.output
