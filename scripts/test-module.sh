#!/bin/bash
# test-module.sh MODULE [OPTIONS] - Run pytest on module
MODULE=${1:-test_core_config}
OPTS=${2:-"-v"}

echo "=== Testing $MODULE $OPTS ==="

pytest "$MODULE.py" $OPTS --tb=short || {
    echo "Failures logged; check above"
    exit 1
}

echo "PASS: $MODULE"
coverage report "$MODULE.py" || true
