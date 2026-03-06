"""assgen upgrade — check GitHub releases and optionally install the latest."""
from __future__ import annotations

import sys


import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from assgen.version import get_version_info

console = Console()

REPO = "aallbrig/assgen"
RELEASES_API = f"https://api.github.com/repos/{REPO}/releases"
RELEASES_URL = f"https://github.com/{REPO}/releases"

app = typer.Typer(
    help="Check for and install the latest assgen release.",
    invoke_without_command=True,
    no_args_is_help=False,
)


@app.callback(invoke_without_command=True)
def upgrade(
    ctx: typer.Context,
    check: bool = typer.Option(False, "--check", help="Only check — do not install"),
    pre: bool = typer.Option(False, "--pre", help="Include pre-release versions"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Check for and install the latest assgen release from GitHub.

    Compares the running version against GitHub Releases and, if a newer
    version is available, upgrades via pip.

    Examples:
      assgen upgrade              # check and prompt
      assgen upgrade --check      # check only, exit 0 if up-to-date, 1 if outdated
      assgen upgrade --yes        # upgrade without confirmation
      assgen upgrade --pre        # include pre-releases
    """
    if ctx.invoked_subcommand:
        return

    info = get_version_info()
    current = info.get("version") or "unknown"

    console.print(f"\n[bold]Current version:[/bold] [cyan]{current}[/cyan]")
    console.print("[dim]Checking GitHub for latest release…[/dim]")

    latest_tag, latest_info = _fetch_latest(pre=pre)

    if latest_tag is None:
        console.print("[yellow]⚠[/yellow]  Could not reach GitHub — check your connection.")
        raise typer.Exit(1)

    latest_version = latest_tag.lstrip("v")
    is_newer = _version_is_newer(latest_version, current)

    if not is_newer:
        console.print(
            f"[green]✓[/green]  You are running the latest release "
            f"([cyan]{current}[/cyan]).\n"
        )
        raise typer.Exit(0)

    # Newer version available
    _print_release_summary(latest_tag, latest_info)

    if check:
        console.print(
            f"[yellow]![/yellow]  New version available: "
            f"[cyan]{latest_version}[/cyan] (you have [dim]{current}[/dim])"
        )
        raise typer.Exit(1)  # non-zero so scripts can detect "outdated"

    if not yes:
        confirmed = typer.confirm(
            f"\nUpgrade from {current} → {latest_version}?", default=True
        )
        if not confirmed:
            console.print("[dim]Upgrade cancelled.[/dim]")
            raise typer.Exit(0)

    _do_upgrade(latest_version)


# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------

def _fetch_latest(pre: bool = False) -> tuple[str | None, dict | None]:
    """Return (tag_name, release_dict) for the newest applicable release."""
    try:
        import httpx
        if not pre:
            # /releases/latest always returns the newest non-prerelease
            r = httpx.get(f"{RELEASES_API}/latest", timeout=10.0, follow_redirects=True)
            if r.status_code == 200:
                data = r.json()
                return data.get("tag_name"), data
            # fall through to list endpoint if latest not available
        r = httpx.get(RELEASES_API, timeout=10.0, follow_redirects=True)
        if r.status_code != 200:
            return None, None
        releases = r.json()
        for rel in releases:
            if not pre and rel.get("prerelease"):
                continue
            return rel.get("tag_name"), rel
    except Exception as exc:
        console.print(f"[dim]GitHub API error: {exc}[/dim]")
    return None, None


def _print_release_summary(tag: str, rel: dict) -> None:
    version = tag.lstrip("v")
    name = rel.get("name") or tag
    body = (rel.get("body") or "").strip()
    published = (rel.get("published_at") or "")[:10]

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_row("[bold]Version[/bold]", f"[cyan]{version}[/cyan]")
    table.add_row("[bold]Published[/bold]", published)
    table.add_row("[bold]Release page[/bold]", f"[link={RELEASES_URL}/tag/{tag}]{RELEASES_URL}/tag/{tag}[/link]")

    console.print()
    console.print(Panel(table, title=f"[bold green]New release: {name}[/bold green]", expand=False))

    if body:
        # Truncate long release notes
        lines = body.splitlines()[:12]
        if len(body.splitlines()) > 12:
            lines.append("[dim]…(see release page for full notes)[/dim]")
        console.print("\n[bold]Release notes:[/bold]")
        for line in lines:
            console.print(f"  {line}")
    console.print()


# ---------------------------------------------------------------------------
# Installation helpers
# ---------------------------------------------------------------------------

def _do_upgrade(version: str) -> None:
    """Run pip install --upgrade assgen=={version} in the current Python env."""
    import subprocess

    pip = _find_pip()
    cmd = [pip, "install", f"assgen=={version}"]

    console.print(f"[bold]Running:[/bold] {' '.join(cmd)}")
    result = subprocess.run(cmd, check=False)

    if result.returncode == 0:
        console.print(f"\n[green]✓[/green]  Upgraded to [cyan]{version}[/cyan].\n")
    else:
        console.print(
            "\n[red]✗[/red]  pip exited with a non-zero status.\n"
            f"You can upgrade manually:\n"
            f"  pip install assgen=={version}\n"
            f"  or download from: {RELEASES_URL}\n"
        )
        raise typer.Exit(result.returncode)


def _find_pip() -> str:
    """Return an appropriate pip executable for the current Python environment."""
    import shutil

    # 1. pip next to the running Python (handles venvs correctly)
    python = sys.executable
    candidate = str(__import__("pathlib").Path(python).parent / "pip")
    if __import__("pathlib").Path(candidate).exists():
        return candidate

    # 2. pip3 / pip on PATH
    for name in ("pip3", "pip"):
        found = shutil.which(name)
        if found:
            return found

    # 3. Fallback: python -m pip
    return f"{python} -m pip"


# ---------------------------------------------------------------------------
# Version comparison (PEP 440-ish, no external deps)
# ---------------------------------------------------------------------------

def _parse_version(v: str) -> tuple[int, ...]:
    """Parse a version string like '0.1.2' or '0.1.dev5' into a sortable tuple."""
    import re
    v = v.strip().lstrip("v")
    # Strip local / dev suffixes for comparison
    v = re.split(r"[+-]", v)[0]
    v = re.sub(r"\.dev\d*$", "", v)
    try:
        return tuple(int(x) for x in v.split(".") if x.isdigit())
    except ValueError:
        return (0,)


def _version_is_newer(candidate: str, current: str) -> bool:
    """Return True if *candidate* is strictly newer than *current*."""
    c_parts = _parse_version(candidate)
    r_parts = _parse_version(current)
    return c_parts > r_parts
