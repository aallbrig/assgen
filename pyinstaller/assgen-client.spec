# PyInstaller spec for the assgen CLIENT binary.
#
# Produces a single-file executable:
#   dist/assgen        (Linux / macOS)
#   dist/assgen.exe    (Windows)
#
# Usage:
#   pip install pyinstaller
#   pyinstaller pyinstaller/assgen-client.spec
#
# The server is intentionally NOT bundled here — it requires PyTorch
# which is multi-GB and unsuitable for a standalone binary.
# Users run the server via Docker or `pip install assgen[inference]`.

import sys
from pathlib import Path

# Resolve the package root so spec works from any CWD
HERE = Path(SPECPATH)  # noqa: F821 — injected by PyInstaller
SRC  = HERE.parent / "src"

block_cipher = None

a = Analysis(
    [str(SRC / "assgen" / "__main__.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=[
        # Embed the built-in model catalog
        (str(SRC / "assgen" / "catalog.yaml"), "assgen"),
    ],
    hiddenimports=[
        # typer internals
        "typer",
        "typer.main",
        "typer.core",
        "click",
        "click.exceptions",
        # rich
        "rich",
        "rich.console",
        "rich.progress",
        "rich.table",
        "rich.text",
        "rich.panel",
        "rich.markup",
        "rich.style",
        "rich.theme",
        "rich.live",
        # httpx
        "httpx",
        "httpx._transports.default",
        # yaml
        "yaml",
        # platformdirs
        "platformdirs",
        # huggingface_hub (used by `assgen models search`)
        "huggingface_hub",
        "huggingface_hub.utils",
        # pydantic
        "pydantic",
        "pydantic.networks",
        # assgen client subcommands (dynamic imports via Typer)
        "assgen.client.commands.gen",
        "assgen.client.commands.jobs",
        "assgen.client.commands.models",
        "assgen.client.commands.server",
        "assgen.client.commands.tasks",
        "assgen.client.commands.config",
        "assgen.client.commands.client_cmd",
        "assgen.client.commands.upgrade",
        "assgen.client.auto_server",
        "assgen.client.api",
        "assgen.client.output",
        "assgen.catalog",
        "assgen.config",
        "assgen.db",
        "assgen.version",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Heavy ML libraries — not needed in the client
        "torch",
        "torchvision",
        "torchaudio",
        "transformers",
        "diffusers",
        "accelerate",
        "numpy",
        "scipy",
        "sklearn",
        "matplotlib",
        # Server-only
        "fastapi",
        "uvicorn",
        "starlette",
        # Misc dev deps
        "pytest",
        "IPython",
        "jupyter",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="assgen",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    # Icon can be added here:  icon="assets/assgen.ico"
)
