"""
Core data models for VariDex variant analysis system.

This module provides dataclass-based models for genetic variants, annotations,
and ACMG classifications with comprehensive validation.

Development version - Black formatted, PEP 8 compliant.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union
import dataclasses

from varidex.core.exceptions import ValidationError


# ============================================================================
# ACMG Evidence Models
# ============================================================================


@dataclass
class ACMGEvidence:
    """Single piece of ACMG evidence with code and strength."""

    code: str
    strength: str
    description: str = ""

    def __post_init__(self):
        """Validate evidence after initialization."""
        valid_strengths = {
            "very_strong",
            "strong",
            "moderate",
            "supporting",
            "stand_alone",
        }
        if self.strength not in valid_strengths:
            raise ValidationError(
                f"Invalid strength '{self.strength}'. "
                f"Must be one of: {valid_strengths}"
            )


@dataclass
class ACMGEvidenceSet:
    """Collection of ACMG evidence codes for variant classification."""

    pathogenic: List[ACMGEvidence] = field(default_factory=list)
    benign: List[ACMGEvidence] = field(default_factory=list)

    def add_pathogenic(self, code: str, strength: str, description: str = ""):
        """Add pathogenic evidence."""
        self.pathogenic.append(ACMGEvidence(code, strength, description))

    def add_benign(self, code: str, strength: str, description: str = ""):
        """Add benign evidence."""
        self.benign.append(ACMGEvidence(code, strength, description))

    def summary(self) -> Dict[str, List[str]]:
        """Get summary of evidence codes."""
        return {
            "pathogenic": [e.code for e in self.pathogenic],
            "benign": [e.code for e in self.benign],
        }

    def has_evidence(self) -> bool:
        """Check if any evidence exists."""
        return len(self.pathogenic) > 0 or len(self.benign) > 0


# ============================================================================
# Validation Functions
# ============================================================================


def _validate_chromosome(chrom: Union[str, int]) -> str:
    """
    Validate chromosome identifier.

    Args:
        chrom: Chromosome identifier (e.g., 'chr1', '1', 'chrX', 'chrM')

    Returns:
        Validated chromosome string

    Raises:
        ValidationError: If chromosome format is invalid
    """
    if not chrom and chrom != 0:
        raise ValidationError("Chromosome cannot be empty")

    # Convert to string and normalize
    chrom_str = str(chrom).strip().upper()
    if chrom_str.startswith("CHR"):
        chrom_part = chrom_str[3:]
    else:
        chrom_part = chrom_str

    # Valid chromosome identifiers: 1-22, X, Y, M/MT (mitochondrial)
    valid_chroms = set(map(str, range(1, 23))) | {"X", "Y", "M", "MT"}

    if chrom_part not in valid_chroms:
        raise ValidationError(
            f"Invalid chromosome '{chrom}'. Must be 1-22, X, Y, or M/MT"
        )

    # Return normalized format with 'chr' prefix
    return f"chr{chrom_part}"


def _validate_position(position: Union[str, int]) -> int:
    """
    Validate genomic position.

    Args:
        position: Genomic position (must be positive integer)

    Returns:
        Validated position as integer

    Raises:
        ValidationError: If position is invalid
    """
    try:
        pos_int = int(position)
    except (ValueError, TypeError) as e:
        raise ValidationError(
            f"Position must be an integer, got '{position}'"
        ) from e

    if pos_int <= 0:
        raise ValidationError(f"Position must be positive, got {pos_int}")

    return pos_int


def _validate_allele(
    allele: str, allele_type: str = "allele", allow_empty: bool = False
) -> str:
    """
    Validate nucleotide allele string.

    Args:
        allele: Nucleotide sequence (A, C, G, T, N, or empty for deletions)
        allele_type: Type of allele for error messages
        allow_empty: Whether empty alleles are allowed (for deletions)

    Returns:
        Validated allele string (uppercase)

    Raises:
        ValidationError: If allele contains invalid characters
    """
    # CRITICAL FIX: Check for empty string explicitly
    if allele == "" or allele is None:
        if not allow_empty:
            raise ValidationError(f"{allele_type.capitalize()} cannot be empty")
        return ""

    allele_upper = allele.upper()
    valid_nucleotides = set("ACGTN")

    for char in allele_upper:
        if char not in valid_nucleotides:
            raise ValidationError(
                f"Invalid {allele_type} '{allele}'. "
                f"Must contain only nucleotides A, C, G, T, or N"
            )

    return allele_upper


# ============================================================================
# Core Variant Models
# ============================================================================


@dataclass
class VariantData:
    """Complete information for a single genetic variant with enhanced features."""

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

    # Quality metrics
    quality_score: float = 0.0
    depth: int = 0
    allele_frequency: float = 0.0

    # Additional annotations
    annotations: Dict[str, Any] = field(default_factory=dict)

    def __init__(self, **kwargs):
        """
        Initialize VariantData with validation.

        Supports keyword arguments for all fields.
        """
        # Extract and validate core fields with proper mapping
        chrom = kwargs.pop("chrom", None) or kwargs.pop("chromosome", "")
        # CRITICAL FIX: Handle pos=0 correctly (can't use 'or' because 0 is falsy)
        pos = kwargs.pop("pos", None) if "pos" in kwargs else kwargs.pop("position", "")
        ref = kwargs.pop("ref", None) if "ref" in kwargs else kwargs.pop("ref_allele", "")
        alt = kwargs.pop("alt", None) if "alt" in kwargs else kwargs.pop("alt_allele", "")

        # Validate if provided
        if chrom:
            chrom = _validate_chromosome(chrom)
            kwargs["chromosome"] = chrom

        if pos or pos == 0:  # CRITICAL: handle pos=0 explicitly
            pos_int = _validate_position(pos)
            kwargs["position"] = str(pos_int)

        # CRITICAL FIX: Always validate alleles if explicitly provided
        if ref is not None:
            ref = _validate_allele(ref, "reference allele", allow_empty=False)
            kwargs["ref_allele"] = ref

        if alt is not None:
            alt = _validate_allele(alt, "alternate allele", allow_empty=False)
            kwargs["alt_allele"] = alt

        # Initialize all fields from kwargs or defaults
        for field_name in self.__dataclass_fields__:
            field_def = self.__dataclass_fields__[field_name]
            if field_name in kwargs:
                setattr(self, field_name, kwargs[field_name])
            elif field_def.default_factory is not dataclasses.MISSING:
                setattr(self, field_name, field_def.default_factory())
            else:
                setattr(self, field_name, field_def.default)

    def to_dict(self) -> Dict[str, Any]:
        """Convert variant to dictionary representation."""
        return {
            "rsid": self.rsid,
            "chromosome": self.chromosome,
            "position": self.position,
            "ref_allele": self.ref_allele,
            "alt_allele": self.alt_allele,
            "genotype": self.genotype,
            "zygosity": self.zygosity,
            "gene": self.gene,
            "clinical_sig": self.clinical_sig,
            "acmg_classification": self.acmg_classification,
            "annotations": self.annotations,
        }

    def get_variant_id(self) -> str:
        """Generate unique variant identifier."""
        return f"{self.chromosome}:{self.position}:{self.ref_allele}:{self.alt_allele}"


class Variant(VariantData):
    """
    Convenience wrapper for VariantData that supports positional arguments.

    This class enables test-friendly syntax:
        Variant("chr1", 12345, "A", "G", annotations={...})

    Which is equivalent to:
        VariantData(chromosome="chr1", position=12345, ref_allele="A", 
                    alt_allele="G", annotations={...})
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize Variant with support for positional arguments.

        Positional argument formats:
        - Variant(chromosome, position, reference, alternate, **kwargs)
        - Variant(**kwargs)

        Examples:
            >>> v1 = Variant("chr1", 12345, "A", "G")
            >>> v2 = Variant("chr1", 12345, "A", "G", annotations={"gene": "BRCA1"})
            >>> v3 = Variant(chromosome="chr1", position=12345, 
            ...              ref_allele="A", alt_allele="G")
        """
        # Handle positional arguments: (chrom, pos, ref, alt)
        if len(args) >= 4:
            kwargs["chrom"] = args[0]
            kwargs["pos"] = args[1]
            kwargs["ref"] = args[2]
            kwargs["alt"] = args[3]
        elif len(args) > 0:
            raise ValidationError(
                f"Variant requires 0 or 4+ positional args, got {len(args)}"
            )

        # Validate and initialize - re-raise ValidationError without wrapping
        super().__init__(**kwargs)

    def __getattribute__(self, name):
        """
        Override attribute access for convenience properties.

        Returns:
            - For 'pos': int position value
            - For 'ref': reference allele string
            - For 'alt': alternate allele string
            - For all others: normal attribute value
        """
        if name == "pos":
            position_str = super().__getattribute__("position")
            return int(position_str) if position_str else 0
        elif name == "ref":
            return super().__getattribute__("ref_allele")
        elif name == "alt":
            return super().__getattribute__("alt_allele")
        return super().__getattribute__(name)


# ============================================================================
# Annotation Models
# ============================================================================


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

    # Conservation scores
    phylop_score: Optional[float] = None
    phastcons_score: Optional[float] = None

    # Additional annotations
    extra_fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert annotation to dictionary."""
        result = {}
        for field_name in self.__dataclass_fields__:
            value = getattr(self, field_name)
            if value is not None:
                result[field_name] = value
        return result


@dataclass
class AnnotatedVariant:
    """
    Variant with its annotation data.

    Combines core variant information with external annotations.
    """

    variant: Variant = field(default_factory=Variant)
    annotation: VariantAnnotation = field(default_factory=VariantAnnotation)

    def __init__(
        self,
        variant: Optional[Variant] = None,
        annotation: Optional[VariantAnnotation] = None,
        chrom: str = "",
        pos: Optional[int] = None,
        ref: str = "",
        alt: str = "",
        **kwargs: Any,
    ):
        """
        Initialize AnnotatedVariant.

        Can be initialized either with:
        1. A Variant instance (traditional)
        2. Direct chrom/pos/ref/alt parameters (convenience)

        Args:
            variant: Variant instance (optional)
            annotation: VariantAnnotation instance (optional)
            chrom: Chromosome (convenience parameter)
            pos: Position (convenience parameter)
            ref: Reference allele (convenience parameter)
            alt: Alternate allele (convenience parameter)
            **kwargs: Additional Variant or VariantAnnotation parameters
        """
        # If chrom/pos provided but no variant, create Variant
        if not variant and (chrom or pos is not None):
            variant_kwargs = {"chrom": chrom, "pos": pos, "ref": ref, "alt": alt}
            for key in ["rsid", "gene", "assembly", "genotype"]:
                if key in kwargs:
                    variant_kwargs[key] = kwargs.pop(key)
            variant = Variant(**variant_kwargs)

        self.variant = variant if variant else Variant()

        # Handle annotation
        if annotation is None:
            annotation_kwargs = {}
            for key in [
                "gnomad_af",
                "sift_score",
                "polyphen_score",
                "cadd_score",
                "clinvar_significance",
            ]:
                if key in kwargs:
                    annotation_kwargs[key] = kwargs.pop(key)
            annotation = (
                VariantAnnotation(**annotation_kwargs)
                if annotation_kwargs
                else VariantAnnotation()
            )
        self.annotation = annotation

    @property
    def rsid(self) -> str:
        """Convenience accessor for variant rsid."""
        return self.variant.rsid if self.variant else ""

    @property
    def chromosome(self) -> str:
        """Convenience accessor for chromosome."""
        return self.variant.chromosome if self.variant else ""

    @property
    def position(self) -> int:
        """Convenience accessor for position."""
        return self.variant.pos if self.variant else 0

    @property
    def gene(self) -> str:
        """Get gene from variant or annotation."""
        if self.variant and self.variant.gene:
            return self.variant.gene
        if self.annotation and self.annotation.gene_symbol:
            return self.annotation.gene_symbol
        return ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "variant": self.variant.to_dict() if self.variant else {},
            "annotation": self.annotation.to_dict(),
        }


# ============================================================================
# Classification Models
# ============================================================================


class PathogenicityClass(Enum):
    """ACMG pathogenicity classifications."""

    BENIGN = "Benign"
    LIKELY_BENIGN = "Likely Benign"
    VUS = "Uncertain Significance"
    LIKELY_PATHOGENIC = "Likely Pathogenic"
    PATHOGENIC = "Pathogenic"


@dataclass
class VariantClassification:
    """
    Complete classification result for a variant.

    Combines ACMG classification with evidence and metadata.
    """

    classification: str
    variant_id: str = ""
    evidence: ACMGEvidenceSet = field(default_factory=ACMGEvidenceSet)
    confidence: str = ""
    timestamp: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "classification": self.classification,
            "variant_id": self.variant_id,
            "evidence": self.evidence.summary(),
            "confidence": self.confidence,
            "timestamp": self.timestamp or datetime.now().isoformat(),
        }


# ============================================================================
# Batch Processing Models
# ============================================================================


@dataclass
class VariantBatch:
    """Collection of variantch processing."""

    variants: List[Variant] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_variant(self, variant: Variant):
        """Add variant to batch."""
        self.variants.append(variant)

    def __len__(self) -> int:
        """Return number of variants in batch."""
        return len(self.variants)

    def __iter__(self):
        """Iterate over variants."""
        return iter(self.variants)


# ============================================================================
# Export List
# ============================================================================

# ============================================================================
# Backward-compatibility aliases (for tests)
# ============================================================================

# Old name for ACMGEvidenceSet used in tests
ACMGCriteria = ACMGEvidenceSet

# Old name for position-based variant representation used in tests
GenomicVariant = VariantData

__all__ = [
    "ACMGEvidence",
    "ACMGEvidenceSet",
    "ACMGCriteria",      # NEW
    "Variant",
    "VariantData",
    "GenomicVariant",    # NEW
    "VariantAnnotation",
    "AnnotatedVariant",
    "VariantClassification",
    "VariantBatch",
    "PathogenicityClass",
]
