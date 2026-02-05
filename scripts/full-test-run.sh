#!/bin/bash
# full-test-run.sh - Full pytest + coverage (dev)
set -euo pipefail

echo "=== Full VariDex Tests (dev) ==="

# Install deps if needed
pip install -r requirements-dev.txt || pip install pytest pytest-cov black pydantic

# Lint/format
black . --check || black .
flake8 varidex/ || echo "Flake8 warnings"

# Tests
pytest tests/ -v --tb=short --cov=varidex --cov-report=html --cov-report=term-missing

# Quick fixes check
grep -r "AttributeError\|no attribute" tests/ | head -5 || echo "No obvious attr errors"

echo "HTML coverage: htmlcov/index.html"
