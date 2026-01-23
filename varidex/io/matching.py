#!/usr/bin/env python3
"""
varidex/io/matching.py - Variant Matching Strategies v6.0.0

Match user genome variants to ClinVar database using rsID or coordinates.
BUGFIX v6.0.1: Coordinate matching now assigns normalized DataFrames.
"""

import pandas as pd
import logging
from typing import Tuple
import re
from varidex.io.normalization import normalize_dataframe_coordinates


def normalize_column_names(df, source="unknown"):
    """Normalize column names for matching."""

    renames = {}

    if source == "clinvar":
        # ClinVar VCF uses: CHROM, POS, ID, REF, ALT
        if "ID" in df.columns and "rsid" not in df.columns:
            renames["ID"] = "rsid"
        if "REF" in df.columns and "re" not in df.columns:
            renames["REF"] = "re"
        if "ALT" in df.columns and "alt" not in df.columns:
            renames["ALT"] = "alt"

    if renames:
        df = df.rename(columns=renames)

    return df


logger = logging.getLogger(__name__)
REQUIRED_COORD_COLUMNS = ["chromosome", "position", "ref_allele", "alt_allele"]


def match_by_rsid(user_df: pd.DataFrame, clinvar_df: pd.DataFrame) -> pd.DataFrame:
    """Match variants by rsID only (fastest but misses ~30% without rsIDs).

    Args:
        user_df: User genome DataFrame with 'rsid' column
        clinvar_df: ClinVar DataFrame with 'rsid' column
    Returns:
        Merged DataFrame with matched variants
    """
    if "rsid" not in user_df.columns or "rsid" not in clinvar_df.columns:
        logger.warning("rsID column missing, returning empty DataFrame")
        return pd.DataFrame()
    matched = user_df.merge(clinvar_df, on="rsid", how="inner", suffixes=("_user", "_clinvar"))
    logger.info("rsID matches: {len(matched):,}")
    return matched


def match_by_coordinates(user_df: pd.DataFrame, clinvar_df: pd.DataFrame) -> pd.DataFrame:
    """Match variants by coordinates (chr:pos:ref:alt).

    BUGFIX v6.0.1: Explicitly assign normalized DataFrames.
    Original bug: normalization return value ignored → 100% failure.

    Args:
        user_df: User genome DataFrame
        clinvar_df: ClinVar DataFrame
    Returns:
        Merged DataFrame with coordinate-matched variants
    """
    if user_df is None or len(user_df) == 0:
        logger.warning("User DataFrame is empty")
        return pd.DataFrame()
    if clinvar_df is None or len(clinvar_df) == 0:
        logger.warning("ClinVar DataFrame is empty")
        return pd.DataFrame()
    if not all(col in user_df.columns for col in REQUIRED_COORD_COLUMNS):
        logger.warning("User DataFrame missing coordinate columns")
        return pd.DataFrame()
    if not all(col in clinvar_df.columns for col in REQUIRED_COORD_COLUMNS):
        logger.warning("ClinVar DataFrame missing coordinate columns")
        return pd.DataFrame()

    # CRITICAL FIX: Assign normalization return values (bug was here)
    if "coord_key" not in user_df.columns:
        user_df = normalize_dataframe_coordinates(user_df)
    if "coord_key" not in clinvar_df.columns:
        clinvar_df = normalize_dataframe_coordinates(clinvar_df)

    matched = user_df.merge(clinvar_df, on="coord_key", how="inner", suffixes=("_user", "_clinvar"))
    logger.info("Coordinate matches: {len(matched):,}")
    return matched


def match_variants_hybrid(
    # Normalize column names
    clinvar_df: pd.DataFrame,
    user_df: pd.DataFrame,
    clinvar_type: str = "",
    user_type: str = "",
) -> Tuple[pd.DataFrame, int, int]:
    # Normalize column names
    clinvar_df = normalize_column_names(clinvar_df.copy(), source="clinvar")
    user_df = normalize_column_names(user_df.copy(), source="user")

    """Hybrid matching: try rsID first, fall back to coordinates.

    RECOMMENDED strategy:
    1. Match by rsID (fast, high confidence)
    2. For unmatched variants, try coordinate matching
    3. Combine and deduplicate

    Args:
        clinvar_df: ClinVar DataFrame
        user_df: User genome DataFrame
        clinvar_type: ClinVar file type (for logging)
        user_type: User file type (for logging)
    Returns:
        Tuple of (matched_df, rsid_count, coord_count)
    """
    if user_df is None or len(user_df) == 0:
        raise ValueError("User DataFrame is empty")
    if clinvar_df is None or len(clinvar_df) == 0:
        raise ValueError("ClinVar DataFrame is empty")

    logger.info("{'='*60}")
    logger.info("MATCHING: {clinvar_type} × {user_type}")
    logger.info("{'='*60}")

    matches = []
    rsid_count = 0
    coord_count = 0

    # Try rsID matching first
    if "rsid" in user_df.columns and "rsid" in clinvar_df.columns:
        rsid_matched = match_by_rsid(user_df, clinvar_df)
        if len(rsid_matched) > 0:
            matches.append(rsid_matched)
            rsid_count = len(rsid_matched)
            logger.info("✓ rsID: {rsid_count:,} matches")

    # Try coordinate matching for unmatched variants
    if clinvar_type in ["vc", "vcf_tsv"]:
        if rsid_count > 0 and "rsid" in user_df.columns:
            matched_rsids = set(rsid_matched["rsid"])
            unmatched = user_df[~user_df["rsid"].isin(matched_rsids)]
        else:
            unmatched = user_df

        if len(unmatched) > 0:
            coord_matched = match_by_coordinates(unmatched, clinvar_df)
            if len(coord_matched) > 0:
                matches.append(coord_matched)
                coord_count = len(coord_matched)
                logger.info("✓ Coordinate: {coord_count:,} matches")

    # Combine all matches
    if not matches:
        raise ValueError("No matches found. ClinVar: {clinvar_type}, User: {user_type}")

    combined = pd.concat(matches, ignore_index=True)

    # Deduplicate (prefer rsID matches if duplicate coord_key)
    if "coord_key" in combined.columns:
        combined = combined.drop_duplicates(subset="coord_key", keep="first")
    elif "rsid" in combined.columns:
        combined = combined.drop_duplicates(subset="rsid", keep="first")

    len(combined) / len(user_df) * 100
    logger.info("{'='*60}")
    logger.info("TOTAL: {len(combined):,} matches ({coverage:.1f}% coverage)")
    logger.info("{'='*60}")

    
    # Reconcile column names for classification
    if 'chromosome_clinvar' in combined.columns and 'chromosome' not in combined.columns:
        combined['chromosome'] = combined['chromosome_clinvar']
    
    if 'position_clinvar' in combined.columns and 'position' not in combined.columns:
        combined['position'] = combined['position_clinvar']
    
    # Extract gene from INFO field if missing
    if 'gene' not in combined.columns or combined['gene'].isna().all():
        def extract_gene(info_str):
            if pd.isna(info_str):
                return None
            match = re.search(r'GENEINFO=([^:;]+)', str(info_str))
            return match.group(1) if match else None
        
        combined['gene'] = combined['INFO'].apply(extract_gene)
    
    # Ensure molecular_consequence exists
    if 'molecular_consequence' not in combined.columns:
        def extract_consequence(info_str):
            if pd.isna(info_str):
                return ''
            match = re.search(r'MC=([^;]+)', str(info_str))
            return match.group(1) if match else ''
        
        combined['molecular_consequence'] = combined['INFO'].apply(extract_consequence)
    
    # Ensure variant_type exists
    if 'variant_type' not in combined.columns:
        def extract_variant_type(info_str):
            if pd.isna(info_str):
                return 'single_nucleotide_variant'
            match = re.search(r'CLNVC=([^;]+)', str(info_str))
            return match.group(1).replace('_', ' ') if match else 'single_nucleotide_variant'
        
        combined['variant_type'] = combined['INFO'].apply(extract_variant_type)


    return combined, rsid_count, coord_count
