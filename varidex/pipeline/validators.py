"""VariDex Comprehensive Validators - Prevents v6.0.0 bugs"""

import re
import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class ComprehensiveValidator:
    """Comprehensive validation for variant data."""

    VALID_CHROMOSOMES = set([str(i) for i in range(1, 23)] + ["X", "Y", "MT", "M"])

    CHROMOSOME_BOUNDS = {
        "1": 248956422,
        "2": 242193529,
        "3": 198295559,
        "4": 190214555,
        "5": 181538259,
        "6": 170805979,
        "7": 159345973,
        "8": 145138636,
        "9": 138394717,
        "10": 133797422,
        "11": 135086622,
        "12": 133275309,
        "13": 114364328,
        "14": 107043718,
        "15": 101991189,
        "16": 90338345,
        "17": 83257441,
        "18": 80373285,
        "19": 58617616,
        "20": 64444167,
        "21": 46709983,
        "22": 50818468,
        "X": 156040895,
        "Y": 57227415,
        "MT": 16569,
        "M": 16569,
    }

    VALID_NUCLEOTIDES = set("ACGTN")

    @staticmethod
    def validate_rsid(rsid: str) -> Tuple[bool, Optional[str]]:
        """Validate rsID format."""
        if not rsid or pd.isna(rsid):
            return True, None
        rsid_str = str(rsid).strip()
        if not re.match(r"^rs\d+$", rsid_str):
            return False, "Invalid rsID format: {rsid_str}"
        return True, None

    @staticmethod
    def validate_chromosome(chromosome: str) -> Tuple[bool, Optional[str]]:
        """Validate chromosome identifier."""
        if not chromosome or pd.isna(chromosome):
            return False, "Missing chromosome"
        chrom_str = str(chromosome).strip().upper().replace("CHR", "")
        if chrom_str not in ComprehensiveValidator.VALID_CHROMOSOMES:
            return False, "Invalid chromosome: {chromosome}"
        return True, None

    @staticmethod
    def validate_position(position: int, chromosome: str) -> Tuple[bool, Optional[str]]:
        """Validate genomic position within bounds."""
        if pd.isna(position):
            return False, "Missing position"
        try:
            pos_int = int(position)
        except (ValueError, TypeError):
            return False, "Invalid position: {position}"
        if pos_int < 1:
            return False, "Position must be >= 1"
        chrom_norm = str(chromosome).upper().replace("CHR", "")
        max_pos = ComprehensiveValidator.CHROMOSOME_BOUNDS.get(chrom_norm)
        if max_pos and pos_int > max_pos:
            return False, "Position {pos_int} exceeds chr{chrom_norm} length"
        return True, None

    @staticmethod
    def validate_allele(allele: str, allele_type: str) -> Tuple[bool, Optional[str]]:
        """Validate allele sequence."""
        if not allele or pd.isna(allele):
            return False, "Missing {allele_type} allele"
        allele_str = str(allele).strip().upper()
        if len(allele_str) == 0:
            return False, "Empty {allele_type} allele"
        if allele_str in ["-", ".", "*"]:
            return True, None
        invalid_chars = set(allele_str) - ComprehensiveValidator.VALID_NUCLEOTIDES
        if invalid_chars:
            return False, "Invalid characters in {allele_type}: {invalid_chars}"
        return True, None

    @classmethod
    def validate_variant_complete(cls, variant_data: Dict) -> Tuple[bool, List[str]]:
        """Comprehensive variant validation."""
        errors = []
        required = ["chromosome", "position", "ref_allele", "alt_allele"]
        for field in required:
            if field not in variant_data or variant_data[field] is None:
                errors.append("Missing: {field}")
        if errors:
            return False, errors

        if "rsid" in variant_data:
            valid, error = cls.validate_rsid(variant_data["rsid"])
            if not valid:
                errors.append(error)

        valid, error = cls.validate_chromosome(variant_data["chromosome"])
        if not valid:
            errors.append(error)

        valid, error = cls.validate_position(
            variant_data["position"], variant_data["chromosome"]
        )
        if not valid:
            errors.append(error)

        valid, error = cls.validate_allele(variant_data["ref_allele"], "reference")
        if not valid:
            errors.append(error)

        valid, error = cls.validate_allele(variant_data["alt_allele"], "alternate")
        if not valid:
            errors.append(error)

        return len(errors) == 0, errors

    @classmethod
    def validate_dataframe_batch(
        cls, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Batch validate DataFrame."""
        if df is None or len(df) == 0:
            return pd.DataFrame(), pd.DataFrame()

        valid_indices = []
        invalid_records = []

        for idx, row in df.iterrows():
            variant_dict = row.to_dict()
            is_valid, errors = cls.validate_variant_complete(variant_dict)
            if is_valid:
                valid_indices.append(idx)
            else:
                invalid_record = variant_dict.copy()
                invalid_record["error_reason"] = "; ".join(errors)
                invalid_records.append(invalid_record)

        valid_df = df.loc[valid_indices].copy()
        invalid_df = (
            pd.DataFrame(invalid_records) if invalid_records else pd.DataFrame()
        )
        logger.info("Validation: {len(valid_df)} valid, {len(invalid_df)} invalid")
        return valid_df, invalid_df


def validate_assembly(assembly: str) -> bool:
    """
    Validate genome assembly identifier.

    Args:
        assembly: Genome assembly identifier (e.g., "GRCh38", "hg19")

    Returns:
        True if valid assembly identifier

    Raises:
        ValidationError: If assembly is invalid
    """
    valid_assemblies = ["GRCh37", "GRCh38", "hg19", "hg38", "b37", "b38"]

    if assembly not in valid_assemblies:
        raise ValidationError(
            f"Invalid assembly '{assembly}'. "
            f"Valid assemblies: {', '.join(valid_assemblies)}"
        )

    return True


# Module-level validator functions for backward compatibility
def validate_chromosome(chromosome: str) -> bool:
    """
    Validate chromosome identifier.

    Args:
        chromosome: Chromosome identifier (e.g., "1", "chr1", "X", "MT")

    Returns:
        True if valid chromosome

    Raises:
        ValidationError: If chromosome is invalid
    """
    from varidex.exceptions import ValidationError

    chrom = str(chromosome).upper().replace("CHR", "")
    valid_chroms = [str(i) for i in range(1, 23)] + ["X", "Y", "M", "MT"]

    if chrom not in valid_chroms:
        raise ValidationError(f"Invalid chromosome identifier: {chromosome}")

    return True


def validate_coordinates(
    chromosome: str, position: int, ref: str = "", alt: str = ""
) -> bool:
    """
    Validate genomic coordinates.

    Args:
        chromosome: Chromosome identifier
        position: Genomic position
        ref: Reference allele (optional)
        alt: Alternate allele (optional)

    Returns:
        True if coordinates are valid

    Raises:
        ValidationError: If coordinates are invalid
    """
    from varidex.exceptions import ValidationError

    # Validate chromosome
    validate_chromosome(chromosome)

    # Validate position
    if not isinstance(position, int) or position < 1:
        raise ValidationError(f"Invalid position: {position}")

    # Validate alleles if provided
    if ref and not all(c in "ACGTN" for c in ref.upper()):
        raise ValidationError(f"Invalid reference allele: {ref}")

    if alt and not all(c in "ACGTN" for c in alt.upper()):
        raise ValidationError(f"Invalid alternate allele: {alt}")

    return True


def validate_reference_allele(ref: str) -> bool:
    """
    Validate reference allele sequence.

    Args:
        ref: Reference allele sequence

    Returns:
        True if valid

    Raises:
        ValidationError: If invalid
    """
    from varidex.exceptions import ValidationError

    if not ref:
        raise ValidationError("Reference allele cannot be empty")

    if not all(c in "ACGTN" for c in ref.upper()):
        raise ValidationError(f"Invalid reference allele: {ref}")

    return True


def validate_variant(variant_data: dict) -> bool:
    """
    Validate complete variant data.

    Args:
        variant_data: Dictionary with variant information

    Returns:
        True if valid

    Raises:
        ValidationError: If invalid
    """
    from varidex.exceptions import ValidationError

    required_fields = ["chromosome", "position"]
    for field in required_fields:
        if field not in variant_data:
            raise ValidationError(f"Missing required field: {field}")

    # Validate coordinates
    validate_coordinates(
        variant_data["chromosome"],
        variant_data["position"],
        variant_data.get("ref", ""),
        variant_data.get("alt", ""),
    )

    return True


def validate_vcf_file(filepath: str) -> bool:
    """
    Validate VCF file exists and is readable.

    Args:
        filepath: Path to VCF file

    Returns:
        True if valid

    Raises:
        ValidationError: If invalid
    """
    from pathlib import Path
    from varidex.exceptions import ValidationError

    path = Path(filepath)

    if not path.exists():
        raise ValidationError(f"VCF file not found: {filepath}")

    if not path.is_file():
        raise ValidationError(f"Not a file: {filepath}")

    if not path.suffix.lower() in [".vcf", ".vcf.gz"]:
        raise ValidationError(f"Not a VCF file: {filepath}")

    return True
