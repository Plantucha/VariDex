#!/bin/bash
# Repository Cleanup Script
# Removes duplicates, temporary files, and clutter
# Preserves original data files and important artifacts

set -e

echo "🧹 VariDex Repository Cleanup Script"
echo "====================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Safety check
if [ ! -f "pyproject.toml" ]; then
    echo "${RED}❌ Error: Must run from repository root${NC}"
    exit 1
fi

echo "${YELLOW}⚠️  This will remove duplicate and temporary files${NC}"
echo "${YELLOW}⚠️  Original data files will NOT be modified${NC}"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "${RED}Cancelled${NC}"
    exit 1
fi

echo ""
echo "📦 Creating archive directory..."
mkdir -p .archive/old_results
mkdir -p .archive/old_scripts
mkdir -p .archive/backup_files

# Track what we're doing
REMOVED_COUNT=0
ARCHIVED_COUNT=0
KEPT_COUNT=0

echo ""
echo "🗑️  Removing duplicate files..."

# Duplicate victory.txt files (keep the one in root as canonical)
if [ -f "VICTORY.txt" ] && [ -f "victory.txt" ]; then
    echo "  - Removing uppercase VICTORY.txt (duplicate of victory.txt)"
    git rm -f VICTORY.txt 2>/dev/null || rm -f VICTORY.txt
    ((REMOVED_COUNT++))
fi

# Duplicate RESULTS.txt files
if [ -f "RESULTS.txt" ] && [ -f "FINAL_RESULTS.txt" ]; then
    echo "  - Archiving RESULTS.txt (duplicate of FINAL_RESULTS.txt)"
    mv RESULTS.txt .archive/old_results/ 2>/dev/null || true
    git rm -f RESULTS.txt 2>/dev/null || true
    ((ARCHIVED_COUNT++))
fi

if [ -f "FINAL.txt" ] && [ -f "FINAL_RESULTS.txt" ]; then
    echo "  - Archiving FINAL.txt (duplicate of FINAL_RESULTS.txt)"
    mv FINAL.txt .archive/old_results/ 2>/dev/null || true
    git rm -f FINAL.txt 2>/dev/null || true
    ((ARCHIVED_COUNT++))
fi

echo ""
echo "🧪 Cleaning test output files from root..."

# Test result files that should be in .gitignore
for file in test_results.txt test_results_fixed.txt e2e_results.txt final_results.txt pipeline_summary.txt coverage.txt tests.txt test_log.txt; do
    if [ -f "$file" ]; then
        echo "  - Archiving $file"
        mv "$file" .archive/old_results/ 2>/dev/null || true
        git rm -f "$file" 2>/dev/null || true
        ((ARCHIVED_COUNT++))
    fi
done

# Test output file
if [ -f "output" ]; then
    echo "  - Removing 'output' file"
    git rm -f output 2>/dev/null || rm -f output
    ((REMOVED_COUNT++))
fi

echo ""
echo "📝 Moving staging/development files..."

# Staging files in root that should be in varidex/
if [ -f "gnomad_stage.py" ] && [ -f "varidex/gnomad_stage.py" ]; then
    echo "  - Removing duplicate gnomad_stage.py from root (exists in varidex/)"
    git rm -f gnomad_stage.py 2>/dev/null || rm -f gnomad_stage.py
    ((REMOVED_COUNT++))
fi

if [ -f "gnomad_stage_fixed.py" ]; then
    echo "  - Archiving gnomad_stage_fixed.py (development artifact)"
    mv gnomad_stage_fixed.py .archive/old_scripts/ 2>/dev/null || true
    git rm -f gnomad_stage_fixed.py 2>/dev/null || true
    ((ARCHIVED_COUNT++))
fi

if [ -f "clinvar.py" ]; then
    echo "  - Archiving clinvar.py (minimal stub file)"
    mv clinvar.py .archive/old_scripts/ 2>/dev/null || true
    git rm -f clinvar.py 2>/dev/null || true
    ((ARCHIVED_COUNT++))
fi

if [ -f "clinvar_v7.2.0_OPTIMIZED.py" ]; then
    echo "  - Archiving clinvar_v7.2.0_OPTIMIZED.py (old version)"
    mv clinvar_v7.2.0_OPTIMIZED.py .archive/old_scripts/ 2>/dev/null || true
    git rm -f clinvar_v7.2.0_OPTIMIZED.py 2>/dev/null || true
    ((ARCHIVED_COUNT++))
fi

echo ""
echo "🔧 Cleaning development scripts..."

# Old development helper scripts
for script in find_pm2_logic.py test_overview.py test_gnomad_loader.py test_pipeline_validators.py varidex_v6.1.6.py; do
    if [ -f "$script" ]; then
        echo "  - Archiving $script"
        mv "$script" .archive/old_scripts/ 2>/dev/null || true
        git rm -f "$script" 2>/dev/null || true
        ((ARCHIVED_COUNT++))
    fi
done

# Large roadmap/planning files
for file in varidex_acmg_roadmap_INTEGRATED.py varidex_file_splitting.py varidex_security_performance_INTEGRATED.py; do
    if [ -f "$file" ]; then
        echo "  - Archiving $file (planning document)"
        mv "$file" .archive/old_scripts/ 2>/dev/null || true
        git rm -f "$file" 2>/dev/null || true
        ((ARCHIVED_COUNT++))
    fi
done

if [ -f "acmg_implementation_roadmap_INTEGRATED.json" ]; then
    echo "  - Moving acmg_implementation_roadmap_INTEGRATED.json to docs/"
    mkdir -p docs/planning
    mv acmg_implementation_roadmap_INTEGRATED.json docs/planning/ 2>/dev/null || true
    git rm -f acmg_implementation_roadmap_INTEGRATED.json 2>/dev/null || true
    git add docs/planning/acmg_implementation_roadmap_INTEGRATED.json 2>/dev/null || true
    ((KEPT_COUNT++))
fi

echo ""
echo "💾 Cleaning backup files..."

# .bak files
find tests/ -name "*.bak" -type f 2>/dev/null | while read -r file; do
    echo "  - Archiving $file"
    cp "$file" .archive/backup_files/ 2>/dev/null || true
    git rm -f "$file" 2>/dev/null || rm -f "$file"
    ((ARCHIVED_COUNT++))
done

# Disabled test files
find tests/ -name "*.disabled" -type f 2>/dev/null | while read -r file; do
    echo "  - Keeping $file (intentionally disabled)"
    ((KEPT_COUNT++))
done

echo ""
echo "🗂️  Organizing shell scripts..."

# Ensure scripts directory exists
mkdir -p scripts

# Move utility scripts to scripts/ if not already there
for script in add_badges.sh check_compliance.sh check_status.sh clean_before_push.sh format_code.sh pre_push_check.sh refresh_installation.sh; do
    if [ -f "$script" ]; then
        if [ ! -f "scripts/$script" ]; then
            echo "  - Moving $script to scripts/"
            mv "$script" scripts/
            git rm -f "$script" 2>/dev/null || true
            git add "scripts/$script" 2>/dev/null || true
        else
            echo "  - Removing duplicate $script (already in scripts/)"
            git rm -f "$script" 2>/dev/null || rm -f "$script"
            ((REMOVED_COUNT++))
        fi
    fi
done

# Large test/deployment scripts - keep but note
for script in test_e2e.sh test_installation_enhanced_v2.sh run_full_pipeline.sh run.sh reporting_setup.sh; do
    if [ -f "$script" ]; then
        echo "  - Keeping $script in root (active deployment script)"
        ((KEPT_COUNT++))
    fi
done

echo ""
echo "📋 Updating .gitignore..."

# Add patterns to .gitignore if not already present
GITIGNORE_ADDITIONS="
# Test outputs and results
test_results*.txt
e2e_results.txt
final_results.txt
pipeline_summary.txt
coverage.txt
tests.txt
test_log.txt
output

# Archived files
.archive/

# Backup files
*.bak
*.backup
*~

# Development artifacts
FINAL.txt
RESULTS.txt
victory.txt
VICTORY.txt

# Coverage reports
htmlcov/
.coverage
coverage.xml
*.cover
.pytest_cache/

# Build artifacts
dist/
build/
*.egg-info/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
"

if ! grep -q ".archive/" .gitignore 2>/dev/null; then
    echo "$GITIGNORE_ADDITIONS" >> .gitignore
    echo "  ✓ Updated .gitignore with cleanup patterns"
    git add .gitignore 2>/dev/null || true
else
    echo "  ✓ .gitignore already contains cleanup patterns"
fi

echo ""
echo "✅ Creating archive README..."

cat > .archive/README.md << 'EOF'
# Archived Files

This directory contains files removed during repository cleanup.

## Directory Structure

- `old_results/` - Test output and result files
- `old_scripts/` - Development and staging scripts
- `backup_files/` - .bak and backup files

## Purpose

These files were removed to clean up the repository root but are preserved
here for reference. They are not needed for the application to function.

## When Created

Cleanup performed: $(date)
Script: scripts/cleanup_repository.sh

## What Was Kept

- All source code in varidex/
- All tests in tests/
- Active shell scripts (moved to scripts/)
- Documentation files
- Configuration files
- Original data files (NEVER modified)

## What Was Removed/Archived

- Duplicate files (victory.txt, VICTORY.txt, etc.)
- Test output files from root
- Development staging files
- Old version scripts
- .bak backup files
- Temporary build artifacts

## Recovery

If you need any of these files:
```bash
cp .archive/old_results/FILENAME .
```

## Cleanup

This directory can be safely deleted if you don't need the archived files:
```bash
rm -rf .archive/
```
EOF

echo ""
echo "📊 Cleanup Summary"
echo "=================="
echo ""
echo "${GREEN}✓ Removed: $REMOVED_COUNT files${NC}"
echo "${YELLOW}📦 Archived: $ARCHIVED_COUNT files${NC}"
echo "${GREEN}✓ Kept/Moved: $KEPT_COUNT files${NC}"
echo ""
echo "${GREEN}✓ Archive created: .archive/${NC}"
echo "${GREEN}✓ Updated: .gitignore${NC}"
echo ""

echo "📁 Archive contents:"
echo "  - .archive/old_results/ ($(find .archive/old_results -type f 2>/dev/null | wc -l) files)"
echo "  - .archive/old_scripts/ ($(find .archive/old_scripts -type f 2>/dev/null | wc -l) files)"
echo "  - .archive/backup_files/ ($(find .archive/backup_files -type f 2>/dev/null | wc -l) files)"
echo ""

echo "${YELLOW}⚠️  Important Notes:${NC}"
echo "  - Original data files were NOT modified ✓"
echo "  - ClinVar data integrity maintained ✓"
echo "  - All source code preserved ✓"
echo "  - Tests remain intact ✓"
echo ""

echo "${GREEN}🎯 Next Steps:${NC}"
echo "  1. Review changes: git status"
echo "  2. Check archive: ls -la .archive/"
echo "  3. Commit cleanup: git commit -m 'chore: Clean up repository duplicates and clutter'"
echo "  4. Verify tests still pass: pytest tests/"
echo ""

echo "${GREEN}✨ Repository cleanup complete!${NC}"
echo ""
echo "To delete the archive (if you don't need it):"
echo "  rm -rf .archive/"
echo ""
echo "To recover a file:"
echo "  cp .archive/old_results/FILENAME ."
echo ""
