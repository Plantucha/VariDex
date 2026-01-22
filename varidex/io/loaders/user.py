#!/usr/bin/env python3
"""varidex/io/loaders/user.py - User Genome Data Loader
Load 23andMe, VCF, TSV formats → DataFrame(rsid, chromosome, position, genotype)

Version: Managed by varidex.version (import version from varidex.version)
Changelog:
  - v6.0.1: Fixed over-filtering - preserves rs*, i*, d* variants (indels)
  - v6.0.1: Added variant_id_type column for downstream flexibility
  - v6.0.1: Consistent validation across all file formats
  - v6.0.0: Initial unified release
"""
import pandas as pd
import logging
import re
from pathlib import Path
from typing import Optional, Tuple
from pathlib import Path


# Version is managed centrally - do NOT hardcode
try:
    from varidex.version import version as __version__
except ImportError:
    __version__ = "6.0.0"  # Fallback only

from varidex.exceptions import DataLoadError, ValidationError

logger = logging.getLogger(__name__)
USER_FILE_FORMATS = ["23andme", "vcf", "tsv"]


def validate_file_safety(filepath: Path) -> bool:
    """Validate file exists and is readable."""
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    if filepath.stat().st_size == 0:
        raise ValidationError("File is empty", context={"file": str(filepath)})
    return True


def validate_chromosome_consistency(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize chromosomes: chr1→1, NC_000001→1, 23→X, 24→Y, M→MT."""
    if "chromosome" not in df.columns:
        return df
    df = df.copy()
    df["chromosome"] = df["chromosome"].astype(str).str.replace("chr", "", regex=True, case=False)
    nc = re.compile(r"NC_0000([01][0-9]|2[0-4])")
    df["chromosome"] = df["chromosome"].apply(
        lambda c: str(int(nc.match(str(c)).group(1))) if not pd.isna(c) and nc.match(str(c)) else c
    )
    df["chromosome"] = df["chromosome"].replace({"23": "X", "24": "Y", "M": "MT"}).str.upper()
    return df


def classify_variant_id(variant_id: str) -> str:
    """Classify variant ID type for tracking and downstream decisions.

    Returns:
        'rsid': Standard dbSNP (rs123456)
        'insertion': 23andMe insertion (i123456)
        'deletion': 23andMe deletion (d123456)
        'novel': VCF novel/private variant (.)
        'complex': Other formats (chr:pos:ref:alt, etc)
        'invalid': Empty or null
    """
    if pd.isna(variant_id) or variant_id == "" or variant_id == ".":
        return "novel"
    vid = str(variant_id).strip()
    if re.match(r"^rs\d+$", vid):
        return "rsid"
    if re.match(r"^i\d+$", vid):
        return "insertion"
    if re.match(r"^d\d+$", vid):
        return "deletion"
    if ":" in vid or "-" in vid:
        return "complex"
    return "invalid"


def validate_variant_data_quality(df: pd.DataFrame) -> Tuple[pd.DataFrame, dict]:
    """Validate and clean variant data without over-filtering.

    Returns:
        Cleaned DataFrame and stats dict
    """
    stats = {"input_rows": len(df)}

    df = df.dropna(how="all")
    stats["after_empty_removal"] = len(df)

    df["variant_id_type"] = df["rsid"].apply(classify_variant_id)

    valid_mask = df["variant_id_type"] != "invalid"
    df = df[valid_mask]
    stats["after_validation"] = len(df)

    if "position" in df.columns:
        df = df[df["position"].notna() & (df["position"] > 0)]
    stats["after_coordinate_check"] = len(df)

    stats["type_distribution"] = df["variant_id_type"].value_counts().to_dict()

    return df, stats


def detect_user_file_type(filepath: Path) -> str:
    """Auto-detect format: 23andme|vcf|tsv."""
    filepath = Path(filepath)
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = [f.readline() for _ in range(10)]
        if any(l.startswith("##fileformat=VCF") or l.startswith("#CHROM") for l in lines):
            return "vcf"
        if any("23andMe" in l for l in lines):
            return "23andme"
        return "tsv"
    except Exception as e:
        raise DataLoadError(
            "Failed to detect format", context={"file": str(filepath), "error": str(e)}
        )


def load_23andme_file(filepath: Path) -> pd.DataFrame:
    """Load 23andMe raw data file - preserves rs*, i*, d* variants."""
    filepath = Path(filepath)
    logger.info(f"Loading 23andMe: {Path(filepath).name}")
    validate_file_safety(filepath)

    try:
        df = pd.read_csv(
            filepath,
            sep="	",
            comment="#",
            names=["rsid", "chromosome", "position", "genotype"],
            dtype={"chromosome": str, "position": "Int64", "genotype": str},
            on_bad_lines="skip",
        )

        if len(df) == 0:
            raise ValidationError("No variants in file", context={"file": str(filepath)})

        df = validate_chromosome_consistency(df)
        df, stats = validate_variant_data_quality(df)

        if len(df) == 0:
            raise ValidationError(
                "No valid variants after quality check", context={"file": str(filepath)}
            )

        logger.info(f"Loaded {len(df):,} variants from {stats['input_rows']:,} rows")
        logger.info(f"Variant types: {stats['type_distribution']}")

        return df

    except (ValidationError, DataLoadError):
        raise
    except Exception as e:
        raise DataLoadError(
            "Failed to load 23andMe", context={"file": str(filepath), "error": str(e)}
        )


def load_user_vcf(filepath: Path) -> pd.DataFrame:
    """Load personal VCF file - consistent validation with 23andMe."""
    filepath = Path(filepath)
    logger.info(f"Loading VCF: {Path(filepath).name}")
    validate_file_safety(filepath)

    try:
        df = pd.read_csv(
            filepath,
            sep="	",
            comment="#",
            names=["CHROM", "POS", "ID", "REF", "ALT", "QUAL", "FILTER", "INFO"],
            usecols=["CHROM", "POS", "ID", "REF", "ALT"],
            dtype={"CHROM": str, "POS": "Int64", "ID": str, "REF": str, "ALT": str},
            on_bad_lines="skip",
        )

        if len(df) == 0:
            raise ValidationError("No variants in VCF")

        df = df.rename(columns={"CHROM": "chromosome", "POS": "position", "ID": "rsid"})
        df["genotype"] = df["REF"] + df["ALT"]
        df = validate_chromosome_consistency(df)
        df, stats = validate_variant_data_quality(df)

        logger.info(f"Loaded {len(df):,} variants from {stats['input_rows']:,} rows")
        logger.info(f"Variant types: {stats['type_distribution']}")

        return df[["rsid", "chromosome", "position", "genotype", "variant_id_type"]]

    except (ValidationError, DataLoadError):
        raise
    except Exception as e:
        raise DataLoadError("Failed to load VCF", context={"file": str(filepath), "error": str(e)})


def load_user_tsv(filepath: Path) -> pd.DataFrame:
    """Load generic TSV with auto-column detection and consistent validation."""
    filepath = Path(filepath)
    logger.info(f"Loading TSV: {Path(filepath).name}")
    validate_file_safety(filepath)

    try:
        df = pd.read_csv(filepath, sep="	", low_memory=False)

        col_map = {}
        for target, cands in {
            "rsid": ["rsid", "rs#", "dbsnp", "variant_id", "id"],
            "chromosome": ["chromosome", "chr", "chrom", "#chr"],
            "position": ["position", "pos", "bp", "start"],
            "genotype": ["genotype", "alleles", "gt", "allele"],
        }.items():
            for col in df.columns:
                if any(c in col.lower() for c in cands):
                    col_map[col] = target
                    break

        df = df.rename(columns=col_map)

        req = ["rsid", "chromosome", "position", "genotype"]
        miss = [c for c in req if c not in df.columns]
        if miss:
            raise ValidationError(
                f"Missing required columns: {miss}",
                context={"file": str(filepath), "available": list(df.columns)},
            )

        df = validate_chromosome_consistency(df)
        df, stats = validate_variant_data_quality(df)

        logger.info(f"Loaded {len(df):,} variants from {stats['input_rows']:,} rows")
        logger.info(f"Variant types: {stats['type_distribution']}")

        return df[["rsid", "chromosome", "position", "genotype", "variant_id_type"]]

    except (ValidationError, DataLoadError):
        raise
    except Exception as e:
        raise DataLoadError("Failed to load TSV", context={"file": str(filepath), "error": str(e)})


def load_user_file(filepath: Path, file_format: Optional[str] = None) -> pd.DataFrame:
    """Auto-detect and load user genome file with comprehensive validation.

    Args:
        filepath: Path to data file
        file_format: Optional override ('23andme'|'vcf'|'tsv')

    Returns:
        DataFrame with columns: rsid, chromosome, position, genotype, variant_id_type

    Note:
        Preserves all valid variants including insertions (i*), deletions (d*),
        and novel variants (.) to prevent data loss. Use variant_id_type column
        for downstream filtering decisions.
    """
    filepath = Path(filepath)
    if file_format is None:
        file_format = detect_user_file_type(filepath)

    loaders = {"23andme": load_23andme_file, "vcf": load_user_vcf, "tsv": load_user_tsv}

    if file_format not in loaders:
        raise ValueError(f"Unknown format: {file_format}. Must be {USER_FILE_FORMATS}")

    return loaders[file_format](filepath)
