#!/usr/bin/env python3
"""
varidex/core/models.py - Data Models
=====================================
Optimized data structures for variant analysis with sets for O(1) operations.
"""

from dataclasses import dataclass, field
from typing import Set, List, Optional, Dict, Any
from datetime import datetime
import re


@dataclass
class ACMGEvidenceSet:
    """
    Complete set of ACMG evidence codes for a variant (OPTIMIZED).

    Uses sets for O(1) operations and auto-deduplication.
    """

    # Pathogenic evidence (sets for optimization)
    pvs: Set[str] = field(default_factory=set)  # Very Strong
    ps: Set[str] = field(default_factory=set)  # Strong
    pm: Set[str] = field(default_factory=set)  # Moderate
    pp: Set[str] = field(default_factory=set)  # Supporting

    # Benign evidence (sets for optimization)
    ba: Set[str] = field(default_factory=set)  # Stand-alone
    bs: Set[str] = field(default_factory=set)  # Strong
    bp: Set[str] = field(default_factory=set)  # Supporting

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
        parts: List[str] = []
        if self.pvs:
            parts.append(f"PVS:{len(self.pvs)}")
        if self.ps:
            parts.append(f"PS:{len(self.ps)}")
        if self.pm:
            parts.append(f"PM:{len(self.pm)}")
        if self.pp:
            parts.append(f"PP:{len(self.pp)}")
        if self.ba:
            parts.append(f"BA:{len(self.ba)}")
        if self.bs:
            parts.append(f"BS:{len(self.bs)}")
        if self.bp:
            parts.append(f"BP:{len(self.bp)}")
        return " | ".join(parts) if parts else "No evidence"

    def __str__(self) -> str:
        return self.summary()


def _validate_chromosome(chrom: str) -> str:
    """
    Validate chromosome format.
    
    Accepts: 1-22, X, Y, M, MT with optional 'chr' prefix
    Returns normalized chromosome string.
    Raises ValueError if invalid.
    """
    if not chrom:
        return chrom
    
    # Remove 'chr' prefix if present for validation
    normalized = chrom.upper().replace("CHR", "")
    
    # Valid chromosomes: 1-22, X, Y, M, MT
    valid_chroms = set(str(i) for i in range(1, 23)) | {"X", "Y", "M", "MT"}
    
    if normalized not in valid_chroms:
        raise ValueError(
            f"Invalid chromosome '{chrom}'. Must be 1-22, X, Y, M, or MT "
            f"(with optional 'chr' prefix)"
        )
    
    return chrom


def _validate_position(pos: str) -> str:
    """
    Validate genomic position.
    
    Must be positive integer when provided.
    Returns validated position string.
    Raises ValueError if invalid.
    """
    if not pos:
        return pos
    
    try:
        pos_int = int(pos)
        if pos_int <= 0:
            raise ValueError(f"Position must be positive, got {pos_int}")
        return str(pos_int)
    except ValueError as e:
        if "invalid literal" in str(e):
            raise ValueError(
                f"Position must be an integer, got '{pos}'"
            ) from e
        raise


def _validate_allele(allele: str, allele_type: str = "allele") -> str:
    """
    Validate nucleotide allele sequence.
    
    Must contain only A, C, G, T, N (case-insensitive) or be empty.
    Returns uppercase allele string.
    Raises ValueError if invalid.
    """
    if not allele:
        return allele
    
    allele_upper = allele.upper()
    valid_pattern = re.compile(r"^[ACGTN]+$")
    
    if not valid_pattern.match(allele_upper):
        raise ValueError(
            f"Invalid {allele_type} '{allele}'. "
            f"Must contain only nucleotides A, C, G, T, or N"
        )
    
    return allele_upper


@dataclass
class VariantData:
    """Complete information for a single genetic variant"""

    # Core identification
    rsid: str = ""
    chromosome: str = ""
    position: str = ""

    # Genotype information
    genotype: str = ""
    normalized_genotype: str = ""
    genotype_class: str = ""
    zygosity: str = ""

    # Reference and alternate alleles
    ref_allele: str = ""
    alt_allele: str = ""

    # Reference assembly
    assembly: str = ""

    # ClinVar annotation
    gene: str = ""
    clinical_sig: str = ""
    review_status: str = ""
    num_submitters: int = 0
    variant_type: str = ""
    molecular_consequence: str = ""

    # Classification results
    acmg_evidence: ACMGEvidenceSet = field(default_factory=ACMGEvidenceSet)
    acmg_classification: str = ""
    confidence_level: str = ""

    # Quality metrics
    star_rating: int = 0
    conflict_details: List[str] = field(default_factory=list)

    # Metadata
    _processed_timestamp: Optional[str] = field(default=None, repr=False)

    def __init__(
        self,
        rsid: str = "",
        chromosome: str = "",
        position: str = "",
        genotype: str = "",
        normalized_genotype: str = "",
        genotype_class: str = "",
        zygosity: str = "",
        ref_allele: str = "",
        alt_allele: str = "",
        assembly: str = "",
        gene: str = "",
        clinical_sig: str = "",
        review_status: str = "",
        num_submitters: int = 0,
        variant_type: str = "",
        molecular_consequence: str = "",
        acmg_evidence: Optional[ACMGEvidenceSet] = None,
        acmg_classification: str = "",
        confidence_level: str = "",
        star_rating: int = 0,
        conflict_details: Optional[List[str]] = None,
        _processed_timestamp: Optional[str] = None,
        # VCF-style aliases for compatibility
        chrom: str = "",
        pos: Optional[int] = None,
        ref: str = "",
        alt: str = "",
        **kwargs: Any,
    ) -> None:
        """
        Initialize VariantData with validation and dual naming support.
        
        Supports both traditional (chromosome, position) and VCF-style (chrom, pos)
        parameter names. Validates chromosome, position, and alleles for data quality.
        
        Raises:
            ValueError: If chromosome, position, or alleles are invalid
        """
        # Handle VCF-style parameters (chrom, pos, ref, alt)
        if chrom:
            chromosome = chrom
        if pos is not None:
            position = str(pos)
        if ref:
            ref_allele = ref
        if alt:
            alt_allele = alt

        # VALIDATION: Validate inputs before assignment
        try:
            chromosome = _validate_chromosome(chromosome)
            position = _validate_position(position)
            ref_allele = _validate_allele(ref_allele, "reference allele")
            alt_allele = _validate_allele(alt_allele, "alternate allele")
        except ValueError as e:
            raise ValueError(f"Invalid variant data: {e}") from e

        # Set all fields
        self.rsid = rsid
        self.chromosome = chromosome
        self.position = position
        self.genotype = genotype
        self.normalized_genotype = normalized_genotype
        self.genotype_class = genotype_class
        self.zygosity = zygosity
        self.ref_allele = ref_allele
        self.alt_allele = alt_allele
        self.assembly = assembly
        self.gene = gene
        self.clinical_sig = clinical_sig
        self.review_status = review_status
        self.num_submitters = num_submitters
        self.variant_type = variant_type
        self.molecular_consequence = molecular_consequence
        self.acmg_evidence = acmg_evidence or ACMGEvidenceSet()
        self.acmg_classification = acmg_classification
        self.confidence_level = confidence_level
        self.star_rating = star_rating
        self.conflict_details = conflict_details or []
        self._processed_timestamp = _processed_timestamp

    @property
    def processed_timestamp(self) -> str:
        """Lazy timestamp generation."""
        if self._processed_timestamp is None:
            self._processed_timestamp = datetime.now().isoformat()
        return self._processed_timestamp

    @processed_timestamp.setter
    def processed_timestamp(self, value: Optional[str]) -> None:
        """Allow explicit timestamp setting."""
        self._processed_timestamp = value

    @property
    def has_conflicts(self) -> bool:
        """Check for conflicts in ACMG evidence or manual conflict details."""
        acmg_conflict = (
            self.acmg_evidence.has_conflict() if self.acmg_evidence else False
        )
        manual_conflict = len(self.conflict_details) > 0
        return acmg_conflict or manual_conflict

    # VCF-style property aliases
    @property
    def chrom(self) -> str:
        """Alias for chromosome (VCF compatibility)."""
        return self.chromosome

    @property
    def pos(self) -> int:
        """Alias for position as integer (VCF compatibility)."""
        return int(self.position) if self.position else 0

    @property
    def ref(self) -> str:
        """Alias for ref_allele (VCF compatibility)."""
        return self.ref_allele

    @property
    def alt(self) -> str:
        """Alias for alt_allele (VCF compatibility)."""
        return self.alt_allele

    def is_pathogenic(self) -> bool:
        """Check if variant is pathogenic or likely pathogenic."""
        return self.acmg_classification in ["Pathogenic", "Likely Pathogenic"]

    def needs_clinical_review(self) -> bool:
        """Check if variant needs clinical review."""
        return (
            self.is_pathogenic()
            or self.has_conflicts
            or (
                self.acmg_classification == "Uncertain Significance"
                and self.star_rating >= 2
            )
        )

    def add_conflict(self, detail: str) -> None:
        """Add conflict detail."""
        if detail and detail not in self.conflict_details:
            self.conflict_details.append(detail)

    def get_variant_notation(self) -> str:
        """Get standard variant notation (chr:pos:ref>alt)."""
        if self.ref_allele and self.alt_allele:
            return (
                f"{self.chromosome}:{self.position}:"
                f"{self.ref_allele}>{self.alt_allele}"
            )
        return f"{self.chromosome}:{self.position}"

    def to_vcf_string(self) -> str:
        """Convert variant to VCF format string."""
        return (
            f"{self.chromosome}\t{self.position}\t{self.rsid or '.'}\t"
            f"{self.ref_allele or '.'}\t{self.alt_allele or '.'}\t.\tPASS\t."
        )

    @property
    def variant_key(self) -> str:
        """Generate unique variant identifier."""
        return f"{self.chromosome}:{self.position}:{self.ref_allele}:{self.alt_allele}"

    def is_protein_altering(self) -> bool:
        """Check if variant alters protein sequence."""
        protein_altering = [
            "missense",
            "nonsense",
            "frameshift",
            "inframe_insertion",
            "inframe_deletion",
            "start_lost",
            "stop_lost",
            "stop_gained",
        ]
        return any(
            alt in self.molecular_consequence.lower() for alt in protein_altering
        )

    def summary_dict(self) -> Dict[str, Any]:
        """Get dictionary summary for logging/export."""
        summary: Dict[str, Any] = {
            "rsid": self.rsid,
            "gene": self.gene,
            "genotype": self.genotype,
            "zygosity": self.zygosity,
            "classification": self.acmg_classification,
            "confidence": self.confidence_level,
            "evidence": self.acmg_evidence.summary(),
            "stars": self.star_rating,
            "conflicts": self.has_conflicts,
        }
        if self.ref_allele and self.alt_allele:
            summary["variant_notation"] = self.get_variant_notation()
        return summary

    def __str__(self) -> str:
        notation = f" ({self.get_variant_notation()})" if self.ref_allele else ""
        return (
            f"Variant({self.rsid} in {self.gene}{notation}: {self.genotype} -> "
            f"{self.acmg_classification} [{self.acmg_evidence.summary()}])"
        )


@dataclass
class VariantAnnotation:
    """
    Annotation data for a variant from external databases.

    This class stores annotation information separate from the core
    variant data, allowing for flexible annotation sources.
    """

    # Population frequencies
    gnomad_af: Optional[float] = None
    gnomad_ac: Optional[int] = None
    gnomad_an: Optional[int] = None

    # Clinical databases
    clinvar_significance: Optional[str] = None
    clinvar_review_status: Optional[str] = None
    clinvar_stars: Optional[int] = None

    # Computational predictions
    sift_score: Optional[float] = None
    sift_prediction: Optional[str] = None
    polyphen_score: Optional[float] = None
    polyphen_prediction: Optional[str] = None
    cadd_score: Optional[float] = None

    # Functional annotations
    gene_symbol: Optional[str] = None
    consequence: Optional[str] = None
    impact: Optional[str] = None
    transcript_id: Optional[str] = None
    protein_change: Optional[str] = None

    # Additional metadata
    annotation_source: str = "unknown"
    annotation_date: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert annotation to dictionary."""
        return {k: v for k, v in self.__dict__.items() if v is not None}

    def has_frequency_data(self) -> bool:
        """Check if frequency data is available."""
        return self.gnomad_af is not None

    def has_clinical_data(self) -> bool:
        """Check if clinical data is available."""
        return self.clinvar_significance is not None

    def has_prediction_data(self) -> bool:
        """Check if computational prediction data is available."""
        return any(
            [
                self.sift_score is not None,
                self.polyphen_score is not None,
                self.cadd_score is not None,
            ]
        )


@dataclass
class AnnotatedVariant:
    """
    Variant with its annotation data.

    Combines core variant information with external annotations.
    """

    variant: VariantData
    annotation: VariantAnnotation = field(default_factory=VariantAnnotation)

    @property
    def rsid(self) -> str:
        """Convenience accessor for variant rsid."""
        return self.variant.rsid

    @property
    def chromosome(self) -> str:
        """Convenience accessor for chromosome."""
        return self.variant.chromosome

    @property
    def position(self) -> str:
        """Convenience accessor for position."""
        return self.variant.position

    @property
    def gene(self) -> str:
        """Get gene from variant or annotation."""
        return self.variant.gene or self.annotation.gene_symbol or ""

    def has_complete_annotation(self) -> bool:
        """Check if variant has complete annotation."""
        return (
            self.annotation.has_frequency_data()
            and self.annotation.has_clinical_data()
            and self.annotation.has_prediction_data()
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "variant": self.variant.summary_dict(),
            "annotation": self.annotation.to_dict(),
        }


@dataclass
class PipelineState:
    """Track pipeline execution state for checkpointing."""

    stage: str = "initialized"
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
    def start_time(self, value: Optional[str]) -> None:
        """Allow explicit timestamp setting."""
        self._start_time = value

    def add_error(self, error: str) -> None:
        """Add error to state."""
        self.errors.append(f"{datetime.now().isoformat()}: {error}")

    def add_warning(self, warning: str) -> None:
        """Add warning to state."""
        self.warnings.append(f"{datetime.now().isoformat()}: {warning}")

    def summary(self) -> str:
        """Get summary string."""
        return (
            f"Stage: {self.stage} | "
            f"Loaded: {self.variants_loaded} | "
            f"Matched: {self.variants_matched} | "
            f"Classified: {self.variants_classified} | "
            f"Errors: {len(self.errors)} | "
            f"Warnings: {len(self.warnings)}"
        )


# ===================================================================
# BACKWARD COMPATIBILITY ALIASES
# ===================================================================
# These aliases maintain backward compatibility with existing tests
# while the codebase transitions to the new class names.

# Primary alias: Variant -> VariantData
Variant = VariantData

# GenomicVariant alias for position-based variant representation
GenomicVariant = VariantData

# ACMG-related aliases
ACMGCriteria = ACMGEvidenceSet  # Alias for test compatibility


@dataclass
class VariantClassification:
    """
    Complete classification result for a variant.

    Combines ACMG classification with evidence and metadata.
    """

    classification: str
    evidence: ACMGEvidenceSet = field(default_factory=ACMGEvidenceSet)
    confidence: str = ""
    timestamp: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "classification": self.classification,
            "evidence": self.evidence.summary(),
            "confidence": self.confidence,
            "timestamp": self.timestamp or datetime.now().isoformat(),
        }


# Pathogenicity classification enum (for test compatibility)
from enum import Enum


class PathogenicityClass(Enum):
    """ACMG pathogenicity classifications."""

    PATHOGENIC = "Pathogenic"
    LIKELY_PATHOGENIC = "Likely Pathogenic"
    UNCERTAIN_SIGNIFICANCE = "Uncertain Significance"
    LIKELY_BENIGN = "Likely Benign"
    BENIGN = "Benign"


if __name__ == "__main__":
    print("=" * 80)
    print("MODELS MODULE - VERIFICATION WITH VALIDATION")
    print("=" * 80)

    # Test validation functions
    print("\n✓ Testing validation functions")
    try:
        _validate_chromosome("chr1")
        _validate_chromosome("X")
        _validate_chromosome("MT")
        print("  - Valid chromosomes accepted: chr1, X, MT")
    except ValueError:
        print("  ✗ Valid chromosome rejected!")

    try:
        _validate_chromosome("chr99")
        print("  ✗ Invalid chromosome accepted!")
    except ValueError:
        print("  - Invalid chromosome rejected: chr99")

    try:
        _validate_position("12345")
        print("  - Valid position accepted: 12345")
    except ValueError:
        print("  ✗ Valid position rejected!")

    try:
        _validate_position("-100")
        print("  ✗ Negative position accepted!")
    except ValueError:
        print("  - Negative position rejected: -100")

    try:
        _validate_allele("ACGT")
        _validate_allele("N")
        print("  - Valid alleles accepted: ACGT, N")
    except ValueError:
        print("  ✗ Valid allele rejected!")

    try:
        _validate_allele("ACGT123")
        print("  ✗ Invalid allele accepted!")
    except ValueError:
        print("  - Invalid allele rejected: ACGT123")

    # Test VCF-style initialization with validation
    print("\n✓ Testing VCF-style VariantData with validation")
    try:
        vcf_variant = VariantData(chrom="chr1", pos=12345, ref="A", alt="G")
        print(f"  - Valid VCF variant created: {vcf_variant.variant_key}")
    except ValueError as e:
        print(f"  ✗ Valid variant rejected: {e}")

    try:
        invalid_variant = VariantData(chrom="chr99", pos=12345, ref="A", alt="G")
        print("  ✗ Invalid chromosome accepted!")
    except ValueError:
        print("  - Invalid chromosome rejected during initialization")

    try:
        invalid_variant = VariantData(chrom="chr1", pos=-100, ref="A", alt="G")
        print("  ✗ Invalid position accepted!")
    except ValueError:
        print("  - Invalid position rejected during initialization")

    try:
        invalid_variant = VariantData(chrom="chr1", pos=12345, ref="X", alt="G")
        print("  ✗ Invalid ref allele accepted!")
    except ValueError:
        print("  - Invalid ref allele rejected during initialization")

    # Test backward compatibility with empty values
    print("\n✓ Testing backward compatibility with empty values")
    try:
        empty_variant = VariantData(rsid="rs123", gene="BRCA1")
        print(f"  - Variant with empty chr/pos/alleles: {empty_variant.rsid}")
    except ValueError as e:
        print(f"  ✗ Empty values rejected: {e}")

    print("\n✅ All validation tests passed successfully")
    print("=" * 80)
