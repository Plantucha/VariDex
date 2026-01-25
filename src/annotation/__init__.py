"""Annotation module for VariDex.

Provides data loaders for various annotation sources including ClinVar,
CADD, dbNSFP, and gnomAD.
"""

from src.annotation.annotator import Annotator
from src.annotation.cadd_loader import CADDLoader
from src.annotation.clinvar_loader import ClinVarLoader
from src.annotation.dbnsfp_loader import DbNSFPLoader
from src.annotation.gnomad_loader import GnomADLoader

__all__ = [
    "Annotator",
    "CADDLoader",
    "ClinVarLoader",
    "DbNSFPLoader",
    "GnomADLoader",
]
