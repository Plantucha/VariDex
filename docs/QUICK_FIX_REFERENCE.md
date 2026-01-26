# VariDex Quick Fix Reference Card

## 🚀 One-Command Restoration

```bash
bash scripts/restore_varidex.sh
```

---

## ⚡ Critical 5-Minute Fix

If you only have 5 minutes, run these commands:

```bash
# 1. Fix circular imports (30 seconds)
sed -i 's/^from varidex/# from varidex/' varidex/reports/__init__.py
sed -i 's/^from varidex/# from varidex/' varidex/pipeline/__init__.py

# 2. Remove orphan parentheses (30 seconds)
find varidex -name "*.py" -exec sed -i '/^\s*)$/d' {} \;

# 3. Fix critical indents (1 minute)
sed -i '11s/^    //' varidex/io/matching.py
sed -i '8s/^    //' varidex/pipeline/__main__.py
sed -i '11s/^    //' varidex/io/validators_advanced.py 2>/dev/null || true

# 4. Verify (3 minutes)
python3 -c "from varidex.reports.formatters import generate_csv_report" && echo "✅ Test 1"
python3 -c "from varidex.reports.generator import create_results_dataframe" && echo "✅ Test 2"
python3 -c "from varidex.core.models import VariantData" && echo "✅ Test 3"
python3 -c "from varidex.pipeline.orchestrator import main" && echo "✅ Test 4"
python3 -m varidex.pipeline --help | head -n 3 && echo "✅ Test 5"
```

---

## 🎯 Top 10 Most Critical Fixes

### 1. Circular Imports (⭐⭐⭐⭐⭐)
**Files**: `varidex/reports/__init__.py`, `varidex/pipeline/__init__.py`

```bash
sed -i 's/^from varidex/# from varidex/' varidex/reports/__init__.py
sed -i 's/^from varidex/# from varidex/' varidex/pipeline/__init__.py
```

### 2. Orphan Parentheses (⭐⭐⭐⭐⭐)
**Files**: Any Python file with standalone `)` lines

```bash
find varidex -name "*.py" -exec sed -i '/^\s*)$/d' {} \;
```

### 3. matching.py Line 11 (⭐⭐⭐⭐)
**File**: `varidex/io/matching.py`

```bash
sed -i '11s/^    //' varidex/io/matching.py
```

### 4. __main__.py Line 8 (⭐⭐⭐⭐)
**File**: `varidex/pipeline/__main__.py`

```bash
sed -i '8s/^    //' varidex/pipeline/__main__.py
```

### 5. validators_advanced.py Line 11 (⭐⭐⭐)
**File**: `varidex/io/validators_advanced.py`

```bash
sed -i '11s/^    //' varidex/io/validators_advanced.py
```

### 6-10. Already Fixed (✅)
The following are already operational in current state:
- generator.py (v6.0.1) - All import/syntax fixes applied
- orchestrator.py (v6.0.0) - Full coordination working
- formatters.py - All report functions operational
- stages.py - Stage implementations working
- models.py - Core data structures intact

---

## 🛠️ Emergency Syntax Error Fix

If Python throws `SyntaxError: invalid syntax`:

```bash
# Step 1: Find the problematic file
python3 -m varidex.pipeline --help 2>&1 | grep "File"

# Step 2: Check for common issues in that file
FILE="path/to/problematic/file.py"

# Check orphan parentheses
grep -n '^\s*)$' "$FILE"

# Check extra indents on imports
grep -n '^    from ' "$FILE"

# Check unclosed brackets
python3 -m py_compile "$FILE"

# Step 3: Auto-fix common patterns
sed -i '/^\s*)$/d' "$FILE"          # Remove orphan )
sed -i 's/^    from /from /' "$FILE"  # Fix import indents (be careful!)
```

---

## 📊 Verification Quick Check

### 30-Second Test
```bash
python3 -m varidex.pipeline --help | grep -q "CLINVAR-WGS" && echo "✅ WORKING" || echo "❌ BROKEN"
```

### 2-Minute Full Test
```bash
#!/bin/bash
for test in \
  "from varidex.reports.formatters import generate_csv_report" \
  "from varidex.reports.generator import create_results_dataframe" \
  "from varidex.core.models import VariantData" \
  "from varidex.pipeline.orchestrator import main"
do
  python3 -c "$test" 2>/dev/null && echo "✅" || echo "❌ $test"
done
```

---

## 🔍 Troubleshooting Flowchart

```
Error occurs
    ↓
    Is it ImportError?
        YES → Check circular imports in __init__.py files
              → Run: sed -i 's/^from varidex/# from varidex/' varidex/*/__init__.py
        NO  → Continue
    ↓
    Is it SyntaxError?
        YES → Check for orphan ) or extra indents
              → Run: find varidex -name "*.py" -exec sed -i '/^\s*)$/d' {} \;
        NO  → Continue
    ↓
    Is it FileTypeDetectionError?
        YES → Use --format flag or --force
              → Run: python3 -m varidex.pipeline file1 file2 --format 23andme
        NO  → Continue
    ↓
    Check pipeline.log for detailed error
```

---

## 📝 File Status Quick Reference

| File | Status | Fix Priority | Command |
|------|--------|--------------|----------|
| `generator.py` | ✅ Operational | N/A | Already v6.0.1 |
| `orchestrator.py` | ✅ Operational | N/A | Already v6.0.0 |
| `formatters.py` | ✅ Operational | N/A | Already working |
| `matching.py` | ⚠️ Line 11 indent | ⭐⭐⭐⭐ | `sed -i '11s/^    //' varidex/io/matching.py` |
| `reports/__init__.py` | ⚠️ Circular | ⭐⭐⭐⭐⭐ | `sed -i 's/^from varidex/# /' varidex/reports/__init__.py` |
| `pipeline/__init__.py` | ⚠️ Circular | ⭐⭐⭐⭐⭐ | `sed -i 's/^from varidex/# /' varidex/pipeline/__init__.py` |
| `__main__.py` | ⚠️ Line 8 indent | ⭐⭐⭐⭐ | `sed -i '8s/^    //' varidex/pipeline/__main__.py` |
| `validators_advanced.py` | ⚠️ Line 11 indent | ⭐⭐⭐ | `sed -i '11s/^    //' varidex/io/validators_advanced.py` |

---

## 🚀 Production Pipeline Test

```bash
# Full pipeline test with real data
python3 -m varidex.pipeline \
    data/clinvar_latest.txt \
    data/genome_Full_20160412003749.txt \
    --force \
    --non-interactive

# Expected output structure:
# ======================================================================
# CLINVAR-WGS PIPELINE v6.0.0
# ======================================================================
# [1/7] 📋 FILE ANALYSIS
# [2/7] 📥 LOADING CLINVAR
# [3/7] 📥 LOADING USER DATA
# [4/7] 🔗 HYBRID MATCHING
# [5/7] 🧬 ACMG CLASSIFICATION
# [6/7] 📊 CREATE RESULTS
# [7/7] 📄 GENERATE REPORTS
# ======================================================================
# ✅ PIPELINE COMPLETE
# ======================================================================

# Check results/
ls -lh results/*.{csv,json,html}
```

---

## 💡 Pro Tips

### 1. Always Use Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Keep Backups Before Sed
```bash
# Create backup
cp varidex/io/matching.py varidex/io/matching.py.backup

# Run fix
sed -i '11s/^    //' varidex/io/matching.py

# Verify
python3 -c "from varidex.io.matching import match_variants_hybrid"

# If broken, restore
cp varidex/io/matching.py.backup varidex/io/matching.py
```

### 3. Use Git for Safety
```bash
# Commit before fixes
git add -A
git commit -m "Pre-restoration checkpoint"

# Run restoration
bash scripts/restore_varidex.sh

# If something breaks
git diff  # See what changed
git reset --hard HEAD  # Revert everything
```

### 4. Test Incrementally
Don't run all fixes at once. Test after each phase:

```bash
# Phase 1: Circular imports
sed -i 's/^from varidex/# from varidex/' varidex/reports/__init__.py
python3 -c "from varidex.reports.formatters import generate_csv_report"  # TEST

# Phase 2: Orphan parentheses
find varidex -name "*.py" -exec sed -i '/^\s*)$/d' {} \;
python3 -m varidex.pipeline --help  # TEST

# Phase 3: Indents
sed -i '11s/^    //' varidex/io/matching.py
python3 -c "from varidex.io.matching import match_variants_hybrid"  # TEST
```

---

## 📞 Support Commands

```bash
# Check Python version
python3 --version  # Should be 3.8+

# Check installed packages
pip list | grep -E "pandas|pyyaml|tqdm"

# Check file permissions
ls -la scripts/restore_varidex.sh
chmod +x scripts/restore_varidex.sh  # If needed

# Check disk space
df -h .

# Check git status
git status
git log --oneline -5
```

---

## ✅ Success Checklist

- [ ] All 5 import tests pass
- [ ] `--help` shows "CLINVAR-WGS PIPELINE v6.0.0"
- [ ] No SyntaxError or ImportError
- [ ] Pipeline runs through all 7 stages
- [ ] Reports generated in results/
- [ ] CSV, JSON, HTML files present
- [ ] No orphan ) in any Python files
- [ ] No circular imports in __init__.py files
- [ ] pytest tests/ passes (optional)
- [ ] pipeline.log shows no errors

---

## 🔗 Quick Links

- **Full Guide**: [docs/RESTORATION_GUIDE.md](RESTORATION_GUIDE.md)
- **Restoration Script**: [scripts/restore_varidex.sh](../scripts/restore_varidex.sh)
- **Generator Code**: [varidex/reports/generator.py](../varidex/reports/generator.py)
- **Orchestrator Code**: [varidex/pipeline/orchestrator.py](../varidex/pipeline/orchestrator.py)

---

**Last Updated**: 2026-01-26  
**Quick Fix Version**: 1.0  
**Estimated Time**: 5 minutes for critical fixes, 15 minutes for full restoration
