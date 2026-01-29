#!/bin/bash
# Add CI badges to README.md

BADGE_CI="[![CI](https://github.com/Plantucha/VariDex/workflows/VariDex%20CI/badge.svg)](https://github.com/Plantucha/VariDex/actions)"
BADGE_BLACK="[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)"
BADGE_PYTHON="[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)"

# Check if README exists
if [ -f "README.md" ]; then
    # Add badges after first heading if not already present
    if ! grep -q "badge.svg" README.md; then
        sed -i '1a\\n'"$BADGE_CI"' '"$BADGE_BLACK"' '"$BADGE_PYTHON"'\n' README.md
        echo "✓ Badges added to README.md"
    else
        echo "ℹ Badges already exist in README.md"
    fi
else
    echo "⚠ README.md not found"
fi
