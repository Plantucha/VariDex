# ACMG Classifier Engine Version History

**Last Updated:** January 24, 2026  
**Current Production Version:** `engine.py` (v6.4.0)

---

## ⚠️ Version Fragmentation Notice

The classifier currently has **three engine implementations** that co-exist:

| File | Version | Status | Evidence Codes | External Dependencies |
|------|---------|--------|----------------|----------------------|
| **engine.py** | v6.4.0 | ✅ **PRODUCTION** | 7/28 (25%) | None (standalone) |
| engine_v7.py | v7.0.0-alpha | 🧪 EXPERIMENTAL | 9/28 (32%) | gnomAD API |
| engine_v8.py | v8.0.0-alpha | 🧪 EXPERIMENTAL | 12/28 (43%) | gnomAD + SpliceAI + dbNSFP |

**Recommendation:** Use `ACMGClassifier` from `engine.py` for production. V7 and V8 are research prototypes.

---

## Version Details

### **engine.py** - Current Production (v6.4.0) ✅

**Status:** 🟢 **PRODUCTION READY** (as of v6.4.1 after bug fixes)

**Implementation:**
- **7 ACMG evidence codes** (25% coverage):
  - **Pathogenic:** PVS1, PM4, PP2
  - **Benign:** BA1, BS1, BP1, BP3
- **Zero external dependencies**
- **Fast classification** (~3ms per variant)
- **Well-tested** (86% coverage)
- **Type-safe** (100% type hints)

**Use Cases:**
- Production genomic analysis
- Batch variant processing
- Research without external API access
- Offline variant classification

**Limitations:**
- No population frequency data (PM2 disabled)
- No computational predictions (PP3, BP4 disabled)
- No splicing predictions (BP7 disabled)
- No functional domain data (PM1 disabled)

**Import:**
```python
from varidex.core.classifier import ACMGClassifier

classifier = ACMGClassifier()
result = classifier.classify_variant(variant)
```

---

### **engine_v7.py** - Experimental with gnomAD (v7.0.0-alpha) 🧪

**Status:** 🟡 **EXPERIMENTAL** (Not production-validated)

**Implementation:**
- **9 ACMG evidence codes** (32% coverage):
  - Adds: **PM2** (absent from gnomAD), **BS2** (observed in healthy individuals)
- **External Dependencies:**
  - gnomAD API (requires internet connection)
  - Rate limiting (max 10 requests/second)
- **Slower classification** (~500ms per variant due to API calls)

**Additional Features:**
- Population frequency from gnomAD v3.1
- Allele count filtering
- Subpopulation analysis
- Caching for repeated queries

**Use Cases:**
- Research requiring population data
- Validation of PM2 evidence
- Testing gnomAD integration

**Limitations:**
- Requires gnomAD API key
- Network dependency
- Slower than base engine
- Not extensively tested
- May hit rate limits on large batches

**Import:**
```python
from varidex.core.classifier import ACMGClassifierV7

classifier = ACMGClassifierV7(gnomad_api_key="your_key")
result = classifier.classify_variant(variant)
```

---

### **engine_v8.py** - Experimental with Predictions (v8.0.0-alpha) 🧪

**Status:** 🟡 **EXPERIMENTAL** (Not production-validated)

**Implementation:**
- **12 ACMG evidence codes** (43% coverage):
  - Adds: **PM2**, **PP3** (computational predictions), **BP4** (predictions benign), **BP7** (splicing)
- **External Dependencies:**
  - gnomAD API
  - SpliceAI predictions
  - dbNSFP database (local or API)
- **Much slower classification** (~2-5 seconds per variant)

**Additional Features:**
- CADD, REVEL, SIFT, PolyPhen scores
- SpliceAI delta scores
- Conservation scores (PhyloP, PhastCons)
- Meta-predictions (MetaSVM, MetaLR)

**Use Cases:**
- Research requiring computational predictions
- Validation of PP3/BP4/BP7 evidence
- Comprehensive variant analysis
- Testing full ACMG implementation

**Limitations:**
- Requires multiple external dependencies
- Very slow (2-5 seconds per variant)
- High memory usage (dbNSFP is ~20GB)
- Not production-tested
- Complex setup required
- Prediction accuracy not validated

**Import:**
```python
from varidex.core.classifier import ACMGClassifierV8

classifier = ACMGClassifierV8(
    gnomad_api_key="your_key",
    dbnsfp_path="/path/to/dbNSFP",
    spliceai_enabled=True
)
result = classifier.classify_variant(variant)
```

---

## Choosing the Right Engine

### Use `engine.py` (ACMGClassifier) if:

✅ You need production-ready classification  
✅ You want fast, reliable results  
✅ You don't have external API access  
✅ You're processing large batches (1000+ variants)  
✅ You want zero external dependencies  
✅ You need offline capability  

### Use `engine_v7.py` (ACMGClassifierV7) if:

🧪 You're doing research requiring population frequencies  
🧪 You have gnomAD API access  
🧪 You need PM2/BS2 evidence codes  
🧪 You're willing to accept slower classification  
🧪 You're testing integration with gnomAD  

### Use `engine_v8.py` (ACMGClassifierV8) if:

🧪 You're doing comprehensive research  
🧪 You have all external dependencies set up  
🧪 You need computational predictions (PP3/BP4/BP7)  
🧪 Classification speed is not critical  
🧪 You're testing the full ACMG implementation  

---

## Migration Guide

### From V7 to Base Engine

```python
# Before (V7)
from varidex.core.classifier import ACMGClassifierV7
classifier = ACMGClassifierV7(gnomad_api_key=key)

# After (Base)
from varidex.core.classifier import ACMGClassifier
classifier = ACMGClassifier()  # No API key needed

# Note: PM2 and BS2 will not be assigned
```

### From V8 to Base Engine

```python
# Before (V8)
from varidex.core.classifier import ACMGClassifierV8
classifier = ACMGClassifierV8(
    gnomad_api_key=key,
    dbnsfp_path=path,
    spliceai_enabled=True
)

# After (Base)
from varidex.core.classifier import ACMGClassifier
classifier = ACMGClassifier()  # Simplified

# Note: PM2, PP3, BP4, BP7 will not be assigned
```

---

## Future Consolidation Plan

**Goal:** Merge all engines into a single configurable classifier by v7.0.0

### Proposed Architecture (v7.0.0)

```python
from varidex.core.classifier import ACMGClassifier

# Base configuration (fast, no dependencies)
classifier = ACMGClassifier()

# With optional integrations
classifier = ACMGClassifier(
    integrations={
        "gnomad": {"api_key": key, "enabled": True},
        "spliceai": {"enabled": True},
        "dbnsfp": {"path": path, "enabled": True}
    }
)
```

**Benefits:**
- Single engine file
- Optional features via configuration
- Graceful degradation if dependencies missing
- Easier to maintain
- Clearer for users

**Timeline:**
- v6.5: Document current state (this file)
- v6.6-6.9: Refactor engines with plugin architecture
- v7.0: Consolidate into single configurable engine
- v7.1+: Remove engine_v7.py and engine_v8.py

---

## Version Comparison Table

| Feature | engine.py | engine_v7.py | engine_v8.py |
|---------|-----------|--------------|-------------|
| **Status** | Production | Experimental | Experimental |
| **Evidence Codes** | 7/28 | 9/28 | 12/28 |
| **External APIs** | None | gnomAD | gnomAD + SpliceAI + dbNSFP |
| **Speed** | Fast (~3ms) | Medium (~500ms) | Slow (~2-5s) |
| **Setup Complexity** | None | Medium | High |
| **Memory Usage** | Low (~50MB) | Medium (~200MB) | High (~2GB) |
| **Internet Required** | No | Yes | Yes |
| **Test Coverage** | 86% | ~40% | ~20% |
| **Production Ready** | Yes | No | No |
| **Recommended Use** | Production | Research | Research |

---

## FAQ

### Q: Which engine should I use?

**A:** Use `engine.py` (ACMGClassifier) unless you specifically need gnomAD or computational predictions for research.

### Q: Can I use V7 or V8 in production?

**A:** Not recommended. They are experimental and not extensively tested. Use for research only.

### Q: Will V7 and V8 be removed?

**A:** Yes, they will be consolidated into the main engine with optional features in v7.0 (Q2 2026).

### Q: How do I enable gnomAD in the base engine?

**A:** Currently not supported. Wait for v7.0 consolidation, or use engine_v7.py experimentally.

### Q: What's the performance difference?

**A:** Base engine: ~3ms/variant, V7: ~500ms/variant, V8: ~2-5s/variant. For 10,000 variants: 30s vs 1.4h vs 5.6-13.9h.

### Q: Can I switch engines mid-analysis?

**A:** Not recommended. Stick with one engine per analysis for consistency.

---

## Technical Notes

### File Sizes

| File | Lines | Size | Status |
|------|-------|------|--------|
| engine.py | 297 | 11.3 KB | ✅ Under 500 |
| engine_v7.py | 354 | 10.6 KB | ✅ Under 500 |
| engine_v8.py | 442 | 13.2 KB | ✅ Under 500 |

### Import Availability

All three engines can be imported, but V7 and V8 require optional dependencies:

```python
# Always available
from varidex.core.classifier import ACMGClassifier

# Available if dependencies installed
from varidex.core.classifier import ACMGClassifierV7  # Needs gnomad-api
from varidex.core.classifier import ACMGClassifierV8  # Needs gnomad-api, spliceai, dbnsfp
```

### Testing Status

| Engine | Unit Tests | Integration Tests | E2E Tests | Coverage |
|--------|------------|-------------------|-----------|----------|
| engine.py | 40+ | 15+ | 10+ | 86% |
| engine_v7.py | 15+ | 5+ | 2+ | ~40% |
| engine_v8.py | 10+ | 3+ | 1+ | ~20% |

---

## Conclusion

**For most users:** Use `engine.py` (ACMGClassifier) - it's production-ready, fast, and well-tested.

**For researchers:** V7 and V8 provide additional evidence codes but are experimental and require external dependencies.

**Future:** All engines will be consolidated into a single configurable classifier in v7.0.

---

**Questions?** See [GitHub Issues](https://github.com/Plantucha/VariDex/issues) or [Discussions](https://github.com/Plantucha/VariDex/discussions)

**Last Updated:** January 24, 2026 by VariDex Development Team
