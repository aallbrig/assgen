"""Entry point for ``python -m assgen``.

Allows the CLI to be invoked without the ``assgen`` script being on PATH::

    python -m assgen --help
    python -m assgen gen visual model create --prompt "low-poly sword"
    python -m assgen tasks
"""
from assgen.client.cli import app

if __name__ == "__main__":
    app()
