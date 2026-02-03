#!/usr/bin/env python3
"""
varidex/io/matching.py - Variant Matching Engine v3.0.1
========================================================
Efficient matching of user variants against reference databases.
Enhanced with comprehensive parameter support for all test scenarios.

Changes v3.0.1 (2026-02-02) - TEST COMPATIBILITY FIX:
- Added missing MatchingError import
- Added match_alleles parameter to match_by_coordinates()
- Added position_tolerance, allow_allele_mismatch to find_fuzzy_matches()
- Added mode, tolerance parameters to match_variants()
- Enhanced find_exact_matches() to handle both list and DataFrame inputs
- Fixed column name mapping for test compatibility (chromosome/chrom, position/pos)
- All 18 failing matching tests should now pass

Previous version: v3.0.0
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Union, Set
import logging

# CRITICAL FIX: Add missing exception import
from varidex.exceptions import MatchingError
from varidex.core.models import VariantData, Variant

logger = logging.getLogger(__name__)


def create_variant_key(
    chromosome: str,
    position: Union[int, str],
    ref_allele: str = "",
    alt_allele: str = "",
) -> str:
    """
    Create unique variant key for matching.

    Args:
        chromosome: Chromosome identifier
        position: Genomic position
        ref_allele: Reference allele (optional)
        alt_allele: Alternate allele (optional)

    Returns:
        Unique variant key string
    """
    # Normalize chromosome (remove chr prefix, uppercase)
    chrom = str(chromosome).upper().replace("CHR", "")
    pos = str(position)
    ref = str(ref_allele).upper() if ref_allele else ""
    alt = str(alt_allele).upper() if alt_allele else ""

    if ref and alt:
        return f"{chrom}:{pos}:{ref}:{alt}"
    else:
        return f"{chrom}:{pos}"


def _normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize column names to handle multiple naming conventions.

    Maps: chrom->chromosome, pos->position, ref->ref_allele, alt->alt_allele

    Args:
        df: DataFrame with variant data

    Returns:
        DataFrame with normalized column names
    """
    df = df.copy()

    # Column name mappings (test names -> internal names)
    column_map = {
        'chrom': 'chromosome',
        'pos': 'position',
        'ref': 'ref_allele',
        'alt': 'alt_allele',
        'reference': 'ref_allele',
        'alternate': 'alt_allele',
    }

    # Apply mappings
    for old_name, new_name in column_map.items():
        if old_name in df.columns and new_name not in df.columns:
            df = df.rename(columns={old_name: new_name})

    return df


def match_by_coordinates(
    user_df: pd.DataFrame,
    reference_df: pd.DataFrame,
    match_alleles: bool = True,  # FIX: Added missing parameter
) -> pd.DataFrame:
    """
    Match variants by genomic coordinates.

    FIX v3.0.1: Added match_alleles parameter for test compatibility.

    Args:
        user_df: User variant DataFrame
        reference_df: Reference variant DataFrame
        match_alleles: If True, require allele match; if False, coordinate-only match

    Returns:
        DataFrame with matched variants
    """
    # Normalize column names for both DataFrames
    user_df = _normalize_column_names(user_df)
    reference_df = _normalize_column_names(reference_df)

    # Required columns for coordinate matching
    coord_cols = ['chromosome', 'position']

    # Check if coordinate columns exist
    missing_user = [col for col in coord_cols if col not in user_df.columns]
    missing_ref = [col for col in coord_cols if col not in reference_df.columns]

    if missing_user:
        logger.warning(f"User DataFrame missing coordinate columns")
        return pd.DataFrame()

    if missing_ref:
        logger.warning(f"Reference DataFrame missing coordinate columns")
        return pd.DataFrame()

    # Determine merge columns based on match_alleles parameter
    if match_alleles:
        # Require allele match
        merge_cols = ['chromosome', 'position', 'ref_allele', 'alt_allele']
        # Check if allele columns exist
        if 'ref_allele' not in user_df.columns or 'alt_allele' not in user_df.columns:
            logger.warning("Allele columns missing, falling back to coordinate-only match")
            merge_cols = coord_cols
    else:
        # Coordinate-only match
        merge_cols = coord_cols

    # Ensure position is int for proper matching
    user_df = user_df.copy()
    reference_df = reference_df.copy()
    user_df['position'] = pd.to_numeric(user_df['position'], errors='coerce')
    reference_df['position'] = pd.to_numeric(reference_df['position'], errors='coerce')

    # Perform merge
    try:
        result = user_df.merge(
            reference_df,
            on=merge_cols,
            how='inner',
            suffixes=('_user', '_ref')
        )
        logger.info(f"Matched {len(result)} variants by coordinates (match_alleles={match_alleles})")
        return result
    except Exception as e:
        logger.error(f"Error matching by coordinates: {e}")
        return pd.DataFrame()


def match_by_variant_id(
    user_df: pd.DataFrame,
    reference_df: pd.DataFrame,
    id_column: str = 'rsid',
) -> pd.DataFrame:
    """
    Match variants by variant ID (e.g., rsID).

    Args:
        user_df: User variant DataFrame
        reference_df: Reference variant DataFrame
        id_column: Column name containing variant IDs

    Returns:
        DataFrame with matched variants
    """
    # Check if ID column exists
    if id_column not in user_df.columns:
        raise MatchingError(f"Column '{id_column}' not found in user variants")

    if id_column not in reference_df.columns:
        raise MatchingError(f"Column '{id_column}' not found in reference variants")

    # Perform merge on ID column
    result = user_df.merge(
        reference_df,
        on=id_column,
        how='inner',
        suffixes=('_user', '_ref')
    )

    logger.info(f"Matched {len(result)} variants by {id_column}")
    return result


def match_variants(
    user_df: pd.DataFrame,
    reference_df: pd.DataFrame,
    mode: str = "exact",  # FIX: Added missing parameter
    tolerance: int = 0,    # FIX: Added missing parameter
) -> pd.DataFrame:
    """
    Main variant matching function with multiple modes.

    FIX v3.0.1: Added mode and tolerance parameters for test compatibility.

    Args:
        user_df: User variant DataFrame
        reference_df: Reference variant DataFrame
        mode: Matching mode - "exact" or "fuzzy"
        tolerance: Position tolerance for fuzzy matching (in base pairs)

    Returns:
        DataFrame with matched variants

    Raises:
        MatchingError: If required columns are missing or mode is invalid
    """
    # Normalize column names
    user_df = _normalize_column_names(user_df)
    reference_df = _normalize_column_names(reference_df)

    # Validate required columns
    required_cols = ['chromosome', 'position']

    for col in required_cols:
        if col not in user_df.columns:
            raise MatchingError(f"Column '{col}' not found in user variants")
        if col not in reference_df.columns:
            raise MatchingError(f"Column '{col}' not found in ClinVar data")

    # Validate mode
    if mode not in ["exact", "fuzzy"]:
        raise MatchingError(f"Invalid mode '{mode}'. Must be 'exact' or 'fuzzy'")

    # Perform matching based on mode
    if mode == "exact":
        return match_by_coordinates(user_df, reference_df, match_alleles=True)
    else:  # fuzzy mode
        # Use find_fuzzy_matches for fuzzy matching
        # Convert DataFrames to list of variants for fuzzy matching
        user_variants = user_df.to_dict('records')
        reference_variants = reference_df.to_dict('records')

        matches = find_fuzzy_matches(
            user_variants,
            reference_variants,
            position_tolerance=tolerance,
            allow_allele_mismatch=True
        )

        return pd.DataFrame(matches) if matches else pd.DataFrame()


def find_exact_matches(
    variants: Union[List[VariantData], List[Dict], pd.DataFrame],
    reference: Union[List[VariantData], List[Dict], pd.DataFrame],
    assembly: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Find exact matches between variant lists.

    FIX v3.0.1: Enhanced to handle list, dict, and DataFrame inputs.

    Args:
        variants: Query variants (list of Variant objects, dicts, or DataFrame)
        reference: Reference variants (list of Variant objects, dicts, or DataFrame)
        assembly: Optional assembly filter (e.g., "GRCh38")

    Returns:
        List of matched variant dictionaries
    """
    # Convert inputs to DataFrame if needed
    if isinstance(variants, list):
        if len(variants) == 0:
            return []

        # Check if list contains Variant objects or dicts
        if hasattr(variants[0], 'to_dict'):
            # List of Variant objects
            variants_df = pd.DataFrame([v.to_dict() for v in variants])
        else:
            # List of dicts
            variants_df = pd.DataFrame(variants)
    else:
        variants_df = variants.copy()

    if isinstance(reference, list):
        if len(reference) == 0:
            return []

        if hasattr(reference[0], 'to_dict'):
            reference_df = pd.DataFrame([v.to_dict() for v in reference])
        else:
            reference_df = pd.DataFrame(reference)
    else:
        reference_df = reference.copy()

    # Normalize column names
    variants_df = _normalize_column_names(variants_df)
    reference_df = _normalize_column_names(reference_df)

    # Define match columns (chromosome, position, ref, alt)
    match_cols = ['chromosome', 'position', 'ref_allele', 'alt_allele']

    # Filter by assembly if specified
    if assembly:
        if 'assembly' in variants_df.columns:
            variants_df = variants_df[variants_df['assembly'] == assembly]
        if 'assembly' in reference_df.columns:
            reference_df = reference_df[reference_df['assembly'] == assembly]

    # Ensure position is int
    variants_df['position'] = pd.to_numeric(variants_df['position'], errors='coerce')
    reference_df['position'] = pd.to_numeric(reference_df['position'], errors='coerce')

    # Perform exact match
    matched = variants_df.merge(reference_df, on=match_cols, how="inner")

    logger.info(f"Found {len(matched)} exact matches")
    return matched.to_dict('records')


def find_fuzzy_matches(
    variants: Union[List[VariantData], List[Dict]],
    reference: Union[List[VariantData], List[Dict]],
    position_tolerance: int = 0,        # FIX: Added missing parameter
    allow_allele_mismatch: bool = False,  # FIX: Added missing parameter
) -> List[Dict[str, Any]]:
    """
    Find fuzzy matches allowing position tolerance and optional allele mismatch.

    FIX v3.0.1: Added position_tolerance and allow_allele_mismatch parameters.

    Args:
        variants: Query variants (list of Variant objects or dicts)
        reference: Reference variants (list of Variant objects or dicts)
        position_tolerance: Maximum position difference for match (default: 0)
        allow_allele_mismatch: If True, match on coordinates only (default: False)

    Returns:
        List of matched variant dictionaries
    """
    matches = []

    # Convert to dicts if Variant objects
    if len(variants) == 0 or len(reference) == 0:
        return []

    var_dicts = []
    for v in variants:
        if hasattr(v, 'to_dict'):
            var_dicts.append(v.to_dict())
        else:
            var_dicts.append(v)

    ref_dicts = []
    for r in reference:
        if hasattr(r, 'to_dict'):
            ref_dicts.append(r.to_dict())
        else:
            ref_dicts.append(r)

    # Normalize to use consistent field names
    for v in var_dicts:
        if 'chrom' in v and 'chromosome' not in v:
            v['chromosome'] = v['chrom']
        if 'pos' in v and 'position' not in v:
            v['position'] = v['pos']
        if 'ref' in v and 'ref_allele' not in v:
            v['ref_allele'] = v['ref']
        if 'alt' in v and 'alt_allele' not in v:
            v['alt_allele'] = v['alt']

    for r in ref_dicts:
        if 'chrom' in r and 'chromosome' not in r:
            r['chromosome'] = r['chrom']
        if 'pos' in r and 'position' not in r:
            r['position'] = r['pos']
        if 'ref' in r and 'ref_allele' not in r:
            r['ref_allele'] = r['ref']
        if 'alt' in r and 'alt_allele' not in r:
            r['alt_allele'] = r['alt']

    # Perform fuzzy matching
    for query_var in var_dicts:
        query_chrom = str(query_var.get('chromosome', '')).upper().replace('CHR', '')
        query_pos = int(query_var.get('position', 0))
        query_ref = str(query_var.get('ref_allele', '')).upper()
        query_alt = str(query_var.get('alt_allele', '')).upper()

        for ref_var in ref_dicts:
            ref_chrom = str(ref_var.get('chromosome', '')).upper().replace('CHR', '')
            ref_pos = int(ref_var.get('position', 0))
            ref_ref = str(ref_var.get('ref_allele', '')).upper()
            ref_alt = str(ref_var.get('alt_allele', '')).upper()

            # Check chromosome match
            if query_chrom != ref_chrom:
                continue

            # Check position within tolerance
            if abs(query_pos - ref_pos) > position_tolerance:
                continue

            # Check alleles (if required)
            if not allow_allele_mismatch:
                if query_ref != ref_ref or query_alt != ref_alt:
                    continue

            # Match found!
            match = {
                'query': query_var,
                'reference': ref_var,
                'position_diff': abs(query_pos - ref_pos),
                'allele_match': (query_ref == ref_ref and query_alt == ref_alt)
            }
            matches.append(match)

    logger.info(f"Found {len(matches)} fuzzy matches (tolerance={position_tolerance}, allow_mismatch={allow_allele_mismatch})")
    return matches


# Additional utility functions for completeness

def deduplicate_matches(matches: pd.DataFrame) -> pd.DataFrame:
    """
    Remove duplicate matches, keeping the best match per variant.

    Args:
        matches: DataFrame with matched variants

    Returns:
        Deduplicated DataFrame
    """
    if matches.empty:
        return matches

    # If variant_key column exists, use it for deduplication
    if 'variant_key' in matches.columns:
        return matches.drop_duplicates(subset=['variant_key'], keep='first')

    # Otherwise, deduplicate on coordinate columns
    coord_cols = ['chromosome', 'position']
    if all(col in matches.columns for col in coord_cols):
        return matches.drop_duplicates(subset=coord_cols, keep='first')

    return matches


if __name__ == "__main__":
    print("=" * 80)
    print("MATCHING MODULE v3.0.1 - TEST COMPATIBILITY FIX")
    print("=" * 80)
    print("\nFixes applied:")
    print("  ✓ Added MatchingError import")
    print("  ✓ Added match_alleles parameter to match_by_coordinates()")
    print("  ✓ Added position_tolerance, allow_allele_mismatch to find_fuzzy_matches()")
    print("  ✓ Added mode, tolerance parameters to match_variants()")
    print("  ✓ Enhanced find_exact_matches() to handle list inputs")
    print("  ✓ Fixed column name mapping for test compatibility")
    print("\n✅ All 18 matching test failures should now be resolved!")
    print("=" * 80)
