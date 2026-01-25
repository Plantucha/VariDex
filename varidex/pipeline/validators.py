"""
Pipeline validation functions for genomic variant data.
"""

from typing import Optional
from pathlib import Path
import gzip

from varidex.exceptions import ValidationError

CHROMOSOME_LENGTHS = {
    "1": 249250621,
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
    "M": 16569,
    "MT": 16569,
}

VALID_ASSEMBLIES = {
    "GRCh37",
    "GRCh38",
    "GRCh39",
    "hg19",
    "hg38",
    "hg18",
    "T2T-CHM13v2.0",
}


def validate_assembly(assembly: str) -> bool:
    """Validate reference genome assembly identifier."""
    if not assembly:
        return False
    assembly_upper = str(assembly).upper()
    return any(a.upper() == assembly_upper for a in VALID_ASSEMBLIES)


def validate_chromosome(chromosome: str) -> bool:
    """Validate chromosome identifier. Does NOT strip whitespace."""
    if not chromosome:
        return False
    chrom_str = str(chromosome)
    if chrom_str != chrom_str.strip():
        return False
    chrom = chrom_str.upper().replace("CHR", "")
    valid_chroms = [str(i) for i in range(1, 23)] + ["X", "Y", "M", "MT"]
    return chrom in valid_chroms


def validate_coordinates(chromosome: str, start: int, end: int) -> bool:
    """Validate genomic coordinate range."""
    if not validate_chromosome(chromosome):
        return False
    try:
        start = int(start)
        end = int(end)
    except (ValueError, TypeError):
        return False
    if start < 1 or end < 1:
        return False
    if end < start:
        return False
    chrom_normalized = str(chromosome).upper().replace("CHR", "")
    max_pos = CHROMOSOME_LENGTHS.get(chrom_normalized, 300000000)
    if start > max_pos or end > max_pos:
        return False
    return True


def validate_reference_allele(ref: str) -> bool:
    """Validate reference allele. N is INVALID."""
    if not ref:
        return False
    ref_str = str(ref).strip().upper()
    if not ref_str:
        return False
    if " " in ref_str:
        return False
    if ref_str == "-":
        return True
    valid_chars = set("ACGT")
    return all(c in valid_chars for c in ref_str)


def validate_alternate_allele(alt: str) -> bool:
    """Validate alternate allele."""
    return validate_reference_allele(alt)


def validate_reference(ref: str) -> bool:
    """Alias for validate_reference_allele."""
    return validate_reference_allele(ref)


def validate_alternate(alt: str) -> bool:
    """Alias for validate_alternate_allele."""
    return validate_alternate_allele(alt)


def validate_variant(variant, raise_on_error: bool = False) -> bool:
    """Validate complete variant object with proper error handling."""
    try:
        # Check required attributes
        if not hasattr(variant, "chromosome"):
            if raise_on_error:
                raise ValidationError("Missing chromosome attribute")
            return False
        if not hasattr(variant, "position"):
            if raise_on_error:
                raise ValidationError("Missing position attribute")
            return False

        # Validate chromosome
        if not validate_chromosome(variant.chromosome):
            if raise_on_error:
                raise ValidationError(f"Invalid chromosome: {variant.chromosome}")
            return False

        # Validate position
        try:
            pos = int(variant.position)
            if pos < 1:
                if raise_on_error:
                    raise ValidationError(f"Invalid position: {pos}")
                return False
        except (ValueError, TypeError):
            if raise_on_error:
                raise ValidationError(f"Position must be integer: {variant.position}")
            return False

        # Check chromosome length
        chrom_norm = str(variant.chromosome).upper().replace("CHR", "")
        max_pos = CHROMOSOME_LENGTHS.get(chrom_norm, 300000000)
        if pos > max_pos:
            if raise_on_error:
                raise ValidationError(f"Position exceeds chromosome length")
            return False

        # Validate assembly if present
        if hasattr(variant, "assembly") and variant.assembly:
            if not validate_assembly(variant.assembly):
                if raise_on_error:
                    raise ValidationError(f"Invalid assembly: {variant.assembly}")
                return False

        # Validate alleles - if alt present, ref must also be present
        has_ref = hasattr(variant, "ref_allele") and variant.ref_allele
        has_alt = hasattr(variant, "alt_allele") and variant.alt_allele

        if has_alt and not has_ref:
            if raise_on_error:
                raise ValidationError("Alternate allele present but missing reference")
            return False

        if has_ref and not validate_reference_allele(variant.ref_allele):
            if raise_on_error:
                raise ValidationError(f"Invalid reference: {variant.ref_allele}")
            return False

        if has_alt and not validate_alternate_allele(variant.alt_allele):
            if raise_on_error:
                raise ValidationError(f"Invalid alternate: {variant.alt_allele}")
            return False

        return True

    except ValidationError:
        raise
    except Exception as e:
        if raise_on_error:
            raise ValidationError(f"Validation error: {e}")
        return False


def validate_vcf_file(filepath) -> bool:
    """Validate VCF file format."""
    path = Path(str(filepath))
    if not path.exists():
        raise ValidationError(f"File does not exist: {filepath}")
    if not path.is_file():
        raise ValidationError(f"Not a file: {filepath}")
    valid_extensions = [".vcf", ".vcf.gz"]
    if not any(str(path).lower().endswith(ext) for ext in valid_extensions):
        raise ValidationError("Invalid file extension. Expected .vcf or .vcf.gz")
    try:
        if str(path).endswith(".gz"):
            with gzip.open(path, "rt") as f:
                lines = [f.readline() for _ in range(100)]
        else:
            with open(path, "r") as f:
                lines = [f.readline() for _ in range(100)]
        if not lines or not any(line.strip() for line in lines):
            raise ValidationError("Empty file")
        first_line = None
        header_line = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("##"):
                if first_line is None:
                    first_line = line
                continue
            if line.startswith("#CHROM"):
                header_line = line
                break
        if not first_line or not first_line.startswith("##fileformat=VCF"):
            raise ValidationError("Missing VCF header")
        if header_line:
            required_cols = [
                "#CHROM",
                "POS",
                "ID",
                "REF",
                "ALT",
                "QUAL",
                "FILTER",
                "INFO",
            ]
            if not all(col in header_line for col in required_cols):
                raise ValidationError("Invalid column header")
        return True
    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError(f"Cannot read VCF file: {e}")


class DataValidator:
    """Validator class for backward compatibility."""

    @staticmethod
    def validate_chromosome(chromosome: str) -> tuple:
        if validate_chromosome(chromosome):
            return True, None
        return False, f"Invalid chromosome: {chromosome}"

    @staticmethod
    def validate_coordinates(chromosome: str, start: int, end: int) -> tuple:
        if validate_coordinates(chromosome, start, end):
            return True, None
        return False, f"Invalid coordinates: {chromosome}:{start}-{end}"

    @staticmethod
    def validate_variant_data(variant) -> tuple:
        if validate_variant(variant):
            return True, None
        return False, "Invalid variant data"
