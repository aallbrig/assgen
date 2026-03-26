#!/usr/bin/env python3
"""Export the OpenAPI schema from the assgen-server FastAPI app.

Usage:
    python scripts/export_openapi.py          # writes docs/openapi.json
    python scripts/export_openapi.py --check  # exits non-zero if committed spec is stale
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure the source tree is importable when running from the repo root.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

SPEC_PATH = _REPO_ROOT / "docs" / "openapi.json"


def _get_spec() -> dict:
    from assgen.server.app import create_app

    app = create_app(server_config={
        "host": "127.0.0.1",
        "port": 8432,
        "device": "cpu",
        "allow_list": [],
        "skip_model_validation": True,
    })
    schema = app.openapi()
    # Pin the version so spec diffs aren't noisy on every dev commit.
    schema["info"]["version"] = "0"
    return schema


def _canonical(obj: dict) -> str:
    return json.dumps(obj, indent=2, sort_keys=True) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Compare generated spec against committed file; exit 1 if they differ.",
    )
    args = parser.parse_args()

    spec = _get_spec()
    generated = _canonical(spec)

    if args.check:
        if not SPEC_PATH.exists():
            print(f"ERROR: {SPEC_PATH} does not exist. Run `python scripts/export_openapi.py` first.")
            raise SystemExit(1)
        committed = SPEC_PATH.read_text()
        if committed != generated:
            print(
                f"ERROR: {SPEC_PATH} is out of date.\n"
                "Run `python scripts/export_openapi.py` and commit the result."
            )
            raise SystemExit(1)
        print(f"OK: {SPEC_PATH} is up to date.")
        return

    SPEC_PATH.parent.mkdir(parents=True, exist_ok=True)
    SPEC_PATH.write_text(generated)
    print(f"Wrote {SPEC_PATH}")


if __name__ == "__main__":
    main()
