# VariDex Code Standards - BINDING RULES

**Document Version:** 1.0  
**Date:** January 21, 2026  
**Status:** ✅ BINDING - MANDATORY FOR ALL CODE  
**Authority:** Approved migration from [VariDex_500_Line_Limit_Migration_Proposal.md](VariDex_500_Line_Limit_Migration_Proposal.md)

---

## Executive Authority

This document establishes **binding rules** for all VariDex codebase contributions. These standards were approved based on the 500-Line Limit Migration Proposal analysis showing:
- **16% AI efficiency improvement**
- **2.7-4.0x ROI in first year**
- **Surgical precision** (only 4 files require splitting)

All code MUST comply with these rules. Non-compliant code will be rejected during code review.

---

## RULE 1: 500-Line File Limit (MANDATORY)

### Statement
**All Python source files MUST NOT exceed 500 lines of code.**

### Scope
- **Applies to:** All `.py` files in `varidex/` package
- **Excludes:** Test files, generated files, configuration files
- **Counting method:** Physical lines including comments and docstrings

### Enforcement
```bash
# Check compliance
find varidex -name "*.py" -not -path "*/tests/*" | xargs wc -l | awk '$1 > 500 {print $2 ": " $1 " lines - VIOLATION"}'
```

### Consequences of Violation
- Files >500 lines: **Automatic PR rejection**
- Files 475-500 lines: **Warning** (consider splitting before adding features)
- Files >550 lines: **Blocking issue** (must split before any other work)

### Rationale
- AI context window optimization
- Improved maintainability
- Reduced bug density
- Faster code generation
- Easier code review

---

## RULE 2: PEP 8 Naming Convention (MANDATORY)

### Statement
**All modules MUST follow Python PEP 8 naming: lowercase_with_underscores**

### Naming Patterns

#### Module Files
```
✓ CORRECT:
varidex/io/loaders/clinvar.py
varidex/core/classifier/engine.py
varidex/reports/generator.py

✗ INCORRECT:
file_5_loader.py
file_4a_classifier_CORE.py
varidex_0_exceptions.txt
```

#### Functions and Variables
```python
✓ CORRECT:
def load_clinvar_file(filepath: Path) -> pd.DataFrame:
    variant_count = len(df)
    clinical_significance = row['CLNSIG']

✗ INCORRECT:
def LoadClinvarFile(filepath: Path) -> pd.DataFrame:
    VariantCount = len(df)
    ClinicalSignificance = row['CLNSIG']
```

#### Classes
```python
✓ CORRECT:
class VariantData:
class ACMGClassifier:
class OptimizedProgressTracker:

✗ INCORRECT:
class variantData:
class acmg_classifier:
class optimized_progress_tracker:
```

#### Constants
```python
✓ CORRECT:
MAX_FILE_SIZE = 10_000_000_000
VALID_CHROMOSOMES = {'1', '2', ..., 'X', 'Y', 'MT'}
ACMG_PATHOGENIC_THRESHOLD = 10

✗ INCORRECT:
maxFileSize = 10_000_000_000
valid_chromosomes = {'1', '2', ..., 'X', 'Y', 'MT'}
```

### Enforcement
- Pre-commit hook: `pylint --errors-only`
- CI/CD: Automated naming validation
- Code review: Blocking for naming violations

---

## RULE 3: Canonical Folder Structure (MANDATORY)

### Statement
**All code MUST be organized in the canonical package structure**

### Required Structure

```
varidex/                              # Package root
├── __init__.py                       # Version exports
├── version.py                        # ✓ Single source of truth
│
├── core/                             # Core pipeline logic
│   ├── __init__.py
│   ├── config.py                     # ✓ Constants, gene lists
│   ├── models.py                     # ✓ Data models (419 lines)
│   ├── genotype.py                   # ✓ Genotype normalization
│   └── classifier/                   # ✓ ACMG classification
│       ├── __init__.py
│       ├── engine.py                 # ✓ (480 lines - compliant)
│       └── config.py                 # ✓ ACMG rules
│
├── io/                               # Input/output operations
│   ├── __init__.py
│   ├── loaders/                      # ✓ Data loaders
│   │   ├── __init__.py
│   │   ├── base.py                   # ✓ Validation utilities
│   │   ├── clinvar.py                # ✓ ClinVar formats
│   │   └── user.py                   # ✓ User genome files
│   ├── matching.py                   # ✓ Variant matching
│   ├── normalization.py              # ✓ Coordinate normalization
│   └── checkpoint.py                 # ✓ Parquet checkpointing
│
├── reports/                          # Report generation
│   ├── __init__.py
│   ├── generator.py                  # ✓ Report orchestration
│   ├── formatters.py                 # ✓ CSV/JSON/HTML
│   └── templates/                    # ✓ HTML templates
│       ├── __init__.py
│       ├── builder.py                # ✓ HTML generation
│       └── components.py             # ✓ UI components
│
├── pipeline/                         # Pipeline orchestration
│   ├── __init__.py
│   ├── orchestrator.py               # ✓ Main coordinator
│   └── stages.py                     # ✓ Pipeline stages
│
├── utils/                            # Utilities
│   ├── __init__.py
│   ├── helpers.py                    # ✓ (449 lines - compliant)
│   ├── security.py                   # ✓ Security validators
│   └── exceptions.py                 # ✓ Exception hierarchy
│
├── cli/                              # Command-line interface
│   ├── __init__.py
│   └── main.py                       # ✓ CLI entry point
│
└── tests/                            # Test suite
    ├── __init__.py
    ├── test_core.py
    ├── test_io.py
    ├── test_reports.py
    ├── test_pipeline.py
    └── test_integration.py
```

### Placement Rules

| Module Type | Location | Max Lines |
|-------------|----------|-----------|
| Data models | `varidex/core/models.py` | 500 |
| Configuration | `varidex/core/config.py` | 300 |
| ACMG classifier | `varidex/core/classifier/engine.py` | 500 |
| ClinVar loader | `varidex/io/loaders/clinvar.py` | 500 |
| User loader | `varidex/io/loaders/user.py` | 500 |
| Report generator | `varidex/reports/generator.py` | 500 |
| HTML templates | `varidex/reports/templates/builder.py` | 500 |
| Pipeline orchestrator | `varidex/pipeline/orchestrator.py` | 500 |
| Utilities | `varidex/utils/helpers.py` | 500 |

### Enforcement
- **New files:** Must be placed in correct package
- **Moved files:** Update all imports in single commit
- **Deprecated paths:** Not allowed in new code

---

## RULE 4: No File Duplication (MANDATORY)

### Statement
**PROHIBITED: Maintaining duplicate files with different extensions**

### Examples

```
✗ FORBIDDEN:
varidex/io/loader.py       # Source code
varidex/io/loader.txt      # Backup copy
varidex/io/loader_v6.py    # Versioned copy

✓ REQUIRED:
varidex/io/loaders/clinvar.py    # Single source of truth
# Version history in git, not filenames
```

### Version Management

```
✗ FORBIDDEN:
file_5_loader_v6.0.4.py
file_5_loader_v6.0.5.py
file_5_loader_PERFECT.py
file_5_loader_FINAL.py

✓ REQUIRED:
varidex/io/loaders/clinvar.py
# Version in code: __version__ = "6.0.5"
# Version in git: tags (v6.0.5)
```

### Enforcement
- Pre-commit hook: Detect duplicate file content
- CI/CD: Reject PRs with version numbers in filenames
- Code review: Blocking for duplicate files

---

## RULE 5: Type Hints (MANDATORY)

### Statement
**All public functions MUST include type hints for parameters and return values**

### Examples

```python
✓ CORRECT:
def load_clinvar_file(
    filepath: Path,
    use_checkpoint: bool = True,
    max_size: Optional[int] = None
) -> pd.DataFrame:
    """Load ClinVar data from file."""
    ...

✗ INCORRECT:
def load_clinvar_file(filepath, use_checkpoint=True, max_size=None):
    """Load ClinVar data from file."""
    ...
```

### Coverage Requirements
- **Public functions:** 100% type hints required
- **Private functions:** Recommended but not enforced
- **Complex types:** Use `typing` module

### Enforcement
```bash
# Check compliance
mypy --strict varidex/
```

---

## RULE 6: Docstring Requirements (MANDATORY)

### Statement
**All public functions, classes, and modules MUST include Google-style docstrings**

### Format

```python
def load_clinvar_vcf(
    filepath: Path,
    use_checkpoint: bool = True
) -> pd.DataFrame:
    """
    Load full ClinVar VCF file with multiallelic splitting.

    Features:
    - Handles .vcf.gz compression
    - Splits multiallelic variants
    - Extracts INFO fields (CLNSIG, GENEINFO)
    - Checkpoint caching for large files

    Args:
        filepath: Path to ClinVar VCF file
        use_checkpoint: Enable checkpoint caching for faster reloads

    Returns:
        DataFrame with columns: rsid, chromosome, position, ref_allele,
        alt_allele, gene, clinical_significance, variant_type

    Raises:
        FileNotFoundError: If filepath doesn't exist
        ValueError: If file format is invalid
        ValidationError: If required VCF fields missing

    Example:
        >>> df = load_clinvar_vcf(Path('clinvar.vcf.gz'))
        >>> print(len(df))
        2400000
    """
    ...
```

### Required Sections
- **Description:** One-line summary + detailed explanation
- **Args:** All parameters with types and descriptions
- **Returns:** Return type and description
- **Raises:** All possible exceptions
- **Example:** Usage example for complex functions

### Enforcement
- Code review: Blocking for missing docstrings
- CI/CD: `pydocstyle` validation
- Coverage: 100% for public APIs

---

## RULE 7: No Original Data Modification (ABSOLUTE)

### Statement
**PROHIBITED: Any code that modifies original ClinVar or user genome files**

### Protected Data

```python
✗ FORBIDDEN:
def process_clinvar(filepath: Path):
    # NEVER overwrite original file
    df = load_clinvar(filepath)
    df_modified = transform(df)
    df_modified.to_csv(filepath)  # ❌ VIOLATION

✓ REQUIRED:
def process_clinvar(filepath: Path, output_dir: Path):
    # Create new files, never modify originals
    df = load_clinvar(filepath)
    df_modified = transform(df)
    output_path = output_dir / f"processed_{filepath.name}"
    df_modified.to_csv(output_path)  # ✓ CORRECT
```

### Enforcement
- **Pre-commit hook:** Scan for overwrite operations
- **Code review:** Blocking for any original file modifications
- **Testing:** Integration tests verify no original data changes

---

## RULE 8: Feature Preservation (MANDATORY)

### Statement
**PROHIBITED: Removing features during refactoring without explicit approval**

### Examples

```python
✗ FORBIDDEN:
# Removing coordinate matching during split
def load_variants(filepath: Path) -> pd.DataFrame:
    # Coordinate matching removed - VIOLATION
    return load_basic(filepath)

✓ REQUIRED:
# Preserve all features, move to appropriate module
# varidex/io/loaders/base.py
def load_variants(filepath: Path) -> pd.DataFrame:
    df = load_basic(filepath)
    return df

# varidex/io/matching.py
def match_by_coordinates(user_df, clinvar_df):
    # Feature preserved in dedicated module
    ...
```

### Refactoring Rules
1. **Document features:** List all features before refactoring
2. **Verify preservation:** Test suite confirms all features work
3. **No silent removal:** Features can only be removed with issue approval
4. **Deprecation process:** Use deprecation warnings before removal

---

## RULE 9: Security Requirements (MANDATORY)

### Statement
**All user input and file operations MUST include security validation**

### Required Validations

```python
# File Input Security
def load_user_file(filepath: Path) -> pd.DataFrame:
    # 1. Path validation
    filepath = filepath.resolve()  # Resolve symlinks
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    # 2. Path traversal protection
    if '..' in str(filepath):
        raise SecurityError("Path traversal detected")
    
    # 3. Size validation
    max_size = 10_000_000_000  # 10 GB
    if filepath.stat().st_size > max_size:
        raise ValueError(f"File too large: {filepath.stat().st_size}")
    
    # 4. Permission check
    if not os.access(filepath, os.R_OK):
        raise PermissionError(f"File not readable: {filepath}")
    
    return pd.read_csv(filepath)

# HTML Output Security (XSS Protection)
def generate_html_report(data: dict) -> str:
    import html
    
    # Escape ALL user data
    safe_gene = html.escape(str(data['gene']))
    safe_rsid = html.escape(str(data['rsid']))
    
    return f"<tr><td>{safe_gene}</td><td>{safe_rsid}</td></tr>"

# rsID Validation
def validate_rsid(rsid: str) -> bool:
    """Validate rsID format to prevent injection."""
    import re
    return bool(re.match(r'^rs\d+$', str(rsid)))
```

### Security Checklist
- [ ] Path traversal protection (no `..` in paths)
- [ ] File size limits enforced
- [ ] HTML escaping for all user data
- [ ] SQL injection protection (if using SQL)
- [ ] rsID format validation
- [ ] Chromosome validation (only valid chromosomes)

### Enforcement
- **Security review:** Required for all I/O code
- **Automated scanning:** SAST tools in CI/CD
- **Penetration testing:** XSS/injection testing on HTML reports

---

## RULE 10: Test Coverage (MANDATORY)

### Statement
**All modules MUST have ≥90% test coverage**

### Requirements

| Module Type | Min Coverage | Test Types |
|-------------|--------------|------------|
| Core logic | 95% | Unit + integration |
| I/O operations | 90% | Unit + integration |
| Reports | 90% | Unit + visual regression |
| Utilities | 95% | Unit |
| Pipeline | 85% | Integration + E2E |

### Test Structure

```python
# tests/test_io_loaders_clinvar.py
import pytest
from pathlib import Path
from varidex.io.loaders.clinvar import load_clinvar_vcf

def test_load_clinvar_vcf_basic():
    """Test basic ClinVar VCF loading."""
    df = load_clinvar_vcf(Path('test_data/clinvar_mini.vcf'))
    assert len(df) > 0
    assert 'rsid' in df.columns

def test_load_clinvar_vcf_multiallelic():
    """Test multiallelic variant splitting."""
    df = load_clinvar_vcf(Path('test_data/multiallelic.vcf'))
    # rs123 with ALT=A,G should become 2 rows
    rs123_rows = df[df['rsid'] == 'rs123']
    assert len(rs123_rows) == 2

def test_load_clinvar_vcf_invalid_file():
    """Test error handling for invalid files."""
    with pytest.raises(FileNotFoundError):
        load_clinvar_vcf(Path('nonexistent.vcf'))

def test_load_clinvar_vcf_checkpoint():
    """Test checkpoint caching works."""
    # First load creates checkpoint
    df1 = load_clinvar_vcf(Path('test_data/large.vcf'), use_checkpoint=True)
    
    # Second load uses checkpoint (faster)
    df2 = load_clinvar_vcf(Path('test_data/large.vcf'), use_checkpoint=True)
    
    pd.testing.assert_frame_equal(df1, df2)
```

### Enforcement
```bash
# Check coverage
pytest --cov=varidex --cov-report=term-missing --cov-fail-under=90
```

---

## Implementation Timeline

### Phase 1: Foundation (Days 1-3) - COMPLETED ✓
- [x] Folder structure created
- [x] Naming convention established
- [x] Documentation updated

### Phase 2: File Splitting (Days 4-6) - IN PROGRESS
- [ ] Split `io/loader.py` → `loaders/{base,clinvar,user}.py`
- [ ] Split `reports/generator.py` → `generator.py` + `formatters.py`
- [ ] Split `reports/templates.py` → `templates/{builder,components}.py`
- [ ] Split `pipeline.py` → `pipeline/{orchestrator,stages}.py`

### Phase 3: Testing & Validation (Days 7-8) - PENDING
- [ ] Unit tests for all 19 modules
- [ ] Integration tests
- [ ] Coverage validation (≥90%)
- [ ] Security penetration testing
- [ ] Performance benchmarks

---

## Compliance Verification

### Automated Checks

```bash
# 1. Line count compliance
./scripts/check_line_limits.sh

# 2. Naming convention compliance
pylint --errors-only varidex/

# 3. Type hint coverage
mypy --strict varidex/

# 4. Docstring coverage
pydocstyle varidex/

# 5. Test coverage
pytest --cov=varidex --cov-fail-under=90

# 6. Security scan
bandit -r varidex/
```

### Manual Review Checklist

- [ ] All files ≤500 lines
- [ ] PEP 8 naming followed
- [ ] Correct folder placement
- [ ] No duplicate files
- [ ] Type hints present
- [ ] Docstrings complete
- [ ] No original data modification
- [ ] All features preserved
- [ ] Security validations present
- [ ] Test coverage ≥90%

---

## Exceptions and Waivers

### Requesting an Exception

Exceptions to these rules require:
1. **Written justification** (GitHub issue)
2. **Technical necessity** (not convenience)
3. **Approval from 2+ maintainers**
4. **Time-limited** (review after 6 months)

### Granted Exceptions
None currently granted.

---

## Consequences of Non-Compliance

### Pull Request Handling
- **Minor violations** (e.g., 505 lines): Request changes
- **Major violations** (e.g., 600 lines): Reject PR
- **Security violations**: Immediate rejection + security review

### Code Review Standards
- **Blocking:** Security, naming, duplication
- **Non-blocking:** Style preferences, optimization suggestions
- **Required reviewers:** 1 maintainer minimum, 2 for core modules

---

## Revision History

| Version | Date | Changes | Authority |
|---------|------|---------|-----------|
| 1.0 | 2026-01-21 | Initial binding rules from approved proposal | Architecture Team |

---

## References

- [VariDex_500_Line_Limit_Migration_Proposal.md](VariDex_500_Line_Limit_Migration_Proposal.md) - Original analysis
- [PEP 8 - Style Guide for Python Code](https://pep8.org/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [VariDex Canonical Schema](VariDex%20Canonical%20Schema.md)

---

**END OF BINDING RULES**
