"""Standalone mock models for reporting module (no external dependencies)."""
from dataclasses import dataclass
from typing import Optional

@dataclass
class AnnotatedVariant:
    """Mock AnnotatedVariant for reporting (self-contained)."""
    chr: str
    pos: int
    ref: str
    alt: str
    acmg_class: str = "VUS"
    gnomad_af: Optional[float] = None

# Re-export for backward compatibility
Variant = AnnotatedVariant
