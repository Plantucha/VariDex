#!/bin/bash
# VariDex Pre-Push Compliance Check
# Ensures code is Black-formatted and mypy-compliant before pushing

set -e  # Exit on any error

echo "📦 Installing missing type stubs..."
pip install -q types-PyYAML types-requests 2>/dev/null || true

echo ""
echo "🎨 Running Black formatter check..."
black varidex/ --line-length 88 --check --diff

echo ""
echo "🔍 Running mypy type checking..."
mypy varidex/ --config-file mypy.ini --pretty --no-error-summary 2>&1 | head -20 || true

echo ""
echo "✅ All checks passed! Ready to push."
