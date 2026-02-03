#!/bin/bash
# Check GitHub Actions CI/CD status
# Usage: ./scripts/check_ci_status.sh [commit-sha]

set -e

REPO="Plantucha/VariDex"
COMMIT_SHA="${1:-HEAD}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Checking CI/CD Status for ${REPO}${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Get latest commit if HEAD specified
if [ "$COMMIT_SHA" = "HEAD" ]; then
    COMMIT_SHA=$(git rev-parse HEAD)
fi

echo -e "${YELLOW}Commit: ${COMMIT_SHA:0:7}${NC}"
echo ""

# Check GitHub Actions (requires gh CLI)
if command -v gh &> /dev/null; then
    echo -e "${BLUE}📊 GitHub Actions Workflows:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # List recent workflow runs
    gh run list --repo "$REPO" --limit 5 --json name,status,conclusion,headSha,createdAt --jq '.[] | select(.headSha == "'$COMMIT_SHA'") | "\(.name): \(.conclusion // .status)"'
    
    if [ $? -ne 0 ]; then
        echo -e "${YELLOW}⚠️  No workflow runs found for this commit yet${NC}"
        echo -e "${BLUE}   Showing latest runs:${NC}"
        gh run list --repo "$REPO" --limit 5
    fi
    
    echo ""
    echo -e "${BLUE}🔗 View all runs:${NC}"
    echo -e "   https://github.com/${REPO}/actions"
    
else
    echo -e "${YELLOW}⚠️  GitHub CLI (gh) not installed${NC}"
    echo -e "   Install: https://cli.github.com/"
    echo -e "   Or view online: https://github.com/${REPO}/actions${NC}"
fi

echo ""
echo -e "${BLUE}📋 Expected Workflows:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✓${NC} Code Quality Checks (Python 3.12, Black, MyPy)"
echo -e "${GREEN}✓${NC} Test Suite (Python 3.9-3.12, Ubuntu/macOS/Windows)"
echo -e "${GREEN}✓${NC} Security Scanning (Bandit, detect-secrets, Safety)"
echo ""

echo -e "${BLUE}💡 Quick Commands:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  View latest run:     gh run view --repo $REPO"
echo "  Watch workflow:      gh run watch --repo $REPO"
echo "  List all runs:       gh run list --repo $REPO"
echo "  Re-run failed:       gh run rerun --repo $REPO <run-id>"
echo ""

echo -e "${BLUE}🛠️  Local Checks (run before push):${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Format code:         black varidex/ tests/"
echo "  Type check:          mypy varidex/ --ignore-missing-imports"
echo "  Run tests:           pytest"
echo "  Secret scan:         detect-secrets scan --baseline .secrets.baseline"
echo "  Pre-commit:          pre-commit run --all-files"
echo ""

# Check if there are uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "${YELLOW}⚠️  You have uncommitted changes${NC}"
    echo -e "   Run: git status"
fi
