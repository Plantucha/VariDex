"""varidex/core/classifier - ACMG Variant Classifier

Production-grade ACMG 2015 variant classification system.

Modules:
    - engine: ACMGClassifier main implementation (v6.4.0)
    - engine_v7: ACMGClassifierV7 with gnomAD integration
    - engine_v8: ACMGClassifierV8 with computational predictions
    - config: ACMGConfig and presets
    - evidence_utils: Utility functions for evidence assignment
    - evidence_assignment: Evidence code assignment logic

Usage:
    from varidex.core.classifier import ACMGClassifier

    classifier = ACMGClassifier()
    classification, confidence, evidence, duration = classifier.classify_variant(variant)

Refactored in v6.4.0:
    - Split engine.py into 3 files for better modularity
    - All files now under 500-line limit
    - Maintained backward compatibility
"""

from typing import List
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
try:
    from .engine_v7 import ACMGClassifierV7

    HAS_V7: bool = True
except ImportError:
    HAS_V7 = False

try:
    from .engine_v8 import ACMGClassifierV8

    HAS_V8: bool = True
except ImportError:
    HAS_V8 = False

__all__: List[str] = [
    # Main classifier
    "ACMGClassifier",
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
]

# Add advanced classifiers if available
if HAS_V7:
    __all__.append("ACMGClassifierV7")
if HAS_V8:
    __all__.append("ACMGClassifierV8")
