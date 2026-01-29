"""
VariDex IO Loaders Module
==========================
Data loading utilities for ClinVar and user genome files.

v7.0.2: Uses matching_improved.py with genotype verification
"""

# Lazy loading to avoid circular imports
__all__ = [
    "load_clinvar_file",
    "load_user_file",
    "load_vcf_file",
    "match_variants_hybrid",
]


def load_clinvar_file(*args, **kwargs):
    """Load ClinVar data file. Lazy import wrapper."""
    from varidex.io.loaders.clinvar import load_clinvar_file as _load

    return _load(*args, **kwargs)


def load_user_file(*args, **kwargs):
    """Load user genome file. Lazy import wrapper."""
    from varidex.io.loaders.user import load_user_file as _load

    return _load(*args, **kwargs)


def load_vcf_file(*args, **kwargs):
    """
    Load VCF format file.

    Args:
        filepath: Path to VCF file
        **kwargs: Additional arguments

    Returns:
        Loaded variant data
    """
    # This is a wrapper that can load VCF files from either ClinVar or user sources
    from varidex.io.loaders.clinvar import load_clinvar_file

    # Attempt to load as ClinVar VCF
    try:
        return load_clinvar_file(*args, **kwargs)
    except Exception:
        # If that fails, try user file loader
        from varidex.io.loaders.user import load_user_file

        return load_user_file(*args, **kwargs)


def match_variants_hybrid(*args, **kwargs):
    """Match variants using IMPROVED hybrid strategy with genotype verification."""
    from varidex.io.matching_improved import match_variants_hybrid as _match  # ✅ NEW

    return _match(*args, **kwargs)
