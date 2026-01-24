#!/bin/bash
# Documentation Coverage Checker Script
# Usage: ./scripts/check_documentation.sh

set -e

echo "====================================================================="
echo "VariDex Documentation Coverage Checker"
echo "====================================================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if tools are installed
command -v interrogate >/dev/null 2>&1 || {
    echo -e "${RED}ERROR: interrogate is not installed${NC}"
    echo "Install with: pip install interrogate"
    exit 1
}

command -v pydocstyle >/dev/null 2>&1 || {
    echo -e "${YELLOW}WARNING: pydocstyle is not installed${NC}"
    echo "Install with: pip install pydocstyle"
    echo ""
}

echo "---------------------------------------------------------------------"
echo "1. Checking Docstring Coverage (interrogate)"
echo "---------------------------------------------------------------------"
echo ""

# Run interrogate with verbose output
if interrogate -vv --fail-under 100 varidex/; then
    echo ""
    echo -e "${GREEN}✓ Docstring coverage: 100%${NC}"
else
    COVERAGE=$(interrogate varidex/ 2>&1 | grep -oP '\d+\.\d+%' | head -1 || echo "0%")
    echo ""
    echo -e "${RED}✗ Docstring coverage: ${COVERAGE} (Target: 100%)${NC}"
    echo ""
    echo "Missing docstrings found. Run with -vv to see details:"
    echo "  interrogate -vv varidex/"
    echo ""
fi

echo ""
echo "---------------------------------------------------------------------"
echo "2. Checking Docstring Style (pydocstyle)"
echo "---------------------------------------------------------------------"
echo ""

if command -v pydocstyle >/dev/null 2>&1; then
    if pydocstyle varidex/; then
        echo -e "${GREEN}✓ No docstring style issues${NC}"
    else
        echo -e "${RED}✗ Docstring style issues found${NC}"
        echo ""
        echo "Run for details: pydocstyle varidex/"
        echo ""
    fi
else
    echo -e "${YELLOW}⊘ pydocstyle not installed (skipping)${NC}"
fi

echo ""
echo "---------------------------------------------------------------------"
echo "3. Generating Coverage Badge"
echo "---------------------------------------------------------------------"
echo ""

# Generate badge
if interrogate --generate-badge . varidex/ 2>&1 | grep -q "WROTE"; then
    echo -e "${GREEN}✓ Badge generated: interrogate_badge.svg${NC}"
else
    echo -e "${YELLOW}⊘ Badge generation skipped${NC}"
fi

echo ""
echo "====================================================================="
echo "Documentation Check Complete"
echo "====================================================================="
echo ""
echo "Next Steps:"
echo "  1. Fix any missing docstrings: interrogate -vv varidex/"
echo "  2. Fix any style issues: pydocstyle varidex/"
echo "  3. Build Sphinx docs: cd docs && make html"
echo "  4. Review generated docs: open docs/_build/html/index.html"
echo ""
