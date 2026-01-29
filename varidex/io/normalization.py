"""
VariDex IO Normalization Module v6.5
====================================
Data normalization utilities for variant data.

BUGFIX v6.5: Added coord_key creation and left-alignment
"""

from typing import Any, Tuple
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def normalize_chromosome(chrom: str) -> str:
    """
    Normalize chromosome name.

    Args:
        chrom: Chromosome name (e.g., "chr1", "1", "chrX")

    Returns:
        Normalized chromosome name
    """
    chrom = str(chrom).replace("chr", "").replace("Chr", "").replace("CHR", "")

    if chrom in ["M", "m"]:
        return "MT"

    return chrom.upper()


def normalize_position(pos: Any) -> int:
    """
    Normalize genomic position.

    Args:
        pos: Genomic position

    Returns:
        Normalized position (ensuring positive integer)
    """
    return abs(int(pos))


def normalize_ref_alt(ref: str, alt: str) -> Tuple[str, str]:
    """
    Normalize reference and alternate alleles (basic trimming).

    Args:
        ref: Reference allele
        alt: Alternate allele

    Returns:
        Tuple of (normalized_ref, normalized_alt)
    """
    ref = str(ref).upper().strip()
    alt = str(alt).upper().strip()

    # Trim common prefixes (simple version)
    while len(ref) > 1 and len(alt) > 1 and ref[0] == alt[0]:
        ref = ref[1:]
        alt = alt[1:]

    return (ref, alt)


def left_align_variants(df: pd.DataFrame) -> pd.DataFrame:
    """
    Left-align indels per VCF standard.

    This ensures variants are represented consistently:
    - Removes common suffixes from right side
    - Removes common prefixes from left side (adjusts position)

    Args:
        df: DataFrame with ref_allele, alt_allele, position columns

    Returns:
        DataFrame with left-aligned variants
    """
    df = df.copy()

    required_cols = ["ref_allele", "alt_allele", "position"]
    if not all(col in df.columns for col in required_cols):
        logger.warning(f"Missing columns for left-alignment: {required_cols}")
        return df

    for idx in df.index:
        try:
            ref = str(df.at[idx, "ref_allele"]).upper()
            alt = str(df.at[idx, "alt_allele"]).upper()
            pos = int(df.at[idx, "position"])

            # Skip if missing data
            if pd.isna(ref) or pd.isna(alt) or ref == "" or alt == "":
                continue

            # Trim common suffixes (right side)
            while len(ref) > 1 and len(alt) > 1 and ref[-1] == alt[-1]:
                ref = ref[:-1]
                alt = alt[:-1]

            # Trim common prefixes (left side) and adjust position
            while len(ref) > 1 and len(alt) > 1 and ref[0] == alt[0]:
                ref = ref[1:]
                alt = alt[1:]
                pos += 1

            df.at[idx, "ref_allele"] = ref
            df.at[idx, "alt_allele"] = alt
            df.at[idx, "position"] = pos

        except Exception as e:
            logger.warning(f"Left-alignment failed for row {idx}: {e}")
            continue

    return df


def create_coord_key(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create coordinate matching key (chr:pos:ref:alt).

    CRITICAL: This function was missing in v6.0-6.4, causing all
    coordinate matching to fail!

    Args:
        df: DataFrame with chromosome, position, ref_allele, alt_allele

    Returns:
        DataFrame with added 'coord_key' column
    """
    df = df.copy()

    required_cols = ["chromosome", "position", "ref_allele", "alt_allele"]
    missing = [col for col in required_cols if col not in df.columns]

    if missing:
        logger.error(f"Cannot create coord_key, missing columns: {missing}")
        return df

    # Normalize chromosomes
    df["chromosome"] = df["chromosome"].apply(normalize_chromosome)

    # Left-align indels (CRITICAL for matching!)
    df = left_align_variants(df)

    # Create key: chr:pos:ref:alt
    df["coord_key"] = (
        df["chromosome"].astype(str)
        + ":"
        + df["position"].astype(str)
        + ":"
        + df["ref_allele"].astype(str).str.upper()
        + ":"
        + df["alt_allele"].astype(str).str.upper()
    )

    logger.info(f"Created {len(df)} coord_keys")
    return df


def normalize_dataframe_coordinates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize chromosome coordinates in a dataframe and create coord_key.

    BUGFIX v6.5: Now actually creates coord_key (was missing before!)

    Args:
        df: DataFrame with columns like 'Chromosome', 'Position', etc.

    Returns:
        DataFrame with normalized coordinates and coord_key
    """
    df = df.copy()

    # Normalize chromosome column if it exists
    chrom_cols = ["Chromosome", "chromosome", "Chr", "chr", "CHROM"]
    for col in chrom_cols:
        if col in df.columns:
            df[col] = df[col].apply(normalize_chromosome)
            # Standardize to 'chromosome'
            if col != "chromosome":
                df["chromosome"] = df[col]
            break

    # Normalize position columns if they exist
    pos_cols = ["Position", "position", "Pos", "pos", "POS", "Start", "start"]
    for col in pos_cols:
        if col in df.columns:
            df[col] = df[col].apply(normalize_position)
            # Standardize to 'position'
            if col != "position":
                df["position"] = df[col]
            break

    # Standardize ref/alt column names
    if "REF" in df.columns and "ref_allele" not in df.columns:
        df["ref_allele"] = df["REF"]
    if "ALT" in df.columns and "alt_allele" not in df.columns:
        df["alt_allele"] = df["ALT"]
    if "ref" in df.columns and "ref_allele" not in df.columns:
        df["ref_allele"] = df["ref"]
    if "alt" in df.columns and "alt_allele" not in df.columns:
        df["alt_allele"] = df["alt"]

    # Create coord_key if possible
    required = ["chromosome", "position", "ref_allele", "alt_allele"]
    if all(col in df.columns for col in required):
        df = create_coord_key(df)
        logger.info(f"Normalized {len(df)} variants with coord_key")
    else:
        missing = [col for col in required if col not in df.columns]
        logger.warning(f"Cannot create coord_key, missing: {missing}")

    return df


__all__ = [
    "normalize_chromosome",
    "normalize_position",
    "normalize_ref_alt",
    "normalize_dataframe_coordinates",
    "create_coord_key",
    "left_align_variants",
]
