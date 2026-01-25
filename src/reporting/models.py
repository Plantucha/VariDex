"""Reporting models - self-contained dataclass."""
from dataclasses import dataclass
from typing import Optional

@dataclass
class AnnotatedVariant:
    chr: str
    pos: int  
    ref: str
    alt: str
    acmg_class: str = "VUS"
    gnomad_af: Optional[float] = None
