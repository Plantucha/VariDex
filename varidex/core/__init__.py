"""
VariDex Core Module
===================

Core functionality for ACMG variant classification.

Components:
    - config: Configuration constants and gene lists
    - models: Data models (VariantData, ACMGEvidenceSet)
    - genotype: Genotype normalization and zygosity detection
    - schema: DataFrame schema validation
    - classifier: ACMG classification engine
"""

from varidex.version import get_version

__version__ = get_version("core")
__all__: list[str] = []
