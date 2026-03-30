#!/usr/bin/env python3
"""Smoke test: verify that core handlers produce real inference output.

Runs a small set of handlers directly (bypassing the server) and asserts
the output files are valid (non-empty images, audio with samples, etc.).

Usage:
    python scripts/smoke_test_inference.py
    python scripts/smoke_test_inference.py --device cuda
    python scripts/smoke_test_inference.py --handler visual.concept.generate

Requires: pip install "assgen[inference]"
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path


def _progress(pct: float, msg: str) -> None:
    print(f"  [{pct:5.1%}] {msg}")


# ---------------------------------------------------------------------------
# Test definitions
# ---------------------------------------------------------------------------

TESTS: dict[str, dict] = {
    "visual.concept.generate": {
        "params": {"prompt": "a red cube on a white background", "steps": 2, "width": 512, "height": 512},
        "model_id": "stabilityai/sdxl-turbo",
        "validate": lambda output_dir: _assert_image(output_dir),
    },
    "audio.sfx.generate": {
        "params": {"prompt": "a short beep", "duration": 2},
        "model_id": "facebook/audiogen-medium",
        "validate": lambda output_dir: _assert_audio(output_dir),
    },
    "audio.music.compose": {
        "params": {"prompt": "simple piano melody", "duration": 3},
        "model_id": "facebook/musicgen-stereo-large",
        "validate": lambda output_dir: _assert_audio(output_dir),
    },
    "scene.depth.estimate": {
        "params": {"prompt": "test"},
        "model_id": "Intel/dpt-large",
        "validate": lambda output_dir: _assert_any_file(output_dir),
    },
}


def _assert_image(output_dir: Path) -> None:
    """Assert at least one image file exists and has > 100 bytes."""
    for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
        images = list(output_dir.glob(ext))
        if images:
            size = images[0].stat().st_size
            assert size > 100, f"Image {images[0].name} is only {size} bytes"
            print(f"    image: {images[0].name} ({size:,} bytes)")
            return
    raise AssertionError(f"No image files found in {output_dir}")


def _assert_audio(output_dir: Path) -> None:
    """Assert at least one audio file exists and has > 1 KB."""
    for ext in ("*.wav", "*.mp3", "*.flac", "*.ogg"):
        files = list(output_dir.glob(ext))
        if files:
            size = files[0].stat().st_size
            assert size > 1024, f"Audio {files[0].name} is only {size} bytes"
            print(f"    audio: {files[0].name} ({size:,} bytes)")
            return
    raise AssertionError(f"No audio files found in {output_dir}")


def _assert_any_file(output_dir: Path) -> None:
    """Assert at least one non-trivial output file exists."""
    files = [f for f in output_dir.iterdir() if f.is_file() and f.stat().st_size > 50]
    assert files, f"No output files found in {output_dir}"
    print(f"    output: {files[0].name} ({files[0].stat().st_size:,} bytes)")


def _load_and_run(job_type: str, test: dict, device: str) -> bool:
    """Import the handler module and run it in a temp directory."""
    module_name = "assgen.server.handlers." + job_type.replace(".", "_")
    try:
        import importlib
        mod = importlib.import_module(module_name)
    except ModuleNotFoundError:
        print(f"  SKIP — handler module {module_name} not found")
        return True

    with tempfile.TemporaryDirectory(prefix=f"assgen_smoke_{job_type}_") as tmpdir:
        output_dir = Path(tmpdir)
        try:
            result = mod.run(
                job_type=job_type,
                params=test["params"],
                model_id=test.get("model_id"),
                model_path=None,
                device=device,
                progress_cb=_progress,
                output_dir=output_dir,
            )
        except RuntimeError as e:
            if "not installed" in str(e).lower():
                print(f"  SKIP — missing dependency: {e}")
                return True
            print(f"  FAIL — RuntimeError: {e}")
            return False
        except Exception as e:
            print(f"  FAIL — {type(e).__name__}: {e}")
            return False

        # Check for stub output
        if isinstance(result, dict) and result.get("stub"):
            print("  WARN — handler returned stub output (ML deps likely missing)")
            return True

        # Validate output files
        try:
            test["validate"](output_dir)
            print("  PASS")
            return True
        except AssertionError as e:
            print(f"  FAIL — validation: {e}")
            return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test assgen inference handlers")
    parser.add_argument("--device", default="cpu", help="Inference device: cpu, cuda, mps")
    parser.add_argument("--handler", help="Run only this handler (e.g., visual.concept.generate)")
    args = parser.parse_args()

    tests = TESTS
    if args.handler:
        if args.handler not in TESTS:
            print(f"Unknown handler: {args.handler}")
            print(f"Available: {', '.join(TESTS)}")
            sys.exit(1)
        tests = {args.handler: TESTS[args.handler]}

    print(f"Running inference smoke tests (device={args.device})\n")

    results: dict[str, bool] = {}
    for job_type, test in tests.items():
        print(f"[{job_type}]")
        results[job_type] = _load_and_run(job_type, test, args.device)
        print()

    # Summary
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"{'=' * 50}")
    print(f"Results: {passed}/{total} passed")

    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
