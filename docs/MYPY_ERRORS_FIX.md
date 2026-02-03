# MyPy Type Errors - Fix Guide

## Summary

Local mypy scan found **36 type errors in 12 files**. This guide provides prioritized fixes.

## Quick Commands

```bash
# Pull latest changes (includes .secretsignore)
git pull origin main

# Clean up the corrupted baseline
rm .secrets.baseline

# Run detect-secrets with exclusions
detect-secrets scan --exclude-files '(data/|.*\.vcf$|.*rawM.*|results/)' > .secrets.baseline

# Check mypy errors by file
mypy varidex/core/config.py --ignore-missing-imports
```

## Priority 1: Critical Errors (Block functionality)

### 1. Missing Import - `io/matching.py` (Lines 271, 274, 307, 309)

**Error:** `Name "MatchingError" is not defined`

**Fix:** Add import at top of file

```python
# At the top of varidex/io/matching.py
from varidex.exceptions import MatchingError
```

### 2. Missing Attribute - `pipeline_main_integrated.py:16`

**Error:** `Module "varidex.pipeline.acmg_classifier_stage" has no attribute "ACMGClassifierStage"`

**Fix:** Update import

```python
# Before
from varidex.pipeline.acmg_classifier_stage import ACMGClassifierStage

# After - check actual module structure
from varidex.pipeline.stages import ACMGClassifierStage
# OR if it's in a different module:
from varidex.core.classifier import ACMGClassifierStage
```

### 3. Missing Attribute - `core/classifier/engine_v8.py` (Lines 143, 145)

**Error:** `"VariantData" has no attribute "match_data"`

**Fix:** Add `match_data` field to VariantData class or use correct attribute name

```python
# In varidex/core/models.py - VariantData class
@dataclass
class VariantData:
    # ... existing fields ...
    match_data: Optional[Dict[str, Any]] = None  # Add this field
```

### 4. Duplicate Definitions - `core/classifier/__init__.py` (Lines 99, 121)

**Error:** `Name "ACMGClassifierV7/V8" already defined`

**Fix:** Remove duplicate imports

```python
# Check varidex/core/classifier/__init__.py
# Keep only ONE import for each:
from .engine_v7 import ACMGClassifierV7  # Remove duplicate
from .engine_v8 import ACMGClassifierV8  # Remove duplicate

# Make sure __all__ also lists them only once
__all__ = [
    "ACMGClassifierV7",
    "ACMGClassifierV8",
    # ... other exports
]
```

## Priority 2: Type Annotation Issues (Easy fixes)

### 5. Missing Type Annotations

#### `core/config.py:279`

```python
# Before
FUNCTIONAL_DOMAINS = {
    "DNA_binding": [...],
    "Kinase": [...],
}

# After
from typing import Dict, List

FUNCTIONAL_DOMAINS: Dict[str, List[str]] = {
    "DNA_binding": [...],
    "Kinase": [...],
}
```

#### `io/validators_parallel.py:158`

```python
# Before
all_warnings = {}

# After
from typing import Dict, List

all_warnings: Dict[str, List[str]] = {}
```

#### `io/matching.py:417`

```python
# Before
result = match_variant(...)

# After
from typing import Dict, Any

result: Dict[str, Any] = match_variant(...)
```

### 6. Wrong Type Used - `core/classifier/evidence_assignment.py:155`

**Error:** `Function "builtins.any" is not valid as a type`

```python
# Before
def process(data: any) -> None:  # WRONG - lowercase 'any'
    pass

# After
from typing import Any

def process(data: Any) -> None:  # CORRECT - uppercase 'Any'
    pass
```

## Priority 3: Optional/None Handling

### 7. Optional Match Object - `io/loaders/user.py:53`

**Error:** `Item "None" of "Optional[Match[str]]" has no attribute "group"`

```python
# Before
match = re.search(pattern, line)
value = match.group(1)  # May be None!

# After
import re
from typing import Optional

match: Optional[re.Match[str]] = re.search(pattern, line)
if match:
    value = match.group(1)
else:
    value = None  # or raise error
```

### 8. Optional Path - `gnomad_stage.py:60`

**Error:** `Argument has incompatible type "Optional[Path]"; expected "Path"`

```python
# Before
def process(cache_dir: Optional[Path]) -> None:
    annotate_with_gnomad(data, cache_dir)  # cache_dir may be None

# After
from pathlib import Path

def process(cache_dir: Optional[Path]) -> None:
    if cache_dir is not None:
        annotate_with_gnomad(data, cache_dir)
    else:
        # Handle None case
        pass
```

### 9. Optional Set - `io/loaders/clinvar_xml.py:61`

```python
# Before
def load_clinvar_xml_indexed(
    xml_path: Path,
    gene_filter: Optional[set[str]]
) -> pd.DataFrame:
    # Function expects non-None set
    pass

# After - Option 1: Provide default
def load_clinvar_xml_indexed(
    xml_path: Path,
    gene_filter: Optional[set[str]] = None
) -> pd.DataFrame:
    if gene_filter is None:
        gene_filter = set()  # Empty set as default
    # Now gene_filter is always a set
    pass

# After - Option 2: Check at call site
if gene_filter is not None:
    result = load_clinvar_xml_indexed(xml_path, gene_filter)
```

## Priority 4: Type Compatibility Issues

### 10. Return Type Mismatch - `core/config.py` (Lines 256, 261)

```python
# Before
def get_int_value(self) -> int:
    return self.config.get("key", 0)  # Returns 'object'

def get_str_value(self) -> str:
    return self.config.get("key", "")  # Returns 'object'

# After
def get_int_value(self) -> int:
    value = self.config.get("key", 0)
    return int(value)  # Explicit cast

def get_str_value(self) -> str:
    value = self.config.get("key", "")
    return str(value)  # Explicit cast
```

### 11. String/Path Conversion - `pipeline_main_integrated.py` (Lines 145, 149)

```python
# Before
clinvar_path = "/path/to/file.vcf"  # str
load_clinvar_vcf(clinvar_path)  # Expects Path

# After
from pathlib import Path

clinvar_path = Path("/path/to/file.vcf")
load_clinvar_vcf(clinvar_path)  # Now correct type
```

### 12. Type Assignments - `io/matching.py` (Lines 415, 426, 431, 436)

```python
# Before (Line 415)
result: str = calculate_position()  # Returns int

# After
result: int = calculate_position()  # Match actual return type

# Before (Lines 426, 431)
gnomad_data: dict[Any, Any] = get_optional_data()  # Returns Optional

# After
from typing import Optional, Dict, Any

gnomad_data: Optional[Dict[str, Any]] = get_optional_data()
if gnomad_data is not None:
    # Use gnomad_data safely
    pass
```

### 13. Position Type - `io/matching.py` (Lines 427, 432)

```python
# Before
pos_str: str = "12345"
freq = self._get_gnomad_freq(chrom, pos_str, ref)  # Expects int

# After
pos_str: str = "12345"
pos: int = int(pos_str)
freq = self._get_gnomad_freq(chrom, pos, ref)  # Now correct
```

## Priority 5: Complex Type Issues

### 14. VariantData Dict Unpacking - `core/models.py:786`

**Error:** Multiple incompatible types when unpacking dict

```python
# Before
variant_dict: Dict[str, Union[str, int, None]] = {...}
variant = VariantData(**variant_dict)  # Type mismatch

# After - Option 1: Use TypedDict
from typing import TypedDict, Optional

class VariantDataDict(TypedDict, total=False):
    chromosome: str
    position: int
    ref_allele: str
    alt_allele: str
    # ... all other fields with correct types

variant_dict: VariantDataDict = {...}
variant = VariantData(**variant_dict)  # Now type-safe

# After - Option 2: Explicit construction
variant = VariantData(
    chromosome=str(variant_dict["chromosome"]),
    position=int(variant_dict["position"]),
    ref_allele=str(variant_dict["ref_allele"]),
    alt_allele=str(variant_dict["alt_allele"]),
    # ... explicit field assignment
)

# After - Option 3: Add type: ignore for now
variant = VariantData(**variant_dict)  # type: ignore[arg-type]
```

### 15. GzipFile Type - `io/loaders/clinvar_xml.py:108`

```python
# Before
import gzip

f: GzipFile = gzip.open(path, 'rb')  # Returns BufferedReader

# After
from typing import IO, Any
import gzip

f: IO[bytes] = gzip.open(path, 'rb')  # More flexible type
# Or just let mypy infer:
f = gzip.open(path, 'rb')  # Type inference works fine
```

### 16. Module Assignment - `__init__.py:40`

```python
# Before
import sys
from types import ModuleType

some_module: ModuleType = None  # Assigning None to Module

# After
from typing import Optional
from types import ModuleType

some_module: Optional[ModuleType] = None  # Correct type
```

## Fix Strategy

### Phase 1: Quick Wins (30 minutes)

1. Fix missing imports (MatchingError)
2. Add type annotations for empty dicts/lists
3. Fix `any` → `Any` typo
4. Remove duplicate imports

### Phase 2: None Handling (1 hour)

5. Add None checks for Optional types
6. Provide default values
7. Update function signatures

### Phase 3: Type Conversions (1 hour)

8. Fix str/Path conversions
9. Fix str/int conversions
10. Add explicit casts

### Phase 4: Complex Types (2 hours)

11. Create TypedDicts for variant data
12. Fix VariantData unpacking
13. Review and test

## Testing After Fixes

```bash
# Check specific file after fix
mypy varidex/io/matching.py --ignore-missing-imports

# Run full check
mypy varidex/ --ignore-missing-imports

# Generate progress report
mypy varidex/ --html-report ./mypy-report

# Count remaining errors
mypy varidex/ 2>&1 | grep "Found.*errors" 
```

## Gradual Improvement

Don't fix all 36 errors at once! Work incrementally:

**Week 1:** Fix Priority 1 (critical errors) - 10 errors  
**Week 2:** Fix Priority 2 (annotations) - 6 errors  
**Week 3:** Fix Priority 3 (Optional handling) - 8 errors  
**Week 4:** Fix Priority 4 (type compatibility) - 10 errors  
**Week 5:** Fix Priority 5 (complex types) - 2 errors  

## Commit Strategy

```bash
# Fix one category at a time
git checkout -b fix/mypy-priority-1
# Make fixes...
git commit -m "fix(types): Add missing MatchingError import and fix duplicates"
git push origin fix/mypy-priority-1
# Create PR, review, merge

# Then move to next priority
git checkout -b fix/mypy-priority-2
# ...
```

## When to Use `# type: ignore`

For complex issues that would require major refactoring:

```python
# Acceptable temporary ignore
variant = VariantData(**variant_dict)  # type: ignore[arg-type]

# Add TODO comment
# TODO(types): Create VariantDataDict TypedDict to fix this properly
variant = VariantData(**variant_dict)  # type: ignore[arg-type]
```

## Resources

- [MyPy Common Issues](https://mypy.readthedocs.io/en/stable/common_issues.html)
- [Type Variance Guide](https://mypy.readthedocs.io/en/stable/common_issues.html#variance)
- [VariDex MyPy Setup Guide](./MYPY_SETUP.md)

---

**Version:** 7.0.3-dev  
**Last Updated:** February 2026  
**Total Errors:** 36 → Target: 0
