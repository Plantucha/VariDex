"""varidex/core/classifier - ACMG Variant Classifier

Production-grade ACMG 2015 variant classification system.

**IMPORTANT: Version Clarification**

This module contains THREE classifier engines:

1. **ACMGClassifier** (engine.py) - ✅ PRODUCTION (v6.4.0)
   - 7 ACMG evidence codes (25%)
   - Fast, reliable, no external dependencies
   - 86% test coverage
   - **RECOMMENDED for production use**

2. **ACMGClassifierV7** (engine_v7.py) - 🧪 EXPERIMENTAL
   - 9 ACMG evidence codes (32%)
   - Requires gnomAD API access
   - Slower, not production-tested
   - **For research use only**

3. **ACMGClassifierV8** (engine_v8.py) - 🧪 EXPERIMENTAL
   - 12 ACMG evidence codes (43%)
   - Requires gnomAD + SpliceAI + dbNSFP
   - Very slow, not production-tested
   - **For research use only**

See VERSION_HISTORY.md for detailed comparison and migration guide.

Modules:
    - engine: ACMGClassifier main implementation (v6.4.0) - PRODUCTION
    - engine_v7: ACMGClassifierV7 with gnomAD - EXPERIMENTAL
    - engine_v8: ACMGClassifierV8 with predictions - EXPERIMENTAL
    - config: ACMGConfig and presets
    - evidence_utils: Utility functions for evidence assignment
    - evidence_assignment: Evidence code assignment logic

Recommended Usage:
    from varidex.core.classifier import ACMGClassifier

    classifier = ACMGClassifier()
    classification, confidence, evidence, duration = classifier.classify_variant(variant)

Refactored in v6.4.0:
    - Split engine.py into 3 files for better modularity
    - All files now under 500-line limit
    - Maintained backward compatibility

Consolidation Plan:
    - v6.5: Document current state (VERSION_HISTORY.md) ✅
    - v6.6-6.9: Refactor with plugin architecture
    - v7.0: Consolidate into single configurable engine
    - v7.1+: Remove engine_v7.py and engine_v8.py
"""

from typing import List
import warnings
from varidex.version import get_version

__version__: str = get_version("core.classifier")

# Core classifier engines
from .engine import ACMGClassifier
from .config import ACMGConfig, ACMGMetrics

# Utility functions
from .evidence_utils import (
    get_star_rating,
    validate_variant,
    extract_genes,
    check_lof,
    LOF_INDICATORS,
)

# Evidence assignment
from .evidence_assignment import (
    assign_evidence_codes,
    assign_pathogenic_evidence,
    assign_benign_evidence,
)

# Advanced classifiers (optional imports with graceful degradation)
HAS_V7: bool = False
HAS_V8: bool = False

try:
    from .engine_v7 import ACMGClassifierV7

    HAS_V7 = True
    
    # Issue warning when V7 is imported
    warnings.warn(
        "ACMGClassifierV7 is EXPERIMENTAL and not production-tested. "
        "Use ACMGClassifier for production. See VERSION_HISTORY.md for details.",
        UserWarning,
        stacklevel=2
    )
except ImportError as e:
    # V7 requires gnomAD dependencies
    def ACMGClassifierV7(*args, **kwargs):
        raise ImportError(
            "ACMGClassifierV7 requires gnomAD integration. "
            "Install with: pip install varidex[gnomad]\n"
            f"Original error: {e}"
        )

try:
    from .engine_v8 import ACMGClassifierV8

    HAS_V8 = True
    
    # Issue warning when V8 is imported
    warnings.warn(
        "ACMGClassifierV8 is EXPERIMENTAL and not production-tested. "
        "Use ACMGClassifier for production. See VERSION_HISTORY.md for details.",
        UserWarning,
        stacklevel=2
    )
except ImportError as e:
    # V8 requires gnomAD + SpliceAI + dbNSFP dependencies
    def ACMGClassifierV8(*args, **kwargs):
        raise ImportError(
            "ACMGClassifierV8 requires gnomAD, SpliceAI, and dbNSFP integration. "
            "Install with: pip install varidex[predictions]\n"
            f"Original error: {e}"
        )

__all__: List[str] = [
    # Main classifier (PRODUCTION)
    "ACMGClassifier",  # ✅ Use this for production
    "ACMGConfig",
    "ACMGMetrics",
    # Utility functions
    "get_star_rating",
    "validate_variant",
    "extract_genes",
    "check_lof",
    "LOF_INDICATORS",
    # Evidence assignment
    "assign_evidence_codes",
    "assign_pathogenic_evidence",
    "assign_benign_evidence",
    # Version flags
    "HAS_V7",
    "HAS_V8",
]

# Add experimental classifiers to exports (with warnings)
if HAS_V7:
    __all__.append("ACMGClassifierV7")  # 🧪 EXPERIMENTAL
if HAS_V8:
    __all__.append("ACMGClassifierV8")  # 🧪 EXPERIMENTAL

# Module-level documentation
__doc_addendum__ = """

## Quick Start

```python
# RECOMMENDED: Use production classifier
from varidex.core.classifier import ACMGClassifier

classifier = ACMGClassifier()
result = classifier.classify_variant(variant)
```

## Version Information

- **Production:** ACMGClassifier (engine.py)
- **Experimental:** ACMGClassifierV7 (engine_v7.py), ACMGClassifierV8 (engine_v8.py)

See `VERSION_HISTORY.md` for detailed comparison.

## Flags

- `HAS_V7`: True if ACMGClassifierV7 is available
- `HAS_V8`: True if ACMGClassifierV8 is available
"""

__doc__ = __doc__ + __doc_addendum__ if __doc__ else __doc_addendum__
