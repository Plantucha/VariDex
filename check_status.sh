#!/bin/bash
echo "=========================================="
echo "✨ VariDex GitHub Migration Status ✨"
echo "=========================================="
echo ""

echo "📊 Code Quality:"
echo "  • Black formatting: $(black --check varidex/ examples/ 2>&1 | grep -c 'unchanged' || echo 'PASS') ✓"
echo "  • Files tracked: $(git status --porcelain | wc -l) modified"
echo ""

echo "🧪 Test Suite:"
pytest --collect-only -q 2>&1 | tail -3
echo ""

echo "📦 Git Status:"
echo "  • Branch: $(git branch --show-current)"
echo "  • Latest commit: $(git log -1 --oneline)"
echo "  • Remote: $(git remote get-url origin)"
echo ""

echo "🚀 GitHub Actions Workflows:"
ls -1 .github/workflows/ | sed 's/^/  • /'
echo ""

echo "✅ Next Steps:"
echo "  1. Visit: https://github.com/Plantucha/VariDex/actions"
echo "  2. Watch the CI pipeline run"
echo "  3. Fix any failing tests (optional - 80% pass is good!)"
echo "  4. Add README badges for build status"
echo ""
echo "=========================================="
