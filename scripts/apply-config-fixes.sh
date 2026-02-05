#!/bin/bash
# apply-config-fixes.sh - Apply VariDexConfig patches (dev-v0.1)
set -euo pipefail

echo "=== VariDexConfig Fixes (dev) ==="

# Backup
cp varidex/core/config.py config.py.backup

# Apply patch (save my previous response as config.patch)
patch -p1 < config.patch || {
    echo "Patch failed; manual apply needed"
    exit 1
}

# Black format
black varidex/core/config.py

echo "Config fixed. Run: pytest test_core_config.py -v"
