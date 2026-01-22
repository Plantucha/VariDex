"""
ACMG Variant Classifier
========================

Production-grade ACMG 2015 variant classification system.

Modules:
    - engine: ACMGClassifier implementation
    - config: ACMGConfig and presets (strict/balanced/lenient)
    - metrics: ACMGMetrics for production monitoring
    - rules: Evidence combination rules

Usage:
    from varidex.core.classifier import ACMGClassifier, combine_evidence

    classifier = ACMGClassifier()
    result = classifier.classify(variant)
"""

from varidex.version import get_version

__version__ = get_version("core.classifier")

# Import core components
try:
    pass

    __all__ = [
        "ACMGClassifier",
        "ACMGConfig",
        "get_preset",
        "ACMGMetrics",
        "combine_evidence",
        "validate_evidence_combination",
    ]
except ImportError:
    # Graceful degradation if dependencies missing
    import warnings

    warnings.warn("Could not import classifier components: {e}")
    __all__ = []
