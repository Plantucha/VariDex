"""
varidex/integrations/gnomad/__init__.py v6.4.0-dev

gnomAD population frequency integration for ACMG criteria PM2, BA1, BS1.

Development version - not for production use.
"""

from .query import GnomADQuerier, query_allele_frequency
from .config import GnomADConfig

__all__ = ["GnomADQuerier", "query_allele_frequency", "GnomADConfig"]
