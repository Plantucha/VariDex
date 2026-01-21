# VariDex v6.0.0 File Splits

**Document Version:** 1.0  
**Last Updated:** 2026-01-19  

Detailed breakdown of 7 file splits to enforce 500-line limit.

---

## Split 1: file_5_loader.txt (551L → 3 files)

### New Structure

```
varidex/io/loaders/
├── clinvar.py (250 lines) - ClinVar parsers
├── user.py (150 lines) - User genome loaders
└── matching.py (150 lines) - Variant matching
```

### Critical Bug Fix

```python
# BUG: Return value ignored
normalize_dataframe_coordinates(user_df)

# FIX: Assign return value
user_df = normalize_dataframe_coordinates(user_df)
```

---

## Split 2: file_6a_generator.txt (590L → 2 files)

```
varidex/reports/
├── generator.py (300 lines) - Orchestration, DataFrame creation
└── formatters.py (290 lines) - CSV/JSON/HTML generators
```

**Version Fix:** v5.2 → v6.0.0

**Preserve signatures:**
```python
generate_csv_report(df, output_file)
generate_json_report(df, output_file, full_data=True)
generate_html_report(df, output_file)
```

---

## Split 3: file_6B_templates.txt (600L → 2 files)

```
varidex/reports/templates/
├── builder.py (300 lines) - HTML template generator
└── components.py (300 lines) - Cards, tables, legends
```

**Security:** HTML-escape ALL user data:
```python
import html
safe_gene = html.escape(str(variant.gene))
```

---

## Split 4: file_7a_main.txt (582L → 2 files)

```
varidex/pipeline/
├── orchestrator.py (450 lines) - Main loop, utilities
└── stages.py (232 lines) - Stage 2-7 implementations
```

---

## Split 5: file_0_downloader.txt (650L → 2 files)

```
varidex/io/
├── downloader.py (400 lines) - Download orchestration
└── validators.py (250 lines) - MD5, disk space checks
```

---

## Single-File Reductions

### file_2_models.txt (571L → 500L)

Remove VEP hallucination (71 lines):
```python
# DELETE unused fields:
aaposition: Optional[int] = None
aachange: Optional[str] = None
```

### file_7b_helpers.txt (598L → 500L)

Move ErrorCode enum (60 lines) to exceptions.py

---

## Import Dependencies

```python
# generator.py → formatters.py
from varidex.reports.formatters import generate_csv_report

# orchestrator.py → stages.py
from varidex.pipeline.stages import stage2_load_clinvar

# downloader.py → validators.py
from varidex.io.validators import verify_md5
```

**Critical:** No circular imports!

---

## Summary Table

| Original File | Lines | New Files | Lines Each | Strategy |
|---------------|-------|-----------|------------|----------|
| file_5_loader.txt | 551 | 3 files | 250+150+150 | Functional split |
| file_6a_generator.txt | 590 | 2 files | 300+290 | Orchestration/formatters |
| file_6B_templates.txt | 600 | 2 files | 300+300 | Builder/components |
| file_7a_main.txt | 582 | 2 files | 450+232 | Orchestrator/stages |
| file_0_downloader.txt | 650 | 2 files | 400+250 | Download/validators |
| file_2_models.txt | 571 | 1 file | 500 | Reduction only |
| file_7b_helpers.txt | 598 | 1 file | 500 | Reduction only |

**Total:** 7 files → 13 files (all ≤500 lines)

---

## Files That Stay Intact (6 files)

```
✓ core/classifier/engine.py   480 lines (96% utilization)
✓ utils/helpers.py            449 lines (90% utilization)
✓ core/models.py              419 lines (84% utilization)
✓ core/genotype.py            315 lines
✓ io/normalization.py         300 lines
✓ utils/security.py           250 lines
```

---

See also:
- `01_overview.md`: Migration rationale
- `03_version_unification.md`: Version fixes
- `04_security_fixes.md`: Security patches
- `05_testing_deployment.md`: Testing plan
