"""
VariDex I/O Module
==================

Input/output operations for genomic data.

Components:
    - loaders: ClinVar and user genome data loaders
    - validators: File validation and security checks
    - validators_advanced: Extended validation with caching
    - matching: Variant matching strategies (rsID, coordinates, hybrid)

Usage:
    from varidex.io.loaders import load_clinvar_file
    from varidex.io.matching import match_variants_hybrid
"""

from varidex.version import get_version

__version__ = get_version("io")
__all__: list[str] = []
