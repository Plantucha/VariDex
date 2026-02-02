# MyPy Type Checking Setup Guide

## Overview

Mypy is a static type checker for Python that helps catch type-related bugs before runtime[web:19][web:23]. VariDex uses mypy to improve code quality and maintainability.

## Current Configuration

Your mypy configuration is in `pyproject.toml`[cite:18]:

```toml
[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false  # Currently lenient
disallow_incomplete_defs = false  # Currently lenient
check_untyped_defs = true
disallow_untyped_decorators = false
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true

[[tool.mypy.overrides]]
module = "tests.*"
ignore_errors = true  # Tests are excluded
```

## Installation

### Local Development Setup

```bash
# Install mypy in your development environment
pip install mypy

# Or install with VariDex dev dependencies
pip install -e .[dev]
```

### IDE Integration

**VS Code:**
1. Install the "Mypy Type Checker" extension
2. Add to `.vscode/settings.json`:
```json
{
    "mypy-type-checker.args": [
        "--config-file=pyproject.toml"
    ],
    "python.linting.mypyEnabled": true
}
```

**PyCharm:**
1. Go to Settings → Tools → External Tools
2. Add mypy as external tool
3. Enable type checking in Settings → Editor → Inspections

## Running MyPy

### Command Line

```bash
# Check entire varidex package
mypy varidex/

# Check specific module
mypy varidex/acmg/classifier.py

# Check with ignore-missing-imports (current CI setting)
mypy varidex/ --ignore-missing-imports

# Verbose output for debugging
mypy varidex/ --show-error-codes --show-error-context
```

### CI/CD Integration

Mypy runs automatically in GitHub Actions but is **non-blocking**[cite:16]:

```yaml
- name: Type check with mypy (non-blocking)
  run: |
    mypy varidex/ --ignore-missing-imports
  continue-on-error: true
```

This allows development to continue while gradually improving type coverage.

## Gradual Type Hinting Strategy

### Phase 1: Core Data Models (Current Phase)

**Priority modules to type:**
1. `varidex/core/models.py` - Core data structures
2. `varidex/core/config.py` - Configuration classes
3. `varidex/acmg/classifier.py` - ACMG classification logic

**Example: Adding type hints to a function**

```python
# Before
def classify_variant(variant, evidence):
    result = {}
    # ... logic ...
    return result

# After
from typing import Dict, Any
import pandas as pd

def classify_variant(
    variant: pd.Series,
    evidence: Dict[str, Any]
) -> Dict[str, str]:
    result: Dict[str, str] = {}
    # ... logic ...
    return result
```

### Phase 2: Public APIs

**Focus on:**
- Pipeline orchestrator functions
- Annotator interfaces
- Report generator methods

### Phase 3: Strict Mode (Future)

Once Phase 1 and 2 are complete, enable strict type checking:

```toml
[tool.mypy]
disallow_untyped_defs = true
disallow_incomplete_defs = true
```

## Common Type Hints for Genomics Code

### Variant Data

```python
from typing import Dict, List, Optional, Union
import pandas as pd
import numpy as np

# Variant record
VariantRecord = Dict[str, Union[str, int, float]]

# DataFrame with variants
def process_variants(df: pd.DataFrame) -> pd.DataFrame:
    """Process variant DataFrame."""
    pass

# Optional genomic coordinate
def get_position(chrom: str, pos: Optional[int] = None) -> int:
    """Get genomic position."""
    pass
```

### ACMG Evidence

```python
from typing import Dict, Set, Literal

# Evidence codes
EvidenceCode = Literal[
    "PVS1", "PS1", "PS2", "PS3", "PS4",
    "PM1", "PM2", "PM3", "PM4", "PM5", "PM6",
    "PP1", "PP2", "PP3", "PP4", "PP5",
    "BA1", "BS1", "BS2", "BS3", "BS4",
    "BP1", "BP2", "BP3", "BP4", "BP5", "BP6", "BP7"
]

# Evidence dictionary
Evidence = Dict[EvidenceCode, bool]

def apply_evidence(evidence: Evidence) -> str:
    """Apply ACMG evidence codes."""
    pass
```

### ClinVar/dbNSFP Data

```python
from typing import TypedDict, Optional

class ClinVarRecord(TypedDict):
    """ClinVar variant record."""
    variant_id: str
    clinical_significance: str
    review_status: str
    chromosome: str
    position: int
    ref_allele: str
    alt_allele: str

class GnomADFrequency(TypedDict, total=False):
    """gnomAD allele frequency data."""
    af: Optional[float]
    af_popmax: Optional[float]
    ac: Optional[int]
    an: Optional[int]
```

## Handling Third-Party Libraries

### Install Type Stubs

Many libraries have separate type stub packages:

```bash
# Pandas type stubs (already in requirements-test.txt)
pip install pandas-stubs

# Requests type stubs
pip install types-requests

# Check for available stubs
mypy --install-types
```

### Create Custom Stubs

For libraries without stubs, create a stub file:

```python
# stubs/somelib.pyi
from typing import Any

def some_function(x: Any) -> Any: ...
```

Then configure mypy:
```toml
[tool.mypy]
mypy_path = "stubs"
```

### Use `# type: ignore`

For one-off cases:

```python
import some_untyped_library  # type: ignore

result = some_untyped_library.function()  # type: ignore[attr-defined]
```

## Common MyPy Errors and Fixes

### Error: `Incompatible return value type`

```python
# Problem
def get_count() -> int:
    return None  # Error!

# Fix
from typing import Optional

def get_count() -> Optional[int]:
    return None  # OK
```

### Error: `Argument has incompatible type`

```python
# Problem
def process(x: str) -> None:
    pass

process(123)  # Error!

# Fix
process(str(123))  # OK
```

### Error: `Missing type parameters`

```python
# Problem
from typing import Dict

def get_data() -> Dict:  # Error!
    return {}

# Fix
def get_data() -> Dict[str, Any]:  # OK
    return {}
```

### Error: `Module has no attribute`

```python
# For pandas DataFrame operations
import pandas as pd

df: pd.DataFrame = pd.DataFrame()
df['new_col'] = df['old_col'].str.upper()  # May show error

# Fix: Use assert or ignore
assert isinstance(df['old_col'], pd.Series)
df['new_col'] = df['old_col'].str.upper()  # OK
```

## Best Practices

### 1. Start with Function Signatures

Focus on public API functions first:

```python
# Priority 1: Public functions
def classify_variant(variant: pd.Series) -> Dict[str, str]:
    pass

# Priority 2: Internal functions
def _helper(x: str) -> str:
    pass
```

### 2. Use Type Aliases

Make complex types readable:

```python
from typing import Dict, List, Tuple

# Instead of this
def process(
    data: Dict[str, List[Tuple[str, int, float]]]
) -> Dict[str, List[Tuple[str, int, float]]]:
    pass

# Use this
VariantData = Dict[str, List[Tuple[str, int, float]]]

def process(data: VariantData) -> VariantData:
    pass
```

### 3. Document Complex Types

```python
from typing import TypedDict

class PipelineConfig(TypedDict):
    """Configuration for variant analysis pipeline.
    
    Attributes:
        input_file: Path to input VCF/23andMe file
        output_dir: Directory for output files
        reference_build: Genome build (GRCh37 or GRCh38)
        enable_gnomad: Whether to fetch gnomAD frequencies
    """
    input_file: str
    output_dir: str
    reference_build: str
    enable_gnomad: bool
```

### 4. Incremental Adoption

Add `# mypy: ignore-errors` at the top of files you're not ready to type:

```python
# mypy: ignore-errors
"""Module with legacy code - types coming soon."""

def legacy_function(x, y):
    return x + y
```

## Monitoring Progress

### Generate Coverage Report

```bash
# HTML coverage report
mypy varidex/ --html-report ./mypy-report

# Text summary
mypy varidex/ --txt-report ./mypy-report

# Count typed functions
mypy --linecoverage-report ./mypy-report varidex/
```

### Set Coverage Goals

Track improvement over time:

```bash
# Get current stats
mypy varidex/ --show-error-codes | wc -l

# Goal: Reduce errors by 10% each sprint
```

## CI/CD Enforcement (Future)

Once type coverage reaches 80%+, enable blocking mode:

```yaml
# .github/workflows/test.yml
- name: Type check with mypy (ENFORCED)
  run: |
    mypy varidex/
  continue-on-error: false  # Fail CI on errors
```

## Resources

- [MyPy Documentation](https://mypy.readthedocs.io/)[web:19]
- [Type Hints Cheat Sheet](https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html)[web:22]
- [Python Type Hints Guide](https://betterstack.com/community/guides/scaling-python/python-type-hints/)[web:23]
- [Typing Module Docs](https://docs.python.org/3/library/typing.html)

## Support

For questions or issues with type checking:
1. Check this guide first
2. Review mypy documentation[web:19]
3. Ask in project discussions
4. File an issue with `[mypy]` prefix

---

**Version:** 7.0.3-dev  
**Last Updated:** February 2026
