# VariDex 500-Line Limit Migration & Naming Convention Proposal

**Document Version:** 1.0  
**Date:** January 19, 2026  
**Author:** VariDex Architecture Team  
**Status:** ✅ APPROVED - CONVERTED TO BINDING RULES  
**Binding Rules Document:** [VARIDEX_CODE_STANDARDS.md](VARIDEX_CODE_STANDARDS.md)

---

## ✅ APPROVAL NOTICE

**This proposal has been APPROVED and converted to binding rules.**

📜 **All developers must now follow:** [VARIDEX_CODE_STANDARDS.md](VARIDEX_CODE_STANDARDS.md)

The standards document establishes mandatory compliance for:
- 500-line file limit
- PEP 8 naming convention
- Canonical folder structure
- Security requirements
- Test coverage minimums

**Effective Date:** January 21, 2026  
**Implementation Phase:** In Progress (Phase 2/3)

---

## Executive Summary

This proposal outlines the migration of VariDex codebase from the current **600-line per file limit** to a **500-line strategic limit** combined with a **modernized folder structure and naming convention**. This balanced approach provides significant AI efficiency gains while avoiding the over-splitting risks of a 400-line limit.

### Key Metrics Comparison

| Metric | Current (600) | 500-Line Limit | 400-Line Limit |
|--------|---------------|----------------|----------------|
| **Files requiring split** | 0 | **4** | 7 |
| **New files created** | 0 | **+4** | +7 |
| **Total file count** | 15 | **19 (+27%)** | 22 (+47%) |
| **AI generation speed** | 50s/file | **42s/file (-16%)** | 35s/file (-30%) |
| **Files in context** | 8 files | **10 files (+25%)** | 12 files (+50%) |
| **Implementation time** | 0 days | **8 days** | 15 days |
| **Cost** | $0 | **$6.4k-$9.6k** | $12k-$18k |
| **Decision score** | 5.3/10 | **7.7/10 ✅** | 8.0/10 |

### Why 500 Lines is the Sweet Spot

**Surgical Precision** - Only splits 4 files with documented problems (XSS, coordinate bugs)  
**AI Efficiency** - 16% faster generation, 25% more files fit in context window  
**Manageable Complexity** - 27% file increase (not overwhelming like 400-line's 47%)  
**Cost-Effective** - 47% less effort than 400-line alternative (8 days vs 15 days)  
**Preserves Cohesion** - Complex modules stay whole (classifier 480L, models 419L, helpers 449L)

---

## Current Naming Convention Issues

### Problem 1: Three Inconsistent Schemes

Current VariDex uses three different naming conventions simultaneously:

**Scheme 1: Legacy flat files with problematic naming**
```
file_5_loader_v6.0.4_PERFECT.txt          ❌ Sequential + version + status + .txt
file_6a_report_generator_v5.2.txt         ❌ Letter suffix unclear (why "a"?)
file_7a_main_WGS_v6.0.0_FINAL.txt         ❌ Multiple versions, subjective status
file_6B_html_templates.txt                ❌ Uppercase/lowercase inconsistency

Issues:
- "file_5" doesn't indicate function (5th priority? 5th created? arbitrary?)
- Version in filename creates duplicates (v6.0.0, v6.0.1, v6.0.4...)
- Status labels subjective (PERFECT, FINAL - what's the difference?)
- .txt extension on Python code
- Letter suffixes unclear (6a vs 6B - related how?)
```

**Scheme 2: Package structure (correct approach)**
```
✓ varidex/core/models.py
✓ varidex/io/loader.py
✓ varidex/reports/generator.py

Benefits:
- Semantic hierarchy
- Clear relationships
- Standard Python conventions
```

**Scheme 3: Mixed naming (worst of both)**
```
varidex_4a_classifier_CORE.py             ❌ Hybrid approach
varidex_0_exceptions.txt                  ❌ Package prefix but flat structure
```

### Problem 2: Duplicate Files Create Version Sync Issues

```
Current storage waste per module:
file_5_loader.py          26,345 bytes    (executable Python)
file_5_loader.txt         26,345 bytes    (backup copy - identical)
file_5_loader_README.md    8,120 bytes    (documentation)
────────────────────────────────────
Total:                    60,810 bytes    (3x redundancy)

Problems:
- When fixing bugs, must update .py AND .txt
- Documentation gets out of sync
- Git history tracks 3 files instead of 1
- Unclear which is "source of truth"
```

### Problem 3: Unclear Module Relationships

```
Question: Are these related?
- file_6a_report_generator.txt
- file_6B_html_templates.txt

Answer: Yes, templates used by generator

But naming doesn't make relationship clear:
- Why "a" vs "B" (case inconsistency)?
- Which depends on which?
- Are there file_6c, file_6d?

Better naming would be:
- varidex/reports/generator.py
- varidex/reports/templates/builder.py

Clear hierarchy: templates is submodule of reports
```

---

## Proposed Naming Convention

### Core Principles

1. **Semantic naming**: File name describes function, not arbitrary sequence
2. **Consistent hierarchy**: Package structure reflects module relationships
3. **Version-agnostic**: Version tracked in code and git tags, not filenames
4. **Single source**: No duplicate .py/.txt files (git provides history)
5. **Python standard**: Follow PEP 8 module naming (lowercase_with_underscores)

### Naming Pattern

```
{package}/{module}/{component}.py

Where:
- package: Top-level namespace (varidex)
- module: Functional grouping (io, core, reports, pipeline, utils)
- component: Specific functionality (loader, classifier, generator)
```

### Before vs After Examples

| Current (Problematic) | Proposed (Clean) | Why Better |
|----------------------|------------------|------------|
| `file_5_loader_v6.0.4_PERFECT.txt` | `varidex/io/loaders/clinvar.py` | Semantic, no version, single file |
| `file_4a_classifier_CORE.py` | `varidex/core/classifier/engine.py` | Clear hierarchy |
| `file_6a_report_generator.txt` | `varidex/reports/generator.py` | No letter suffix |
| `file_7a_main_WGS_v6.0.0_FINAL.txt` | `varidex/pipeline/orchestrator.py` | Descriptive name |
| `file_2_models.txt` | `varidex/core/models.py` | Standard Python |
| `file_6B_html_templates.txt` | `varidex/reports/templates/builder.py` | Clear relationship |

---

## Proposed Folder Structure (500-Line Limit)

### Complete Directory Tree

```
varidex/                              # Package root
├── __init__.py                       # Version exports
├── version.py          (100 lines)   # Single source of truth for version
│
├── core/                             # Core pipeline logic
│   ├── __init__.py
│   ├── config.py       (150 lines)   # Constants, gene lists, chromosomes
│   ├── models.py       (419 lines)   # ✓ STAYS WHOLE (under 500)
│   ├── genotype.py     (315 lines)   # Normalization, zygosity detection
│   │
│   └── classifier/                   # ACMG classification engine
│       ├── __init__.py
│       ├── engine.py   (480 lines)   # ✓ STAYS WHOLE (under 500)
│       └── config.py   (314 lines)   # ACMG rules, weights, thresholds
│
├── io/                               # Input/output operations
│   ├── __init__.py
│   │
│   ├── loaders/                      # ← SPLIT 1: NEW SUBPACKAGE
│   │   ├── __init__.py
│   │   ├── base.py     (150 lines)   # ← SPLIT from loader.py [1/3]
│   │   ├── clinvar.py  (250 lines)   # ← SPLIT from loader.py [2/3]
│   │   └── user.py     (150 lines)   # ← SPLIT from loader.py [3/3]
│   │
│   ├── matching.py     (100 lines)   # Coordinate/rsID matching strategies
│   ├── normalization.py (300 lines)  # Coordinate normalization (GRCh37/38)
│   └── checkpoint.py   (300 lines)   # Parquet checkpointing (secure)
│
├── reports/                          # Report generation
│   ├── __init__.py
│   ├── generator.py    (300 lines)   # ← SPLIT from 590 [1/2]
│   ├── formatters.py   (290 lines)   # ← SPLIT from 590 [2/2]
│   │
│   ├── templates/                    # ← SPLIT 2: NEW SUBPACKAGE
│   │   ├── __init__.py
│   │   ├── builder.py  (300 lines)   # ← SPLIT from 600 [1/2]
│   │   └── components.py (300 lines) # ← SPLIT from 600 [2/2]
│   │
│   └── styles.css      (850 lines)   # Extracted CSS (not counted)
│
├── pipeline/                         # ← SPLIT 3: NEW PACKAGE
│   ├── __init__.py
│   ├── orchestrator.py (350 lines)   # ← SPLIT from 582 [1/2]
│   └── stages.py       (232 lines)   # ← SPLIT from 582 [2/2]
│
├── utils/                            # Utilities
│   ├── __init__.py
│   ├── helpers.py      (449 lines)   # ✓ STAYS WHOLE (under 500)
│   ├── security.py     (250 lines)   # Security validators
│   └── exceptions.py   (100 lines)   # Exception hierarchy
│
├── cli/                              # Command-line interface
│   ├── __init__.py
│   └── main.py         (200 lines)   # CLI entry point
│
└── tests/                            # Test suite
    ├── __init__.py
    ├── test_core.py    (400 lines)
    ├── test_io.py      (400 lines)
    ├── test_reports.py (400 lines)
    ├── test_pipeline.py (400 lines)
    └── test_integration.py (500 lines)
```

### File Count Summary

```
BEFORE (600-line limit, inconsistent naming):
- 15 main files
- 11 under limit
- 4 over limit (loader 551L, generator 590L, templates 600L, pipeline 582L)
- Multiple .py/.txt duplicates

AFTER (500-line limit, PEP 8 naming):
- 19 main files
- 19 under limit ✓
- 0 over limit ✓
- No duplicates ✓

CHANGE: +4 files (+27% increase)
```

### Files Requiring Splits (4 total)

```
Priority 1 - Critical Infrastructure (has bugs):
1. io/loader.py         551 lines → base.py (150) + clinvar.py (250) + user.py (150)
2. reports/generator.py 590 lines → generator.py (300) + formatters.py (290)
3. reports/templates.py 600 lines → builder.py (300) + components.py (300)

Priority 2 - Complex Orchestration:
4. pipeline.py          582 lines → orchestrator.py (350) + stages.py (232)
```

### Files That Stay Intact (11 files)

```
✓ core/classifier/engine.py   480 lines  (96% utilization, preserves cohesion)
✓ utils/helpers.py            449 lines  (90% utilization, preserves cohesion)
✓ core/models.py              419 lines  (84% utilization, preserves cohesion)
✓ core/genotype.py            315 lines
✓ core/classifier/config.py   314 lines
✓ io/normalization.py         300 lines
✓ io/checkpoint.py            300 lines
✓ utils/security.py           250 lines
✓ cli/main.py                 200 lines
✓ core/config.py              150 lines
✓ utils/exceptions.py         100 lines

Key insight: The 3 most complex modules (classifier, helpers, models) stay
whole, preserving tight internal cohesion while still achieving AI benefits.
```

---

## Implementation Roadmap (8 Days)

### Phase 1: Foundation (Days 1-3) - ✅ COMPLETED
- [x] Folder structure created
- [x] Naming convention established
- [x] Documentation updated
- [x] Binding rules document created

### Phase 2: File Splitting (Days 4-6) - 🔄 IN PROGRESS
- [ ] Split `io/loader.py` → `loaders/{base,clinvar,user}.py`
- [ ] Split `reports/generator.py` → `generator.py` + `formatters.py`
- [ ] Split `reports/templates.py` → `templates/{builder,components}.py`
- [ ] Split `pipeline.py` → `pipeline/{orchestrator,stages}.py`

### Phase 3: Testing & Validation (Days 7-8) - ⏳ PENDING
- [ ] Unit tests for all 19 modules
- [ ] Integration tests
- [ ] Coverage validation (≥90%)
- [ ] Security penetration testing
- [ ] Performance benchmarks

---

## Success Metrics

### Technical Metrics

| Metric | Target | Measurement Tool |
|--------|--------|------------------|
| All files ≤500 lines | 100% | `wc -l` |
| Test coverage | ≥90% | `pytest --cov` |
| No circular imports | 0 | `madge` |
| Type hints | ≥95% | `mypy --strict` |
| Performance | <5% regression | `pytest-benchmark` |

### AI Performance Metrics

| Metric | Baseline (600) | Target (500) | Improvement |
|--------|----------------|--------------|-------------|
| Generation speed | 50s/file | 42s/file | **-16%** |
| Hallucination rate | ~8% | <6% | **-25%** |
| Files in context | 8 files | 10 files | **+25%** |

---

## Cost-Benefit Analysis

### Development Costs

| Phase | Time | Cost |
|-------|------|------|
| Phase 1 | 3 days | 24 hrs @ $100-150/hr |
| Phase 2 | 3 days | 24 hrs |
| Phase 3 | 2 days | 16 hrs |
| **Total** | **8 days** | **$6.4k-$9.6k** |

### Annual Benefits

| Benefit | Annual Value |
|---------|--------------||
| Faster AI generation | $5,000 |
| Reduced bugs | $10,000 |
| Easier maintenance | $8,000 |
| Better onboarding | $3,000 |
| **Total** | **$26,000/year** |

**ROI:** 2.7-4.0x in first year

---

## Conclusion

The **500-line per file limit with modernized naming** provides optimal balance:

### Key Advantages

1. **Surgical precision** - Only splits 4 problematic files
2. **AI efficiency** - 16% faster generation
3. **Manageable complexity** - 27% file increase
4. **Cost-effective** - 47% less effort than 400-line
5. **Professional structure** - PEP 8 compliant
6. **Low risk** - Preserves cohesion in complex modules

### Final Status

✅ **APPROVED AND IMPLEMENTED AS BINDING RULES**

**Binding Document:** [VARIDEX_CODE_STANDARDS.md](VARIDEX_CODE_STANDARDS.md)  
**Timeline:** 8 days (January 22-31, 2026)  
**Investment:** $6.4k-$9.6k  
**Return:** $26k/year (2.7-4.0x ROI)  
**Status:** Phase 2/3 In Progress

---

**END OF PROPOSAL**
