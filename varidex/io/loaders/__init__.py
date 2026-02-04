"""
VariDex IO Loaders - Main entry points
"""

from .clinvar import load_clinvar_file
from .vcfloader import load_vcf, load_vcf_chunked

# user.py doesn't have load_user_variants - skipping

__all__ = ["load_vcf", "load_vcf_chunked", "load_clinvar_file"]
