#!/bin/bash
########################################################################
# cleanup_junk.sh - Remove temporary fix and diagnostic files
########################################################################

echo "========================================================================"
echo "VariDex Cleanup - Removing Temporary Files"
echo "========================================================================"
echo ""

# List of files to remove
JUNK_FILES=(
    # Bug fix scripts (temporary)
    "apply_bugfixes.sh"
    "apply_engine_fix.sh"
    "apply_fixes.py"
    "fix_bugs.py"
    "fix_permissions.sh"
    "quick_fix_lof.sh"

    # Individual fix scripts (no longer needed)
    "fix1_clinvar.py"
    "fix2_config.py"
    "fix3_coord_key.py"
    "fix4_user_loader.py"
    "fix5_user_filepath.py"
    "fix6_user_complete.py"
    "fix7_matching.py"
    "fix8_matching_clean.py"
    "fix9_placement.py"
    "fix10_clinvar_rsid.py"
    "fix11_try_block.py"
    "fix12_proper_insert.py"
    "fix13_simple_rsid.py"

    # Diagnostic scripts (temporary)
    "check_info_field.py"
    "check_rsids.py"
    "diagnose_columns.py"
    "diagnose_matching.py"

    # Old/backup files
    "fixed_engine.py"
    "clinvar_PERFECT.py"
    "cleanup_precise.sh"

    # Old pipeline log
    "pipeline.log"
)

# Count files
total=0
removed=0

echo "Files to remove:"
for file in "${JUNK_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file"
        total=$((total + 1))
    fi
done
echo ""

if [ $total -eq 0 ]; then
    echo "✓ No junk files found - directory is clean!"
    exit 0
fi

echo "Found $total temporary files"
echo ""
read -p "Remove these files? (yes/no): " response

if [ "$response" != "yes" ]; then
    echo "Cleanup cancelled"
    exit 0
fi

echo ""
echo "Removing files..."

for file in "${JUNK_FILES[@]}"; do
    if [ -f "$file" ]; then
        rm "$file"
        echo "  Removed: $file"
        removed=$((removed + 1))
    fi
done

echo ""
echo "========================================================================"
echo "✅ Cleanup Complete"
echo "========================================================================"
echo ""
echo "Removed: $removed files"
echo ""
echo "Remaining important files:"
echo "  ✓ varidex/ - Main package"
echo "  ✓ data/ - ClinVar and user genome data"
echo "  ✓ test_output/ - Test results"
echo "  ✓ test_real_data.sh - Main test script"
echo "  ✓ test_classification.py - Classification test"
echo "  ✓ test_installation.sh - Installation test"
echo "  ✓ requirements.txt - Dependencies"
echo "  ✓ README.md - Documentation"
echo "  ✓ LICENSE - License file"
echo ""
echo "========================================================================"
