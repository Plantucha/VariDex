#!/usr/bin/env python3
"""varidex/io/loaders/user.py - User Genome Data Loader.

Load 23andMe, VCF, TSV formats → DataFrame(rsid, chromosome, position, genotype)
"""

import logging
import re
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd

try:
    from varidex.version import version as __version__
except ImportError:
    __version__ = "6.0.2"

from varidex.exceptions import DataLoadError, ValidationError

logger = logging.getLogger(__name__)
USER_FILE_FORMATS = ["23andme", "vcf", "tsv"]


def validate_file_safety(filepath: Path) -> None:
    """Validate file exists and is readable."""
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    if filepath.stat().st_size == 0:
        raise ValidationError("File is empty", context={"file": str(filepath)})


def normalize_chromosome(chrom: str) -> str:
    """Normalize single chromosome value."""
    chrom_clean = str(chrom).replace("chr", "").replace("Chr", "").upper()
    nc_pattern = re.compile(r"NC_0000([01][0-9]|2[0-4])")
    nc_match = nc_pattern.match(chrom_clean)
    if nc_match:
        return str(int(nc_match.group(1)))
    chrom_map = {"23": "X", "24": "Y", "M": "MT"}
    return chrom_map.get(chrom_clean, chrom_clean)


def validate_chromosome_consistency(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize chromosomes."""
    if "chromosome" not in df.columns:
        return df
    df = df.copy()
    df["chromosome"] = (
        df["chromosome"]
        .astype(str)
        .str.replace("chr", "", regex=True, case=False)
        .str.upper()
    )
    df["chromosome"] = df["chromosome"].apply(
        lambda c: normalize_chromosome(c) if not pd.isna(c) else c
    )
    return df


def classify_variant_id(variant_id: str) -> str:
    """Classify variant ID type."""
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


def validate_variant_data_quality(
    df: pd.DataFrame,
) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """Validate and clean variant data."""
    stats: Dict[str, int] = {"input_rows": len(df)}
    df = df.dropna(how="all")
    stats["after_empty_removal"] = len(df)
    df["variant_id_type"] = df["rsid"].apply(classify_variant_id)
    valid_mask = df["variant_id_type"] != "invalid"
    df = df[valid_mask]
    stats["after_validation"] = len(df)
    if "position" in df.columns:
        df = df[df["position"].notna() & (df["position"] > 0)]
    stats["after_coordinate_check"] = len(df)
    type_counts = df["variant_id_type"].value_counts().to_dict()
    stats["type_distribution"] = {str(k): int(v) for k, v in type_counts.items()}
    return df, stats


def detect_user_file_type(filepath: Path) -> str:
    """Auto-detect format."""
    filepath = Path(filepath)
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = [f.readline() for _ in range(10)]
        if any(
            line.startswith("##fileformat=VCF") or line.startswith("#CHROM")
            for line in lines
        ):
            return "vcf"
        if any("23andMe" in line for line in lines):
            return "23andme"
        return "tsv"
    except Exception as e:
        raise DataLoadError(
            "Failed to detect format",
            context={"file": str(filepath), "error": str(e)},
        )


def load_23andme_file(filepath: Path) -> pd.DataFrame:
    """Load 23andMe file."""
    filepath = Path(filepath)
    logger.info(f"Loading 23andMe: {filepath.name}")
    validate_file_safety(filepath)
    try:
        df = pd.read_csv(
            filepath,
            sep="\t",
            comment="#",
            names=["rsid", "chromosome", "position", "genotype"],
            dtype={"chromosome": str, "position": "Int64", "genotype": str},
            on_bad_lines="skip",
        )
        if len(df) == 0:
            raise ValidationError(
                "No variants in file", context={"file": str(filepath)}
            )
        df = validate_chromosome_consistency(df)
        df, stats = validate_variant_data_quality(df)
        if len(df) == 0:
            raise ValidationError("No valid variants", context={"file": str(filepath)})
        logger.info(f"Loaded {len(df):,} variants from {stats['input_rows']:,} rows")
        return df
    except (ValidationError, DataLoadError):
        raise
    except Exception as e:
        raise DataLoadError(
            "Failed to load 23andMe",
            context={"file": str(filepath), "error": str(e)},
        )


def load_user_vcf(filepath: Path) -> pd.DataFrame:
    """Load VCF file with flexible column detection."""
    filepath = Path(filepath)
    logger.info(f"Loading VCF: {filepath.name}")
    validate_file_safety(filepath)
    try:
        # Count lines to skip (## metadata lines)
        skip_rows = []
        with open(filepath, "r") as f:
            for i, line in enumerate(f):
                if line.startswith("##"):
                    skip_rows.append(i)
                elif line.startswith("#CHROM"):
                    break  # Header found, stop
                elif not line.startswith("#"):
                    break  # Data without header
        
        # Read VCF skipping only ## lines
        df = pd.read_csv(
            filepath,
            sep="	",
            skiprows=skip_rows if skip_rows else None,
            dtype={
                "#CHROM": str,
                "CHROM": str,
                "POS": "Int64",
                "ID": str,
                "REF": str,
                "ALT": str,
            },
            on_bad_lines="skip",
            low_memory=False,
        )
        
        # Handle #CHROM vs CHROM
        if "#CHROM" in df.columns:
            df = df.rename(columns={"#CHROM": "CHROM"})
        elif len(df.columns) == 5 and "CHROM" not in df.columns:
            # No header detected, assign names
            df.columns = ["CHROM", "POS", "ID", "REF", "ALT"]

        if len(df) == 0:
            raise ValidationError("No variants in VCF", context={"file": str(filepath)})

        # Keep needed columns
        needed = ["CHROM", "POS", "ID", "REF", "ALT"]
        df = df[[col for col in needed if col in df.columns]]

        # STEP 1: Rename ID->rsid FIRST
        df = df.rename(columns={"CHROM": "chromosome", "POS": "position", "ID": "rsid"})

        # STEP 2: Create genotype from REF/ALT
        if "REF" in df.columns and "ALT" in df.columns:
            df["genotype"] = df["REF"].astype(str) + df["ALT"].astype(str)
            df = df.drop(columns=["REF", "ALT"])
        else:
            df["genotype"] = ""

        # STEP 3: Normalize chromosomes
        df = validate_chromosome_consistency(df)

        # STEP 4: Validate (rsid exists now)
        df, stats = validate_variant_data_quality(df)

        if len(df) == 0:
            raise ValidationError("No valid variants", context={"file": str(filepath)})

        logger.info(f"Loaded {len(df):,} variants from {stats['input_rows']:,} rows")
        return df[["rsid", "chromosome", "position", "genotype", "variant_id_type"]]

    except (ValidationError, DataLoadError):
        raise
    except Exception as e:
        raise DataLoadError(
            "Failed to load VCF", context={"file": str(filepath), "error": str(e)}
        )



def load_user_tsv(filepath: Path) -> pd.DataFrame:
    """Load generic TSV."""
    filepath = Path(filepath)
    logger.info(f"Loading TSV: {filepath.name}")
    validate_file_safety(filepath)
    try:
        df = pd.read_csv(filepath, sep="\t", low_memory=False)
        col_map: Dict[str, str] = {}
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
            raise ValidationError(f"Missing: {miss}", context={"file": str(filepath)})
        df = validate_chromosome_consistency(df)
        df, stats = validate_variant_data_quality(df)
        logger.info(f"Loaded {len(df):,} variants")
        return df[["rsid", "chromosome", "position", "genotype", "variant_id_type"]]
    except (ValidationError, DataLoadError):
        raise
    except Exception as e:
        raise DataLoadError(
            "Failed to load TSV", context={"file": str(filepath), "error": str(e)}
        )


def load_user_file(filepath: Path, file_format: Optional[str] = None) -> pd.DataFrame:
    """Auto-detect and load user genome file."""
    filepath = Path(filepath)
    if file_format is None:
        file_format = detect_user_file_type(filepath)
    loaders = {
        "23andme": load_23andme_file,
        "vcf": load_user_vcf,
        "tsv": load_user_tsv,
    }
    if file_format not in loaders:
        raise ValueError(f"Unknown format: {file_format}")
    return loaders[file_format](filepath)


def load_23andme(filepath: str, assembly: str = "GRCh38") -> pd.DataFrame:
    """Load 23andMe (legacy wrapper)."""
    df = pd.read_csv(
        filepath,
        sep="\t",
        comment="#",
        names=["rsid", "chromosome", "position", "genotype"],
    )
    df = df[df["chromosome"].notna()].copy()
    df["chromosome"] = df["chromosome"].astype(str)
    df["position"] = pd.to_numeric(df["position"], errors="coerce")
    df = df.dropna(subset=["position"])
    df["position"] = df["position"].astype(int)
    return df
