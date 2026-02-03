#!/bin/bash
echo "=========================================="
echo "VariDex Code Compliance Check"
echo "=========================================="
echo ""

echo "✓ Black Formatting:"
black --check varidex/ examples/ 2>&1 | tail -2

echo ""
echo "✓ Mypy Type Checking (showing error count):"
mypy varidex/ --ignore-missing-imports --no-strict-optional 2>&1 | grep "Found.*errors"

echo ""
echo "✓ Pytest (running quick check):"
pytest --collect-only -q 2>&1 | tail -3

echo ""
echo "✓ Git Status:"
git status --short | wc -l | xargs echo "Modified files:"

echo ""
echo "=========================================="
