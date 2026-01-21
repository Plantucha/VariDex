#!/usr/bin/env python3
"""
varidex/core/models.py - Data Models
=====================================
Optimized data structures for variant analysis with sets for O(1) operations.
"""

from dataclasses import dataclass, field
from typing import Set, List, Optional
from datetime import datetime


@dataclass
class ACMGEvidenceSet:
    """
    Complete set of ACMG evidence codes for a variant (OPTIMIZED).

    Uses sets for O(1) operations and auto-deduplication.
    """
    # Pathogenic evidence (sets for optimization)
    pvs: Set[str] = field(default_factory=set)  # Very Strong
    ps: Set[str] = field(default_factory=set)   # Strong
    pm: Set[str] = field(default_factory=set)   # Moderate
    pp: Set[str] = field(default_factory=set)   # Supporting

    # Benign evidence (sets for optimization)
    ba: Set[str] = field(default_factory=set)   # Stand-alone
    bs: Set[str] = field(default_factory=set)   # Strong
    bp: Set[str] = field(default_factory=set)   # Supporting

    # Conflicts (set for auto-deduplication)
    conflicts: Set[str] = field(default_factory=set)

    def all_pathogenic(self) -> Set[str]:
        """Get all pathogenic evidence codes (O(1) set union)."""
        return self.pvs | self.ps | self.pm | self.pp

    def all_benign(self) -> Set[str]:
        """Get all benign evidence codes (O(1) set union)."""
        return self.ba | self.bs | self.bp

    def has_conflict(self) -> bool:
        """
        Check if both pathogenic and benign evidence present (OPTIMIZED).

        O(1) boolean checks instead of list creation.
        """
        has_pathogenic = bool(self.pvs or self.ps or self.pm or self.pp)
        has_benign = bool(self.ba or self.bs or self.bp)
        return has_pathogenic and has_benign

    def summary(self) -> str:
        """Get human-readable summary."""
        parts = []
        if self.pvs: parts.append(f"PVS:{len(self.pvs)}")
        if self.ps: parts.append(f"PS:{len(self.ps)}")
        if self.pm: parts.append(f"PM:{len(self.pm)}")
        if self.pp: parts.append(f"PP:{len(self.pp)}")
        if self.ba: parts.append(f"BA:{len(self.ba)}")
        if self.bs: parts.append(f"BS:{len(self.bs)}")
        if self.bp: parts.append(f"BP:{len(self.bp)}")
        return " | ".join(parts) if parts else "No evidence"

    def __str__(self):
        return self.summary()


@dataclass
class VariantData:
    """Complete information for a single genetic variant"""

    # Core identification
    rsid: str
    chromosome: str
    position: str

    # Genotype information
    genotype: str
    normalized_genotype: str = ''
    genotype_class: str = ''
    zygosity: str = ''

    # Reference and alternate alleles
    ref_allele: str = ''
    alt_allele: str = ''

    # ClinVar annotation
    gene: str = ''
    clinical_sig: str = ''
    review_status: str = ''
    num_submitters: int = 0
    variant_type: str = ''
    molecular_consequence: str = ''

    # Classification results
    acmg_evidence: ACMGEvidenceSet = field(default_factory=ACMGEvidenceSet)
    acmg_classification: str = ''
    confidence_level: str = ''

    # Quality metrics
    star_rating: int = 0
    conflict_details: List[str] = field(default_factory=list)

    # Metadata
    _processed_timestamp: Optional[str] = field(default=None, repr=False)

    @property
    def processed_timestamp(self) -> str:
        """Lazy timestamp generation."""
        if self._processed_timestamp is None:
            self._processed_timestamp = datetime.now().isoformat()
        return self._processed_timestamp

    @processed_timestamp.setter
    def processed_timestamp(self, value: Optional[str]):
        """Allow explicit timestamp setting."""
        self._processed_timestamp = value

    @property
    def has_conflicts(self) -> bool:
        """Check for conflicts in ACMG evidence or manual conflict details."""
        acmg_conflict = self.acmg_evidence.has_conflict() if self.acmg_evidence else False
        manual_conflict = len(self.conflict_details) > 0
        return acmg_conflict or manual_conflict

    def is_pathogenic(self) -> bool:
        """Check if variant is pathogenic or likely pathogenic."""
        return self.acmg_classification in ['Pathogenic', 'Likely Pathogenic']

    def needs_clinical_review(self) -> bool:
        """Check if variant needs clinical review."""
        return (self.is_pathogenic() or 
                self.has_conflicts or 
                (self.acmg_classification == 'Uncertain Significance' and self.star_rating >= 2))

    def add_conflict(self, detail: str):
        """Add conflict detail."""
        if detail and detail not in self.conflict_details:
            self.conflict_details.append(detail)

    def get_variant_notation(self) -> str:
        """Get standard variant notation (chr:pos:ref>alt)."""
        if self.ref_allele and self.alt_allele:
            return f"{self.chromosome}:{self.position}:{self.ref_allele}>{self.alt_allele}"
        return f"{self.chromosome}:{self.position}"

    def is_protein_altering(self) -> bool:
        """Check if variant alters protein sequence."""
        protein_altering = [
            'missense', 'nonsense', 'frameshift', 
            'inframe_insertion', 'inframe_deletion',
            'start_lost', 'stop_lost', 'stop_gained'
        ]
        return any(alt in self.molecular_consequence.lower() 
                  for alt in protein_altering)

    def summary_dict(self) -> dict:
        """Get dictionary summary for logging/export."""
        summary = {
            'rsid': self.rsid,
            'gene': self.gene,
            'genotype': self.genotype,
            'zygosity': self.zygosity,
            'classification': self.acmg_classification,
            'confidence': self.confidence_level,
            'evidence': self.acmg_evidence.summary(),
            'stars': self.star_rating,
            'conflicts': self.has_conflicts
        }
        if self.ref_allele and self.alt_allele:
            summary['variant_notation'] = self.get_variant_notation()
        return summary

    def __str__(self):
        notation = f" ({self.get_variant_notation()})" if self.ref_allele else ""
        return (f"Variant({self.rsid} in {self.gene}{notation}: {self.genotype} -> "
                f"{self.acmg_classification} [{self.acmg_evidence.summary()}])")


@dataclass
class PipelineState:
    """Track pipeline execution state for checkpointing."""
    stage: str = 'initialized'
    variants_loaded: int = 0
    variants_matched: int = 0
    variants_classified: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    _start_time: Optional[str] = field(default=None, repr=False)

    @property
    def start_time(self) -> str:
        """Lazy timestamp generation."""
        if self._start_time is None:
            self._start_time = datetime.now().isoformat()
        return self._start_time

    @start_time.setter
    def start_time(self, value: Optional[str]):
        """Allow explicit timestamp setting."""
        self._start_time = value

    def add_error(self, error: str):
        """Add error to state."""
        self.errors.append(f"{datetime.now().isoformat()}: {error}")

    def add_warning(self, warning: str):
        """Add warning to state."""
        self.warnings.append(f"{datetime.now().isoformat()}: {warning}")

    def summary(self) -> str:
        """Get summary string."""
        return (f"Stage: {self.stage} | "
                f"Loaded: {self.variants_loaded} | "
                f"Matched: {self.variants_matched} | "
                f"Classified: {self.variants_classified} | "
                f"Errors: {len(self.errors)} | "
                f"Warnings: {len(self.warnings)}")


if __name__ == "__main__":
    print("=" * 80)
    print("MODELS MODULE - VERIFICATION")
    print("=" * 80)

    # Test ACMGEvidenceSet with sets
    evidence = ACMGEvidenceSet()
    evidence.pvs.add('PVS1')
    evidence.pvs.add('PVS1')  # Should auto-deduplicate
    evidence.pm.add('PM2')
    evidence.pp.add('PP3')

    print(f"\n✓ ACMGEvidenceSet created with sets")
    print(f"  - Pathogenic codes: {evidence.all_pathogenic()}")
    print(f"  - Summary: {evidence.summary()}")
    print(f"  - Auto-deduplication: {len(evidence.pvs) == 1}")
    assert len(evidence.pvs) == 1, "PVS1 should be deduplicated"

    # Test optimized has_conflict
    print(f"\n✓ Testing optimized has_conflict()")
    print(f"  - Initial: {evidence.has_conflict()}")
    assert not evidence.has_conflict(), "Should be False with only pathogenic"

    evidence.bp.add('BP1')
    print(f"  - After adding BP1: {evidence.has_conflict()}")
    assert evidence.has_conflict(), "Should be True with mixed evidence"

    print("\n✅ All optimized models validated successfully")
    print("=" * 80)
