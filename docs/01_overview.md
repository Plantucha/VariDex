# VariDex v6.0.0 Migration Overview

**Document Version:** 1.0  
**Last Updated:** 2026-01-19  
**Status:** Phase 2 (Execution)

---

## Executive Summary

**Objective:** Enforce 500-line coding standard across VariDex codebase.

**Current State:**
- 13 Python files (7 exceed 500 lines)
- 5 different versions (5.2, 6.0.0, 6.0.1, 6.0.4, v18)
- Security vulnerabilities (XSS, CSV injection)
- Import duplication (20-30 lines per file)

**Target State:**
- 20 Python files (all ≤500 lines)
- Single version (6.0.0)
- Security hardened
- Centralized imports

---

## Rationale

### Why 500 Lines?

**Cognitive Load:**
- Human working memory: 5-9 items (Miller, 1956)
- 500 lines ≈ 10-15 functions
- Manageable in single sitting

**Code Review:**
- GitHub shows 500 lines without scrolling
- Easier diff review
- Faster approval cycles

**Maintainability:**
- Single Responsibility Principle
- Easier debugging
- Lower defect density

### Benefits

**Developer Experience:**
- ✅ Faster file navigation
- ✅ Clearer module boundaries
- ✅ Easier onboarding

**Code Quality:**
- ✅ Forced modularity
- ✅ Better separation of concerns
- ✅ Higher test coverage (smaller units)

**Performance:**
- ✅ Faster imports (lazy loading)
- ✅ Reduced memory footprint
- ✅ Better IDE performance

---

## Scope

### Files Requiring Splits (7 files)

| File | Current | Target | Strategy |
|------|---------|--------|----------|
| file_2_models.txt | 571 | 500 | Remove VEP hallucination (71 lines) |
| file_5_loader.txt | 551 | 3×150 | Split: clinvar, user, matching |
| file_6a_generator.txt | 590 | 2×300 | Split: generator, formatters |
| file_6B_templates.txt | 600 | 2×300 | Split: builder, components |
| file_7a_main.txt | 582 | 2×290 | Split: orchestrator, stages |
| file_7b_helpers.txt | 598 | 500 | Move ErrorCode (60L) to exceptions |
| file_0_downloader.txt | 650 | 2×325 | Split: downloader, validators |

### Version Unification (5 versions → 1)

**Files to Update:**
- file_2_models.txt: v6.0.1 → v6.0.0
- file_5_loader.txt: v6.0.4 → v6.0.0
- file_6a_generator.txt: v5.2 → v6.0.0
- file_6B_templates.txt: v5.2 → v6.0.0
- file_0_downloader.txt: v18 → v6.0.0

**Target:** All files use `from varidex.version import __version__`

---

## Migration Strategy

### Phase 1: Planning (COMPLETE)
- ✅ Analyze all 13 files
- ✅ Identify split points
- ✅ Generate AI coder instructions

### Phase 2: Execution (IN PROGRESS)
- 🔄 AI Coders #1-8: Already provided instructions
- ⏳ AI Coders #9-20: Instructions being generated

### Phase 3: Integration
- Verify all imports resolve
- Run test suite
- Update documentation

### Phase 4: Deployment
- Merge to main branch
- Tag release v6.0.0
- Update package metadata

---

## Key Metrics Comparison

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

---

## Success Criteria

**Code Standards:**
- ✅ All files ≤500 lines
- ✅ Single version (6.0.0)
- ✅ No import duplication
- ✅ Type hints on all functions

**Quality:**
- ✅ All tests pass
- ✅ Security scans clean
- ✅ No circular imports
- ✅ Documentation updated

**Performance:**
- ✅ Import time <200ms
- ✅ Classification speed maintained
- ✅ Memory usage stable

---

## Cost-Benefit Analysis

### Development Costs

| Phase | Time | Cost |
|-------|------|------|
| Phase 1: Planning | 3 days | $2.4k-$3.6k |
| Phase 2: Execution | 3 days | $2.4k-$3.6k |
| Phase 3: Testing | 2 days | $1.6k-$2.4k |
| **Total** | **8 days** | **$6.4k-$9.6k** |

### Annual Benefits

| Benefit | Annual Value |
|---------|--------------|
| Faster AI generation | $5,000 |
| Reduced bugs | $10,000 |
| Easier maintenance | $8,000 |
| Better onboarding | $3,000 |
| **Total** | **$26,000/year** |

**ROI:** 2.7-4.0x in first year

---

## Next Steps

See remaining documentation:
- `02_file_splits.md`: Detailed split strategies
- `03_version_unification.md`: Version migration guide
- `04_security_fixes.md`: Security vulnerability patches
- `05_testing_deployment.md`: Testing and deployment plan
