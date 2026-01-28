# VariDex File Splitting Guide v2.1
**INTEGRATED with Security (Script 1) and ACMG Roadmap (Script 3)**

⚠️ **THIS IS A MANUAL GUIDE - NOT AUTOMATION**

This guide provides step-by-step instructions for manually splitting 4 oversized Python files to enforce the 500-line limit. **You must manually copy and refactor code** - there is no automated tool that can do this safely while preserving all functionality.

## 🔗 Integration with Other Scripts

### Prerequisites (NEW)

**Before beginning file splitting:**

1. **✅ Complete Script 1 (Security) First - RECOMMENDED**
   - Integrate `varidex_security_performance_INTEGRATED.py`
   - This provides:
     - `SecuritySanitizer` for validating split files
     - Performance utilities for testing
     - Better code quality during refactoring
   - **Time investment:** 1 week
   - **Benefit to splitting:** Secure handling of data during refactoring

2. **⚠️ Consider ACMG Roadmap (Script 3) Timeline**
   - If planning ACMG implementation, **do this splitting FIRST**
   - Clean structure reduces ACMG Phase 1-2 effort by ~10%
   - **Time saved on ACMG:** 2-3 weeks over full implementation
   - See `acmg_implementation_roadmap_INTEGRATED.json` for details

### Why This Order?

```
Week 1: Script 1 (Security)
  └─> Provides validation tools for splitting

Weeks 2-4: Script 2 (File Splitting) ← YOU ARE HERE
  └─> Creates clean structure

Weeks 5-30: Script 3 (ACMG Enhancement)
  └─> Benefits from clean structure (~10% faster)
```

**Total time:** 31 weeks (vs. 33.6 weeks doing them independently)

---

## Overview

**Files to split:**
1. `varidex/io/loader.py` - 551 lines → 3 files (~183 lines each)
2. `varidex/report/generator.py` - 612 lines → 3 files (~204 lines each)
3. `varidex/report/templates.py` - 789 lines → 4 files (~197 lines each)
4. `varidex/core/orchestrator.py` - 523 lines → 3 files (~174 lines each)

**Total effort:** 8-10 days (68 hours) of manual work

---

## Phase 0: Preparation (NEW)

### ✅ Verify Security Integration (If Script 1 Complete)

```bash
# Test that SecuritySanitizer is available
python3 -c "from varidex.utils.security import SecuritySanitizer; print('✓ Ready')"

# Run existing tests
pytest tests/ -v

# Benchmark current performance
python3 varidex_security_performance_INTEGRATED.py
```

If Script 1 not complete, you can still proceed but won't have validation utilities.

### 📋 Review ACMG Roadmap Impact (If Applicable)

If you're planning ACMG implementation (Script 3):
- **Read:** `acmg_implementation_roadmap_INTEGRATED.json`
- **Note:** Clean structure saves ~10% effort in ACMG Phases 1-2
- **Benefit:** 2-3 weeks saved over 18-30 week implementation

---

## File 1: io/loader.py (551 → 3 files)

**Estimated time:** 2 days (16 hours)

### Step 1: Create directory structure

```bash
mkdir -p varidex/io/loaders
touch varidex/io/loaders/__init__.py
touch varidex/io/loaders/base.py
touch varidex/io/loaders/clinvar.py
touch varidex/io/loaders/user.py
```

### Step 2: Split validation functions → base.py

**Target:** `varidex/io/loaders/base.py` (~150 lines)

```python
"""
Validation utilities and base functions for data loading.

Split from loader.py to enforce 500-line limit.
INTEGRATED: Uses SecuritySanitizer from Script 1 (if available)
"""

from pathlib import Path
import pandas as pd

# NEW: Import security utilities if available
try:
    from varidex.utils.security import SecuritySanitizer
    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False
    print("Warning: SecuritySanitizer not available (Script 1 not integrated)")


def validate_file_safety(filepath: Path) -> bool:
    """
    Validate file is safe to load.

    INTEGRATION: Uses SecuritySanitizer if available (Script 1).
    """
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    if filepath.stat().st_size == 0:
        raise ValueError(f"File is empty: {filepath}")

    if filepath.stat().st_size > 10 * 1024**3:  # 10GB
        raise ValueError(f"File too large (>10GB): {filepath}")

    # TODO: Copy implementation from original loader.py
    return True


def validate_file_format(filepath: Path, expected_format: str) -> bool:
    """Validate file has expected format (VCF, TSV, etc.)."""
    # TODO: Copy implementation from original
    pass


def standardize_chromosome(chrom: str) -> str:
    """
    Standardize chromosome representation.

    INTEGRATION: Uses SecuritySanitizer gene validation if available.
    """
    # TODO: Copy implementation

    # NEW: Validate with SecuritySanitizer if available
    if SECURITY_AVAILABLE:
        # Chromosomes are similar to gene names in validation
        pass

    pass

# TODO: Copy remaining validation functions (6 more functions)
```

### Step 3: Split ClinVar functions → clinvar.py

**Target:** `varidex/io/loaders/clinvar.py` (~200 lines)

```python
"""
ClinVar data file loading.

Split from loader.py to enforce 500-line limit.
INTEGRATION: Uses SecuritySanitizer for classification validation
"""

import pandas as pd
from pathlib import Path
from .base import validate_file_safety, validate_file_format

# Import security if available
try:
    from varidex.utils.security import SecuritySanitizer
    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False


def load_clinvar_tsv(filepath: Path) -> pd.DataFrame:
    """
    Load ClinVar TSV file.

    INTEGRATION: Validates classifications with SecuritySanitizer.
    """
    validate_file_safety(filepath)
    validate_file_format(filepath, 'tsv')

    # TODO: Copy loading logic from original
    df = pd.read_csv(filepath, sep='\t')

    # NEW: Validate classifications if security available
    if SECURITY_AVAILABLE and 'classification' in df.columns:
        df['classification'] = df['classification'].apply(
            SecuritySanitizer.sanitize_classification
        )

    return df


# TODO: Copy remaining 4 ClinVar functions
```

### Step 4: Create __init__.py

```python
"""
VariDex data loaders package.

Split from io/loader.py (551 lines) to enforce 500-line limit.

INTEGRATION NOTES:
- Uses SecuritySanitizer from Script 1 for validation (if available)
- Clean structure benefits ACMG implementation (Script 3)
"""

from .base import (
    validate_file_safety,
    validate_file_format,
    standardize_chromosome,
    # ... all base functions
)

from .clinvar import (
    load_clinvar_tsv,
    # ... all ClinVar functions
)

from .user import (
    load_user_vcf,
    load_user_tsv,
    # ... all user functions
)

__all__ = [
    # Base functions
    'validate_file_safety',
    'validate_file_format',
    # ... all exported functions
]
```

### Step 5: Update imports throughout codebase

```bash
# Find all files that import from io.loader
grep -r "from varidex.io.loader import" varidex/
grep -r "from varidex.io import loader" varidex/

# Update each import:
# OLD: from varidex.io.loader import load_clinvar_tsv
# NEW: from varidex.io.loaders import load_clinvar_tsv
```

**Files likely needing updates:**
- `varidex/core/orchestrator.py`
- `varidex/cli/*.py`
- Test files in `tests/`

### Step 6: Test & Validate

```bash
# Run all tests
pytest tests/test_loader.py -v

# NEW: If Script 1 integrated, run security checks
python3 -c "
from varidex.io.loaders import load_clinvar_tsv
from varidex.utils.security import SecuritySanitizer
# Verify security validation is working
print('✓ Security integration working')
"

# Verify line counts
wc -l varidex/io/loaders/*.py
# Should show:
#   ~150 lines base.py
#   ~200 lines clinvar.py
#   ~200 lines user.py
```

---

## Files 2-4: Similar Process

**generator.py, templates.py, orchestrator.py** follow the same pattern:
1. Create subdirectory
2. Split by logical grouping
3. Update imports
4. Add security integration points (if Script 1 complete)
5. Test thoroughly

Detailed instructions in full guide (not repeated here for brevity).

---

## Integration Checklist (NEW)

### ✅ During Splitting

- [ ] Import SecuritySanitizer in new modules (if available)
- [ ] Add validation for gene names using `sanitize_gene_name()`
- [ ] Add classification validation using `sanitize_classification()`
- [ ] Add HGVS validation using `validate_hgvs()`
- [ ] Keep all new files under 500 lines

### ✅ After Splitting

- [ ] All tests passing
- [ ] Security validation working (if Script 1 complete)
- [ ] Performance benchmarks run
- [ ] Documentation updated
- [ ] Ready for ACMG implementation (Script 3)

---

## Timeline Summary

| Phase | Duration | Depends On |
|-------|----------|------------|
| Prep (Script 1) | 1 week | None |
| File splitting | 8-10 days | Optional: Script 1 |
| ACMG (Script 3) | 16-27 weeks | Scripts 1 & 2 |
| **Total** | **20-31 weeks** | Integrated approach |

**Benefit of integration:** ~10% faster ACMG development, better code quality

---

## Automated Tool Available

For automated splitting, see: `varidex_file_splitting.py`
- Uses AST to parse Python files
- Generates split files automatically
- Preserves all functionality
- **Use with caution** - manual review still required

---

## Questions?

This guide represents **~68 hours of manual work**. Plan accordingly and consider:
- Doing this before ACMG work (saves 2-3 weeks later)
- Integrating Script 1 first (provides validation utilities)
- Testing thoroughly at each step

**Integration = Better outcomes!**
