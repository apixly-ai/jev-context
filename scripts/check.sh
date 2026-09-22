#!/bin/sh
set -eu
python -m ruff check src tests benchmarks scripts
python -m ruff format --check src tests benchmarks scripts
python -m pytest --cov=jev_context --cov-report=term-missing
python -m benchmarks.run --output "$(mktemp -u)/offline.json"
python -m build
python -m twine check dist/*.whl dist/*.tar.gz
python scripts/check_public.py
