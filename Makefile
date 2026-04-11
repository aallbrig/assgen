.PHONY: dev test test-cov lint lint-check docs docs-build serve clean demo demo-clean

# Install in editable mode with all dev dependencies
dev:
	pip install -e ".[dev,inference]"

# Run the full test suite
test:
	pytest -v

# Run the full test suite with coverage
test-cov:
	pytest -v --cov=src/assgen --cov-report=term-missing --cov-report=html

# Lint and auto-fix
lint:
	ruff check --fix src/ tests/

# Lint without auto-fix (CI mode)
lint-check:
	ruff check src/ tests/

# Build and serve docs locally
docs:
	pip install -e ".[docs]"
	mkdocs serve

# Build docs static site
docs-build:
	mkdocs build

# Run the server locally (foreground, auto-device)
serve:
	assgen-server start --log-level debug

# Remove build artifacts and caches
clean:
	rm -rf dist/ build/ .pytest_cache/ htmlcov/ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

## demo: record all VHS tapes and produce dist/demo.mp4
demo:
	bash scripts/record-demo.sh

## demo-clean: remove recorded segments and final video
demo-clean:
	rm -rf demos/segments dist/demo.mp4
