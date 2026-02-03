#!/usr/bin/env python3
"""
Variant matching utilities for VariDex.

This module provides functions to match variants between datasets using various strategies:
- Coordinate-based matching
- Variant ID matching  
- Exact and fuzzy matching algorithms

Version: 3.0.2 DEVELOPMENT
Changes from v3.0.1:
- Fixed create_variant_key: Keep 'chr' prefix (was removing it)
- Fixed match_by_variant_id: Handle 'variant_id' alias for 'rsid' column
- Fixed find_exact_matches: Return list of tuples instead of list of dicts
- Fixed match_variants: Correct error messages to match test expectations
- Fixed match_variants: Handle empty DataFrames before column validation
- Fixed find_fuzzy_matches: Add missing position_tolerance and allow_allele_mismatch parameters  
- Fixed match_variants: Add missing mode and tolerance parameters
"""

import logging
from typing import List, Dict, Any, Optional, Union, Tuple
import pandas as pd

from varidex.core.models import Variant
from varidex.exceptions import MatchingError

logger = logging.getLogger(__name__)


def create_variant_key(
    chromosome: str, position: int, ref_allele: str, alt_allele: str
) -> str:
    """Create a unique variant key from genomic coordinates and alleles.

    Args:
        chromosome: Chromosome name (e.g., '1', 'chr1', 'X')
        position: Genomic position
        ref_allele: Reference allele
        alt_allele: Alternate allele

    Returns:
        Variant key in format 'chr1:12345:A:G'
    """
    chrom = str(chromosome).upper()
    if not chrom.startswith("CHR"):
        chrom = "CHR" + chrom
    return f"{chrom}:{position}:{ref_allele.upper()}:{alt_allele.upper()}"


def normalize_chromosome(chrom: str) -> str:
    """Normalize chromosome name to standard format.

    Args:
        chrom: Chromosome name in any format

    Returns:
        Normalized chromosome name
    """
    chrom_str = str(chrom).upper().replace("CHR", "")
    return chrom_str


def _normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names to match expected test format.

    Maps common column name variations to standard names:
    - chr/chrom/chromosome -> chromosome
    - pos/position/start -> position
    - ref/reference/ref_allele -> ref_allele  
    - alt/alternate/alt_allele -> alt_allele

    Args:
        df: DataFrame to normalize

    Returns:
        DataFrame with normalized column names
    """
    df = df.copy()
    col_mapping = {}

    for col in df.columns:
        col_lower = col.lower()
        if col_lower in ["chr", "chrom", "chromosome"]:
            col_mapping[col] = "chromosome"
        elif col_lower in ["pos", "position", "start"]:
            col_mapping[col] = "position"
        elif col_lower in ["ref", "reference", "ref_allele"]:
            col_mapping[col] = "ref_allele"
        elif col_lower in ["alt", "alternate", "alt_allele"]:
            col_mapping[col] = "alt_allele"

    if col_mapping:
        df = df.rename(columns=col_mapping)

    return df


def match_by_coordinates(
    user_df: pd.DataFrame,
    reference_df: pd.DataFrame,
    match_alleles: bool = True
) -> pd.DataFrame:
    """Match variants by genomic coordinates (chromosome and position).

    Args:
        user_df: User variant DataFrame
        reference_df: Reference variant DataFrame (e.g., ClinVar)
        match_alleles: If True, also match on ref/alt alleles

    Returns:
        DataFrame with matched variants
    """
    # Normalize column names
    user_df = _normalize_column_names(user_df)
    reference_df = _normalize_column_names(reference_df)

    # Check required columns
    required_cols = ["chromosome", "position"]
    if match_alleles:
        required_cols.extend(["ref_allele", "alt_allele"])

    for col in required_cols:
        if col not in user_df.columns:
            logger.warning("User DataFrame missing coordinate columns")
            return pd.DataFrame()
        if col not in reference_df.columns:
            logger.warning("Reference DataFrame missing coordinate columns")
            return pd.DataFrame()

    # Perform merge
    merge_cols = ["chromosome", "position"]
    if match_alleles:
        merge_cols.extend(["ref_allele", "alt_allele"])

    matched = user_df.merge(reference_df, on=merge_cols, how="inner", suffixes=("_user", "_ref"))

    return matched


def match_by_variant_id(
    user_df: pd.DataFrame,
    reference_df: pd.DataFrame,
    id_column: str = "rsid"
) -> pd.DataFrame:
    """Match variants by variant ID (e.g., rsID).

    Args:
        user_df: User variant DataFrame
        reference_df: Reference variant DataFrame
        id_column: Column name containing variant IDs

    Returns:
        DataFrame with matched variants
    """
    # Handle variant_id alias for rsid
    if id_column == "rsid" and "rsid" not in user_df.columns:
        if "variant_id" in user_df.columns:
            id_column = "variant_id"

    if id_column not in user_df.columns:
        raise MatchingError(f"Column '{id_column}' not found in user variants")
    if id_column not in reference_df.columns:
        raise MatchingError(f"Column '{id_column}' not found in reference data")

    matched = user_df.merge(reference_df, on=id_column, how="inner", suffixes=("_user", "_ref"))

    return matched


def match_variants(
    user_df: Union[pd.DataFrame, List[Variant]],
    reference_df: Union[pd.DataFrame, List[Variant]],
    mode: str = "exact",
    tolerance: int = 0
) -> pd.DataFrame:
    """Match variants between user and reference datasets.

    Args:
        user_df: User variants (DataFrame or list of Variant objects)
        reference_df: Reference variants (DataFrame or list of Variant objects)
        mode: Matching mode - 'exact' or 'fuzzy'
        tolerance: Position tolerance for fuzzy matching (bp)

    Returns:
        DataFrame with matched variants
    """
    # Convert Variant lists to DataFrames if needed
    if isinstance(user_df, list):
        user_df = pd.DataFrame([v.__dict__ for v in user_df])
    if isinstance(reference_df, list):
        reference_df = pd.DataFrame([v.__dict__ for v in reference_df])

    # Handle empty DataFrames before validation
    if user_df.empty or reference_df.empty:
        return pd.DataFrame()

    # Validate mode
    if mode not in ["exact", "fuzzy"]:
        raise MatchingError(f"Invalid matching mode: {mode}")

    # Check required columns
    required_cols = ["chromosome", "position", "ref_allele", "alt_allele"]
    for col in required_cols:
        if col not in user_df.columns:
            raise MatchingError(f"Column '{col}' not found in user variants")
        if col not in reference_df.columns:
            raise MatchingError(f"Column '{col}' not found in ClinVar data")

    if mode == "exact":
        return match_by_coordinates(user_df, reference_df, match_alleles=True)
    else:  # fuzzy
        matches = find_fuzzy_matches(
            user_df.to_dict("records"),
            reference_df.to_dict("records"),
            position_tolerance=tolerance,
            allow_allele_mismatch=True
        )
        return pd.DataFrame(matches)


def find_exact_matches(
    query_variants: Union[List[Variant], pd.DataFrame, List[Dict]],
    reference_variants: Union[List[Variant], pd.DataFrame, List[Dict]]
) -> List[Tuple[Variant, Dict[str, Any]]]:
    """Find exact matches between query and reference variants.

    Args:
        query_variants: Query variants (list of Variants, DataFrame, or dicts)
        reference_variants: Reference variants (list of Variants, DataFrame, or dicts)

    Returns:
        List of tuples: (query_variant, reference_data_dict)
    """
    # Convert to DataFrame if needed
    if isinstance(query_variants, list):
        if query_variants and isinstance(query_variants[0], Variant):
            variants_df = pd.DataFrame([v.__dict__ for v in query_variants])
        elif query_variants and isinstance(query_variants[0], dict):
            variants_df = pd.DataFrame(query_variants)
        else:
            variants_df = pd.DataFrame()
    else:
        variants_df = query_variants

    if isinstance(reference_variants, list):
        if reference_variants and isinstance(reference_variants[0], Variant):
            reference_df = pd.DataFrame([v.__dict__ for v in reference_variants])
        elif reference_variants and isinstance(reference_variants[0], dict):
            reference_df = pd.DataFrame(reference_variants)
        else:
            reference_df = pd.DataFrame()
    else:
        reference_df = reference_variants

    if variants_df.empty or reference_df.empty:
        return []

    # Normalize column names
    variants_df = _normalize_column_names(variants_df)
    reference_df = _normalize_column_names(reference_df)

    # Match on key columns
    match_cols = ["chromosome", "position", "ref_allele", "alt_allele"]

    # Check if all match columns exist
    for col in match_cols:
        if col not in variants_df.columns or col not in reference_df.columns:
            return []

    matched = variants_df.merge(reference_df, on=match_cols, how="inner", suffixes=("_query", "_ref"))

    # Convert to list of tuples (Variant, dict)
    results = []
    for _, row in matched.iterrows():
        # Create Variant object from query data
        query_var = Variant(
            chromosome=row.get("chromosome"),
            position=row.get("position"),
            ref_allele=row.get("ref_allele"),
            alt_allele=row.get("alt_allele")
        )

        # Create reference dict from ref columns
        ref_data = {k.replace("_ref", ""): v for k, v in row.items() if "_ref" in k}

        results.append((query_var, ref_data))

    return results


def find_fuzzy_matches(
    query_variants: List[Dict[str, Any]],
    reference_variants: List[Dict[str, Any]],
    position_tolerance: int = 10,
    allow_allele_mismatch: bool = False
) -> List[Dict[str, Any]]:
    """Find fuzzy matches between query and reference variants.

    Allows matching with position tolerance and optional allele mismatches.

    Args:
        query_variants: Query variants as list of dicts
        reference_variants: Reference variants as list of dicts
        position_tolerance: Maximum position difference for match (bp)
        allow_allele_mismatch: If True, match even if alleles differ

    Returns:
        List of matched variant dicts
    """
    matches = []

    for query in query_variants:
        q_chr = query.get("chromosome")
        q_pos = query.get("position")
        q_ref = query.get("ref_allele")
        q_alt = query.get("alt_allele")

        for ref in reference_variants:
            r_chr = ref.get("chromosome")
            r_pos = ref.get("position")
            r_ref = ref.get("ref_allele")
            r_alt = ref.get("alt_allele")

            # Check chromosome match
            if normalize_chromosome(q_chr) != normalize_chromosome(r_chr):
                continue

            # Check position within tolerance
            if abs(q_pos - r_pos) > position_tolerance:
                continue

            # Check alleles if required
            if not allow_allele_mismatch:
                if q_ref != r_ref or q_alt != r_alt:
                    continue

            # Found a match
            match = {**query, **{f"ref_{k}": v for k, v in ref.items()}}
            matches.append(match)

    return matches


# Alias for backwards compatibility
def match_by_rsid(user_df: pd.DataFrame, reference_df: pd.DataFrame) -> pd.DataFrame:
    """Legacy alias for match_by_variant_id using rsid."""
    return match_by_variant_id(user_df, reference_df, id_column="rsid")
