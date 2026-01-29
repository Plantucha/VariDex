"""
VariDex IO Normalization Module v6.5.4
=======================================
Data normalization utilities for variant data.

BUGFIX v6.5.4: Fixed dtype mismatch in coord_key assignment
"""

from typing import Any, Tuple, Optional
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


def normalize_chromosome(chrom: Any) -> Optional[str]:
    """
    Normalize chromosome name (NaN-safe).

    Args:
        chrom: Chromosome name (e.g., "chr1", "1", "chrX") or NaN

    Returns:
        Normalized chromosome name or None if invalid
    """
    # CRITICAL FIX: Handle NaN/None before string conversion
    if pd.isna(chrom) or chrom is None:
        return None
    
    try:
        chrom = str(chrom).replace("chr", "").replace("Chr", "").replace("CHR", "")
        
        # Handle empty strings
        if chrom.strip() == "" or chrom.upper() in ["NAN", "NONE"]:
            return None

        if chrom in ["M", "m"]:
            return "MT"

        return chrom.upper()
    except Exception as e:
        logger.debug(f"normalize_chromosome failed for {chrom}: {e}")
        return None


def normalize_position(pos: Any) -> Optional[int]:
    """
    Normalize genomic position (NaN-safe).

    Args:
        pos: Genomic position or NaN

    Returns:
        Normalized position (positive integer) or None if invalid
    """
    # CRITICAL FIX: Handle NaN/None before int conversion
    if pd.isna(pos) or pos is None:
        return None
    
    try:
        return abs(int(float(pos)))  # float() handles string numbers
    except (ValueError, TypeError) as e:
        logger.debug(f"normalize_position failed for {pos}: {e}")
        return None


def normalize_ref_alt(ref: str, alt: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Normalize reference and alternate alleles (basic trimming).

    Args:
        ref: Reference allele
        alt: Alternate allele

    Returns:
        Tuple of (normalized_ref, normalized_alt) or (None, None) if invalid
    """
    # Handle NaN inputs
    if pd.isna(ref) or pd.isna(alt):
        return (None, None)
    
    try:
        ref = str(ref).upper().strip()
        alt = str(alt).upper().strip()
        
        # Filter invalid strings
        if ref in ["", "NAN", "NONE"] or alt in ["", "NAN", "NONE"]:
            return (None, None)

        # Trim common prefixes (simple version)
        while len(ref) > 1 and len(alt) > 1 and ref[0] == alt[0]:
            ref = ref[1:]
            alt = alt[1:]

        return (ref, alt)
    except Exception as e:
        logger.debug(f"normalize_ref_alt failed: {e}")
        return (None, None)


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
            # Check for NaN BEFORE converting to string
            if pd.isna(df.at[idx, "ref_allele"]) or pd.isna(df.at[idx, "alt_allele"]):
                continue

            ref = str(df.at[idx, "ref_allele"]).upper()
            alt = str(df.at[idx, "alt_allele"]).upper()
            pos = int(df.at[idx, "position"])

            # Skip empty/invalid strings
            if ref in ["", "NAN", "NONE"] or alt in ["", "NAN", "NONE"]:
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
            logger.debug(f"Left-alignment failed for row {idx}: {e}")
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

    # CRITICAL FIX: Initialize coord_key as object dtype (not float64)
    # This prevents TypeError when assigning strings to float column
    df["coord_key"] = pd.Series([None] * len(df), dtype=object, index=df.index)

    # Filter out NaN rows BEFORE normalizing
    valid_mask = (
        df["chromosome"].notna()
        & df["position"].notna()
        & df["ref_allele"].notna()
        & df["alt_allele"].notna()
    )

    # Work only on valid rows
    valid_df = df[valid_mask].copy()

    if len(valid_df) == 0:
        logger.warning("No valid rows to create coord_keys")
        return df

    # Normalize chromosomes (now NaN-safe)
    valid_df["chromosome"] = valid_df["chromosome"].apply(normalize_chromosome)

    # CRITICAL FIX: Filter out None values AFTER normalization
    # normalize_chromosome can return None for invalid inputs
    post_norm_valid = (
        valid_df["chromosome"].notna()
        & valid_df["chromosome"].notnull()
        & (valid_df["chromosome"] != "None")
        & (valid_df["chromosome"] != "")
    )
    
    valid_df = valid_df[post_norm_valid].copy()
    
    if len(valid_df) == 0:
        logger.warning("No valid rows after normalization")
        return df

    # Left-align indels
    valid_df = left_align_variants(valid_df)

    # Create key: chr:pos:ref:alt
    valid_df["coord_key"] = (
        valid_df["chromosome"].astype(str)
        + ":"
        + valid_df["position"].astype(str)
        + ":"
        + valid_df["ref_allele"].astype(str).str.upper()
        + ":"
        + valid_df["alt_allele"].astype(str).str.upper()
    )

    # Merge back into original dataframe using index
    # Now safe because coord_key is object dtype
    df.loc[valid_df.index, "coord_key"] = valid_df["coord_key"].values

    valid_keys = df["coord_key"].notna().sum()
    invalid_keys = len(df) - valid_keys

    logger.info(f"Created {valid_keys:,} coord_keys ({invalid_keys:,} skipped)")

    return df


def normalize_dataframe_coordinates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize chromosome coordinates in a dataframe and create coord_key.

    BUGFIX v6.5.4: Fixed dtype handling for coord_key column

    Args:
        df: DataFrame with columns like 'Chromosome', 'Position', etc.

    Returns:
        DataFrame with normalized coordinates and coord_key
    """
    df = df.copy()

    # Normalize chromosome column if it exists (NaN-safe)
    chrom_cols = ["Chromosome", "chromosome", "Chr", "chr", "CHROM"]
    for col in chrom_cols:
        if col in df.columns:
            # Use map with na_action to skip NaN
            df[col] = df[col].map(normalize_chromosome, na_action="ignore")
            # Standardize to 'chromosome'
            if col != "chromosome":
                df["chromosome"] = df[col]
            break

    # Normalize position columns if they exist (NaN-safe)
    pos_cols = ["Position", "position", "Pos", "pos", "POS", "Start", "start"]
    for col in pos_cols:
        if col in df.columns:
            # Use map with na_action to skip NaN
            df[col] = df[col].map(normalize_position, na_action="ignore")
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
        valid_count = df["coord_key"].notna().sum()
        logger.info(f"Normalized {len(df):,} variants, {valid_count:,} with coord_key")
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
