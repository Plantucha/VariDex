#!/usr/bin/env python3
"""
Variant matching utilities for VariDex.

This module provides functions to match variants between datasets using various strategies:
- Coordinate-based matching
- Variant ID matching
- Exact and fuzzy matching algorithms

Version: 3.0.4 DEVELOPMENT
Changes from v3.0.3:
- Fixed create_variant_key: Return lowercase 'chr' prefix as expected by tests
- Fixed find_fuzzy_matches: Handle Variant objects (not just dicts)
"""

import logging
from typing import Any, Dict, List, Tuple, Union

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
    chrom = str(chromosome)
    # Ensure lowercase 'chr' prefix
    if not chrom.lower().startswith("chr"):
        chrom = "chr" + chrom
    # Keep original case for chromosome number/letter, but lowercase 'chr'
    if chrom.upper().startswith("CHR"):
        chrom = "chr" + chrom[3:]
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


def _get_column_mapping(df: pd.DataFrame) -> Dict[str, str]:
    """Get mapping of actual column names to standardized names.

    Args:
        df: DataFrame to analyze

    Returns:
        Dictionary mapping standard names to actual column names
    """
    mapping = {}

    for col in df.columns:
        col_lower = col.lower()
        if col_lower in ["chr", "chrom", "chromosome"]:
            mapping["chromosome"] = col
        elif col_lower in ["pos", "position", "start"]:
            mapping["position"] = col
        elif col_lower in ["ref", "reference", "ref_allele"]:
            mapping["ref_allele"] = col
        elif col_lower in ["alt", "alternate", "alt_allele"]:
            mapping["alt_allele"] = col
        elif col_lower in ["rsid", "variant_id", "id"]:
            mapping["variant_id"] = col

    return mapping


def match_by_coordinates(
    user_df: pd.DataFrame, reference_df: pd.DataFrame, match_alleles: bool = True
) -> pd.DataFrame:
    """Match variants by genomic coordinates (chromosome and position).

    Args:
        user_df: User variant DataFrame
        reference_df: Reference variant DataFrame (e.g., ClinVar)
        match_alleles: If True, also match on ref/alt alleles

    Returns:
        DataFrame with matched variants
    """
    if user_df.empty or reference_df.empty:
        return pd.DataFrame(columns=user_df.columns.tolist())

    # Get column mappings
    user_mapping = _get_column_mapping(user_df)
    ref_mapping = _get_column_mapping(reference_df)

    # Check required columns
    required = ["chromosome", "position"]
    if match_alleles:
        required.extend(["ref_allele", "alt_allele"])

    for col in required:
        if col not in user_mapping:
            logger.warning(f"User DataFrame missing {col} column")
            return pd.DataFrame(columns=user_df.columns.tolist())
        if col not in ref_mapping:
            logger.warning(f"Reference DataFrame missing {col} column")
            return pd.DataFrame(columns=user_df.columns.tolist())

    # Create temporary DataFrames with normalized names
    user_temp = user_df.copy()
    ref_temp = reference_df.copy()

    # Build merge columns
    merge_on = []
    for std_name in required:
        user_col = user_mapping[std_name]
        ref_col = ref_mapping[std_name]

        # Rename to common name for merge
        temp_name = f"_merge_{std_name}"
        user_temp[temp_name] = user_temp[user_col]
        ref_temp[temp_name] = ref_temp[ref_col]
        merge_on.append(temp_name)

    # Perform merge
    matched = user_temp.merge(ref_temp, on=merge_on, how="inner", suffixes=("", "_ref"))

    # Drop temporary merge columns
    matched = matched.drop(columns=merge_on)

    return matched


def match_by_variant_id(
    user_df: pd.DataFrame, reference_df: pd.DataFrame, id_column: str = "rsID"
) -> pd.DataFrame:
    """Match variants by variant ID (e.g., rsID).

    Args:
        user_df: User variant DataFrame
        reference_df: Reference variant DataFrame
        id_column: Column name containing variant IDs

    Returns:
        DataFrame with matched variants
    """
    if user_df.empty or reference_df.empty:
        return pd.DataFrame(columns=user_df.columns.tolist())

    # Find the actual column name (case-insensitive)
    user_col = None
    ref_col = None

    id_lower = id_column.lower()

    for col in user_df.columns:
        if col.lower() == id_lower or col.lower() in ["rsid", "variant_id", "id"]:
            user_col = col
            break

    for col in reference_df.columns:
        if col.lower() == id_lower or col.lower() in ["rsid", "variant_id", "id"]:
            ref_col = col
            break

    if user_col is None:
        logger.warning(
            f"Column '{id_column}' not found in user variants. "
            f"Available: {list(user_df.columns)}"
        )
        raise MatchingError(f"Column '{id_column}' not found in user variants")

    if ref_col is None:
        raise MatchingError(f"Column '{id_column}' not found in reference data")

    # Merge on the actual column names
    matched = user_df.merge(
        reference_df,
        left_on=user_col,
        right_on=ref_col,
        how="inner",
        suffixes=("", "_ref"),
    )

    return matched


def match_variants(
    user_df: Union[pd.DataFrame, List[Variant]],
    reference_df: Union[pd.DataFrame, List[Variant]],
    mode: str = "exact",
    tolerance: int = 0,
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
        if user_df and hasattr(user_df[0], "__dict__"):
            user_df = pd.DataFrame([v.__dict__ for v in user_df])
        else:
            user_df = pd.DataFrame()

    if isinstance(reference_df, list):
        if reference_df and hasattr(reference_df[0], "__dict__"):
            reference_df = pd.DataFrame([v.__dict__ for v in reference_df])
        else:
            reference_df = pd.DataFrame()

    # Handle empty DataFrames
    if user_df.empty or reference_df.empty:
        return pd.DataFrame()

    # Validate mode
    if mode not in ["exact", "fuzzy"]:
        raise MatchingError(f"Invalid matching mode: {mode}")

    # Check required columns exist
    user_mapping = _get_column_mapping(user_df)
    ref_mapping = _get_column_mapping(reference_df)

    required = ["chromosome", "position"]
    for col in required:
        if col not in user_mapping:
            logger.warning(f"User DataFrame columns: {list(user_df.columns)}")
            raise MatchingError("Required columns not found in user variants")
        if col not in ref_mapping:
            raise MatchingError("Required columns not found in ClinVar data")

    if mode == "exact":
        return match_by_coordinates(user_df, reference_df, match_alleles=True)
    else:  # fuzzy
        # Get actual column names
        user_cols = user_mapping
        ref_cols = ref_mapping

        # Convert to list of dicts with standardized names
        query_list = []
        for _, row in user_df.iterrows():
            record = {}
            for std_name, actual_name in user_cols.items():
                record[std_name] = row[actual_name]
            # Add all other columns
            for col in user_df.columns:
                if col not in user_cols.values():
                    record[col] = row[col]
            query_list.append(record)

        ref_list = []
        for _, row in reference_df.iterrows():
            record = {}
            for std_name, actual_name in ref_cols.items():
                record[std_name] = row[actual_name]
            # Add all other columns
            for col in reference_df.columns:
                if col not in ref_cols.values():
                    record[col] = row[col]
            ref_list.append(record)

        matches = find_fuzzy_matches(
            query_list,
            ref_list,
            position_tolerance=tolerance,
            allow_allele_mismatch=True,
        )

        return pd.DataFrame(matches)


def find_exact_matches(
    query_variants: Union[List[Variant], pd.DataFrame, List[Dict]],
    reference_variants: Union[List[Variant], pd.DataFrame, List[Dict]],
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
        if query_variants and hasattr(query_variants[0], "__dict__"):
            variants_df = pd.DataFrame([v.__dict__ for v in query_variants])
        elif query_variants and isinstance(query_variants[0], dict):
            variants_df = pd.DataFrame(query_variants)
        else:
            return []
    else:
        variants_df = query_variants.copy()

    if isinstance(reference_variants, list):
        if reference_variants and hasattr(reference_variants[0], "__dict__"):
            reference_df = pd.DataFrame([v.__dict__ for v in reference_variants])
        elif reference_variants and isinstance(reference_variants[0], dict):
            reference_df = pd.DataFrame(reference_variants)
        else:
            return []
    else:
        reference_df = reference_variants.copy()

    if variants_df.empty or reference_df.empty:
        return []

    # Get column mappings
    query_mapping = _get_column_mapping(variants_df)
    ref_mapping = _get_column_mapping(reference_df)

    # Check required columns
    required = ["chromosome", "position", "ref_allele", "alt_allele"]
    for col in required:
        if col not in query_mapping or col not in ref_mapping:
            return []

    # Create standardized temp DataFrames for matching
    query_temp = pd.DataFrame()
    ref_temp = pd.DataFrame()

    for std_name in required:
        query_temp[std_name] = variants_df[query_mapping[std_name]]
        ref_temp[std_name] = reference_df[ref_mapping[std_name]]

    # Ensure position is integer
    query_temp["position"] = query_temp["position"].astype(int)
    ref_temp["position"] = ref_temp["position"].astype(int)

    # Match
    matched = query_temp.merge(ref_temp, on=required, how="inner")

    if matched.empty:
        return []

    # Build results as list of tuples
    results = []
    for _, row in matched.iterrows():
        # Create Variant object with correct field names
        query_var = Variant(
            chromosome=row["chromosome"],
            position=int(row["position"]),
            ref_allele=row["ref_allele"],
            alt_allele=row["alt_allele"],
        )

        # Reference data as dict
        ref_data = {
            "chromosome": row["chromosome"],
            "position": int(row["position"]),
            "ref_allele": row["ref_allele"],
            "alt_allele": row["alt_allele"],
        }

        results.append((query_var, ref_data))

    return results


def find_fuzzy_matches(
    query_variants: Union[List[Dict[str, Any]], List[Variant]],
    reference_variants: Union[List[Dict[str, Any]], List[Variant]],
    position_tolerance: int = 10,
    allow_allele_mismatch: bool = False,
) -> List[Dict[str, Any]]:
    """Find fuzzy matches between query and reference variants.

    Allows matching with position tolerance and optional allele mismatches.

    Args:
        query_variants: Query variants as list of dicts or Variant objects
        reference_variants: Reference variants as list of dicts or Variant objects
        position_tolerance: Maximum position difference for match (bp)
        allow_allele_mismatch: If True, match even if alleles differ

    Returns:
        List of matched variant dicts
    """
    # Convert Variant objects to dicts if needed
    query_list = []
    for q in query_variants:
        if hasattr(q, "__dict__"):
            query_list.append(q.__dict__)
        elif isinstance(q, dict):
            query_list.append(q)
        else:
            query_list.append(q)

    ref_list = []
    for r in reference_variants:
        if hasattr(r, "__dict__"):
            ref_list.append(r.__dict__)
        elif isinstance(r, dict):
            ref_list.append(r)
        else:
            ref_list.append(r)

    matches = []

    for query in query_list:
        q_chr = query.get("chromosome")
        q_pos = query.get("position")
        q_ref = query.get("ref_allele")
        q_alt = query.get("alt_allele")

        # Convert position to int if needed
        if isinstance(q_pos, str):
            q_pos = int(q_pos)

        for ref in ref_list:
            r_chr = ref.get("chromosome")
            r_pos = ref.get("position")
            r_ref = ref.get("ref_allele")
            r_alt = ref.get("alt_allele")

            # Convert position to int if needed
            if isinstance(r_pos, str):
                r_pos = int(r_pos)

            # Check chromosome match
            if normalize_chromosome(str(q_chr)) != normalize_chromosome(str(r_chr)):
                continue

            # Check position within tolerance
            if abs(q_pos - r_pos) > position_tolerance:
                continue

            # Check alleles if required
            if not allow_allele_mismatch:
                if q_ref != r_ref or q_alt != r_alt:
                    continue

            # Found a match - merge query and ref data
            match = {**query}
            # Add reference data with ref_ prefix
            for k, v in ref.items():
                if k not in match:
                    match[k] = v
            matches.append(match)

    return matches


def match_by_rsid(user_df: pd.DataFrame, reference_df: pd.DataFrame) -> pd.DataFrame:
    """Legacy alias for match_by_variant_id using rsid."""
    return match_by_variant_id(user_df, reference_df, id_column="rsID")
