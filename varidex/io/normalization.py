"""
VariDex IO Normalization Module
================================
Data normalization utilities for variant data.
"""

from typing import Any
import pandas as pd


def normalize_chromosome(chrom: str) -> str:
    """
    Normalize chromosome name.

    Args:
        chrom: Chromosome name (e.g., "chr1", "1", "chrX")

    Returns:
        Normalized chromosome name
    """
    # Remove 'chr' prefix if present
    chrom = str(chrom).replace("chr", "").replace("Chr", "").replace("CHR", "")

    # Normalize MT/M to MT
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


def normalize_ref_alt(ref: str, alt: str) -> tuple:
    """
    Normalize reference and alternate alleles.

    Args:
        ref: Reference allele
        alt: Alternate allele

    Returns:
        Tuple of (normalized_ref, normalized_alt)
    """
    # Convert to uppercase
    ref = str(ref).upper().strip()
    alt = str(alt).upper().strip()

    # Remove common prefixes
    while len(ref) > 1 and len(alt) > 1 and ref[0] == alt[0]:
        ref = ref[1:]
        alt = alt[1:]

    return (ref, alt)


def normalize_dataframe_coordinates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize chromosome coordinates in a dataframe.

    Args:
        df: DataFrame with columns like 'Chromosome', 'Position', etc.

    Returns:
        DataFrame with normalized coordinates
    """
    df = df.copy()

    # Normalize chromosome column if it exists
    chrom_cols = ["Chromosome", "chromosome", "Chr", "chr", "CHROM"]
    for col in chrom_cols:
        if col in df.columns:
            df[col] = df[col].apply(normalize_chromosome)
            break

    # Normalize position columns if they exist
    pos_cols = ["Position", "position", "Pos", "pos", "POS", "Start", "start"]
    for col in pos_cols:
        if col in df.columns:
            df[col] = df[col].apply(normalize_position)

    return df


__all__ = [
    "normalize_chromosome",
    "normalize_position",
    "normalize_ref_alt",
    "normalize_dataframe_coordinates",
]
