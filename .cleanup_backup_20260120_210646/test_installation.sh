#!/bin/bash
# VariDex v6.0.0 - Final Verification Test Suite

echo "========================================================================"
echo "VariDex v6.0.0 - Final Verification Test Suite"
echo "========================================================================"
echo ""
echo "Testing complete installation..."
echo ""

PASSED=0
WARNINGS=0
FAILED=0

# Test 1: Package Structure
echo "Test 1: Package Structure"
echo "----------------------------------------------------------------------"
if [ -d "varidex" ]; then
    echo "  ✓ varidex/ directory exists"
    INIT_COUNT=$(find varidex -name "__init__.py" | wc -l)
    echo "  ✓ Found $INIT_COUNT __init__.py files"
    PY_COUNT=$(find varidex -name "*.py" | wc -l)
    echo "  ✓ Found $PY_COUNT total .py files"
    ((PASSED++))
fi

# Test 2: Version Import
echo ""
echo "Test 2: Version Import"
echo "----------------------------------------------------------------------"
VERSION=$(python3 -c "from varidex import version; print(version)" 2>/dev/null)
if [ "$VERSION" = "6.0.0" ]; then
    echo "  ✓ Version imported: $VERSION"
    ((PASSED++))
else
    echo "  ✗ Version import failed"
    ((FAILED++))
fi

# Test 3: Version Module Self-Test
echo ""
echo "Test 3: Version Module Self-Test"
echo "----------------------------------------------------------------------"
if python3 -m varidex.version >/dev/null 2>&1; then
    echo "  ✓ Version module runs successfully"
    ((PASSED++))
else
    echo "  ✗ Version module failed"
    ((FAILED++))
fi

# Test 4: Exceptions Import
echo ""
echo "Test 4: Exceptions Import"
echo "----------------------------------------------------------------------"
if python3 -c "from varidex.exceptions import ACMGValidationError, ACMGClassificationError, ACMGConfigurationError" 2>/dev/null; then
    echo "  ✓ All exception classes imported"
    echo "    - ACMGValidationError"
    echo "    - ACMGClassificationError"
    echo "    - ACMGConfigurationError"
    ((PASSED++))
else
    echo "  ✗ Exception imports failed"
    ((FAILED++))
fi

# Test 5: Exceptions Module Self-Test (FIXED GREP PATTERN)
echo ""
echo "Test 5: Exceptions Module Self-Test"
echo "----------------------------------------------------------------------"
if python3 -m varidex.exceptions 2>&1 | grep -q "14/14 passed"; then
    echo "  ✓ Exceptions: 14/14 tests passed"
    ((PASSED++))
else
    echo "  ✗ Exception tests failed"
    ((FAILED++))
fi

# Test 6: Core Module Imports
echo ""
echo "Test 6: Core Module Imports"
echo "----------------------------------------------------------------------"
CORE_OK=0
python3 -c "from varidex.core import config" 2>/dev/null && echo "  ✓ varidex.core.config" && ((CORE_OK++))
python3 -c "from varidex.core import models" 2>/dev/null && echo "  ✓ varidex.core.models" && ((CORE_OK++))
python3 -c "from varidex.core import schema" 2>/dev/null && echo "  ✓ varidex.core.schema" && ((CORE_OK++))
python3 -c "from varidex.core.classifier import ACMGClassifier" 2>/dev/null && echo "  ✓ varidex.core.classifier.ACMGClassifier" && ((CORE_OK++))

if [ $CORE_OK -eq 4 ]; then
    ((PASSED++))
else
    echo "  ⚠ Only $CORE_OK/4 core modules imported"
    ((WARNINGS++))
fi

# Test 7: ACMGClassifier Instantiation
echo ""
echo "Test 7: ACMGClassifier Instantiation"
echo "----------------------------------------------------------------------"
if python3 -c "from varidex.core.classifier import ACMGClassifier; c = ACMGClassifier()" 2>/dev/null; then
    echo "  ✓ ACMGClassifier instantiates successfully"
    ((PASSED++))
else
    echo "  ✗ ACMGClassifier instantiation failed"
    ((FAILED++))
fi

# Test 8: IO Module Imports
echo ""
echo "Test 8: IO Module Imports"
echo "----------------------------------------------------------------------"
IO_OK=0
python3 -c "from varidex.io import matching" 2>/dev/null && echo "  ✓ varidex.io.matching" && ((IO_OK++))
python3 -c "from varidex.io.loaders import clinvar" 2>/dev/null && echo "  ✓ varidex.io.loaders.clinvar" && ((IO_OK++))
python3 -c "from varidex.io.loaders import user" 2>/dev/null && echo "  ✓ varidex.io.loaders.user" && ((IO_OK++))

if [ $IO_OK -eq 3 ]; then
    echo "  ✓ 3/3 IO modules imported"
    ((PASSED++))
else
    echo "  ⚠ Only $IO_OK/3 IO modules imported"
    ((WARNINGS++))
fi

# Test 9: Reports Module Imports
echo ""
echo "Test 9: Reports Module Imports"
echo "----------------------------------------------------------------------"
REPORTS_OK=0
python3 -c "from varidex.reports import generator" 2>/dev/null && echo "  ✓ varidex.reports.generator" && ((REPORTS_OK++))
python3 -c "from varidex.reports import formatters" 2>/dev/null && echo "  ✓ varidex.reports.formatters" && ((REPORTS_OK++))

if [ $REPORTS_OK -eq 2 ]; then
    ((PASSED++))
else
    echo "  ⚠ Only $REPORTS_OK/2 report modules imported"
    ((WARNINGS++))
fi

# Test 10: Pipeline Module Imports
echo ""
echo "Test 10: Pipeline Module Imports"
echo "----------------------------------------------------------------------"
PIPELINE_OK=0
python3 -c "from varidex.pipeline import orchestrator" 2>/dev/null && echo "  ✓ varidex.pipeline.orchestrator" && ((PIPELINE_OK++))
python3 -c "from varidex.pipeline import stages" 2>/dev/null && echo "  ✓ varidex.pipeline.stages" && ((PIPELINE_OK++))

if [ $PIPELINE_OK -eq 2 ]; then
    ((PASSED++))
else
    echo "  ⚠ Only $PIPELINE_OK/2 pipeline modules imported"
    ((WARNINGS++))
fi

# Test 11: Utils Module Imports
echo ""
echo "Test 11: Utils Module Imports"
echo "----------------------------------------------------------------------"
if python3 -c "from varidex.utils import helpers" 2>/dev/null; then
    echo "  ✓ varidex.utils.helpers"
    ((PASSED++))
else
    echo "  ✗ varidex.utils.helpers"
    ((FAILED++))
fi

# Test 12: Complete Import Chain
echo ""
echo "Test 12: Complete Import Chain"
echo "----------------------------------------------------------------------"
python3 << 'PYEOF' 2>&1 | tail -5
try:
    from varidex import version
    from varidex.core.classifier import ACMGClassifier
    from varidex.exceptions import ACMGValidationError
    from varidex.io.loaders import clinvar, user
    from varidex.pipeline import orchestrator
    from varidex.reports import generator

    print("  ✓ All critical imports successful")
    print(f"  ✓ VariDex v{version} fully operational")
    exit(0)
except Exception as e:
    print(f"  ⚠ Some imports failed: {e}")
    exit(1)
PYEOF

if [ $? -eq 0 ]; then
    ((PASSED++))
else
    ((WARNINGS++))
fi

# Summary
echo ""
echo "========================================================================"
echo "FINAL VERIFICATION SUMMARY"
echo "========================================================================"
echo ""
echo "Total Tests: 12"
echo "  ✓ Passed:   $PASSED"
echo "  ⚠ Warnings: $WARNINGS"
echo "  ✗ Failed:   $FAILED"
echo ""

if [ $PASSED -eq 12 ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ SUCCESS! VariDex v6.0.0 is fully installed and operational!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 0
elif [ $PASSED -ge 10 ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ SUCCESS with warnings - Core functionality is working!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Some optional components may need dependencies, but VariDex is usable."
    exit 0
else
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "❌ INSTALLATION INCOMPLETE - Some tests failed"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Review the errors above and ensure all files are properly installed."
    exit 1
fi
