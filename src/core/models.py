"""Core data models for VariDex variant representation."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class VariantData:
    """
    Represents a genomic variant with VCF-standard fields.

    Attributes:
        chrom: Chromosome identifier
        pos: Position on the chromosome (1-based)
        ref: Reference allele
        alt: Alternate allele
        qual: Quality score (optional)
        filter: Filter status (optional)
        info: Additional variant information dictionary
    """

    chrom: str
    pos: int
    ref: str
    alt: str
    qual: Optional[float] = None
    filter: Optional[str] = None
    info: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate variant data after initialization."""
        if not self.chrom:
            raise ValueError("Chromosome identifier cannot be empty")
        if self.pos < 1:
            raise ValueError(f"Position must be >= 1, got {self.pos}")
        if not self.ref:
            raise ValueError("Reference allele cannot be empty")
        if not self.alt:
            raise ValueError("Alternate allele cannot be empty")

    def to_vcf_string(self) -> str:
        """Convert variant to VCF format string."""
        qual_str = str(self.qual) if self.qual is not None else "."
        filter_str = self.filter if self.filter else "PASS"
        info_str = (
            ";".join(f"{k}={v}" for k, v in self.info.items())
            if self.info
            else "."
        )
        return f"{self.chrom}\t{self.pos}\t.\t{self.ref}\t{self.alt}\t{qual_str}\t{filter_str}\t{info_str}"

    @property
    def variant_key(self) -> str:
        """Generate unique variant identifier."""
        return f"{self.chrom}:{self.pos}:{self.ref}:{self.alt}"
