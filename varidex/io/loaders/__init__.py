"""
VariDex IO Loaders - Main entry points
"""

from .vcfloader import load_vcf, load_vcf_chunked
from .clinvar import load_clinvar_file
# user.py doesn't have load_user_variants - skipping

__all__ = ['load_vcf', 'load_vcf_chunked', 'load_clinvar_file']
