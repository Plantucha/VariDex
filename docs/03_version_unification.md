# VariDex v6.0.0 Version Unification

**Document Version:** 1.0  
**Last Updated:** 2026-01-19  

Standardize all modules to single version (6.0.0).

---

## Current Version Chaos

### 5 Different Versions Across 13 Files

```
v5.2:   file_6a_generator.txt, file_6B_templates.txt
v6.0.0: file_7a_main.txt, file_1_config.txt
v6.0.1: file_2_models.txt, file_7b_helpers.txt
v6.0.4: file_5_loader.txt
v18:    file_0_downloader.txt
```

### Problems

**Import Conflicts:**
```python
# File A imports v6.0.0
from varidex.core.models import VariantData  # v6.0.1

# File B expects v5.2
from varidex.reports.generator import create_report  # v5.2

# CONFLICT: Incompatible interfaces!
```

---

## Target: Single Version File

### New Structure

```python
# varidex/version.py (SINGLE SOURCE OF TRUTH)

__version__ = "6.0.0"
__acmg_version__ = "2015"
__clinvar_schema__ = "2024-01"

VERSION_INFO = {
    "major": 6,
    "minor": 0,
    "patch": 0,
    "release": "stable"
}

COMPONENT_VERSIONS = {
    "classifier": "6.0.0",
    "loader": "6.0.0",
    "generator": "6.0.0",
    "pipeline": "6.0.0",
    "downloader": "6.0.0"
}
```

### Usage in All Files

```python
# Every module imports from central version:
from varidex.version import __version__

def my_function():
    logger.info(f"Running VariDex v{__version__}")
```

---

## Migration Steps

### Step 1: Delete Inline Versions

**Before:**
```python
# file_6a_generator.txt
__version__ = "5.2"  # DELETE THIS

# file_5_loader.txt
VERSION = "6.0.4"  # DELETE THIS
```

**After:**
```python
# All files
from varidex.version import __version__
```

### Step 2: Update Docstrings

**Before:**
```python
"""
ClinVar Loader v6.0.4
"""
```

**After:**
```python
"""
ClinVar Loader

Version controlled by varidex.version module.
"""
```

---

## Files Requiring Updates

| File | Current Version | Action |
|------|----------------|--------|
| file_6a_generator.txt | v5.2 | Update to v6.0.0 |
| file_6B_templates.txt | v5.2 | Update to v6.0.0 |
| file_2_models.txt | v6.0.1 | Merge to v6.0.0 |
| file_5_loader.txt | v6.0.4 | Merge to v6.0.0 |
| file_0_downloader.txt | v18 | Rename to v6.0.0 |
| file_7b_helpers.txt | v6.0.1 | Merge to v6.0.0 |

---

## Verification Tests

```python
# test_version_consistency.py

def test_all_modules_import_central_version():
    """Verify no modules define their own version."""
    for module in find_all_modules():
        source = read_source(module)
        assert '__version__' not in source
        assert 'VERSION =' not in source

def test_central_version_exists():
    from varidex.version import __version__
    assert __version__ == "6.0.0"
```

---

See also:
- `01_overview.md`: Why version unification matters
- `02_file_splits.md`: File restructuring
- `05_testing_deployment.md`: Version verification tests
