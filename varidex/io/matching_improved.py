#!/usr/bin/env python3
"""
varidex/io/matching_improved.py - Improved Variant Matching v6.5.1

Enhancements over matching.py:
1. 23andMe genotype verification (prevents false positives)
2. Match confidence scoring (0.0-1.0 quality metric)
3. Better deduplication (keeps highest quality matches)
4. More robust error handling

BUGFIX v6.5.1: Fixed column suffix handling and genotype logic
"""

import pandas as pd
import logging
from typing import Tuple, Dict, Any, List, Set, Optional
import re
from varidex.io.normalization import (
    normalize_dataframe_coordinates,
    create_coord_key,
)

logger = logging.getLogger(__name__)

REQUIRED_COORD_COLUMNS: List[str] = [
    "chromosome",
    "position",
    "ref_allele",
    "alt_allele",
]


def calculate_match_confidence(
    match_type: str, review_status: Optional[int] = None, **kwargs
) -> float:
    """
    Calculate confidence score for variant match.

    Args:
        match_type: Type of match performed
        review_status: ClinVar review stars (0-4)
        **kwargs: Additional factors (reserved for future)

    Returns:
        Confidence score between 0.0 and 1.0
    """
    base_scores = {
        "rsid_and_coords": 1.0,  # Perfect: rsID + coordinates match
        "rsid_only": 0.8,  # Good but coordinates not verified
        "coords_exact": 0.95,  # Excellent: chr:pos:ref:alt match
        "coords_normalized": 0.9,  # Very good: after left-alignment
        "position_with_allele": 0.7,  # Fair: 23andMe with genotype check
        "position_only": 0.3,  # Risky: position match only
    }

    confidence = base_scores.get(match_type, 0.5)

    # Adjust for ClinVar review status
    if review_status is not None:
        if review_status >= 3:
            confidence *= 1.0  # Trusted, no penalty
        elif review_status == 2:
            confidence *= 0.9
        elif review_status == 1:
            confidence *= 0.8
        else:
            confidence *= 0.6  # Low confidence data

    return min(confidence, 1.0)


def match_by_rsid(user_df: pd.DataFrame, clinvar_df: pd.DataFrame) -> pd.DataFrame:
    """
    Match variants by rsID only.

    Args:
        user_df: User genome DataFrame with 'rsid' column
        clinvar_df: ClinVar DataFrame with 'rsid' column

    Returns:
        Merged DataFrame with matched variants
    """
    if "rsid" not in user_df.columns or "rsid" not in clinvar_df.columns:
        logger.warning("rsID column missing")
        return pd.DataFrame()

    matched = user_df.merge(
        clinvar_df, on="rsid", how="inner", suffixes=("_user", "_clinvar")
    )

    # Add confidence score
    matched["match_confidence"] = matched.apply(
        lambda row: calculate_match_confidence(
            "rsid_only",
            review_status=row.get("review_status", None),
        ),
        axis=1,
    )

    logger.info(f"rsID matches: {len(matched):,}")
    return matched


def match_by_coordinates(
    user_df: pd.DataFrame, clinvar_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Match variants by coordinates (chr:pos:ref:alt).

    Uses improved normalization with coord_key creation.

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
        logger.warning(f"User DataFrame missing: {REQUIRED_COORD_COLUMNS}")
        return pd.DataFrame()

    if not all(col in clinvar_df.columns for col in REQUIRED_COORD_COLUMNS):
        logger.warning(f"ClinVar DataFrame missing: {REQUIRED_COORD_COLUMNS}")
        return pd.DataFrame()

    # Create coord_key using improved normalization
    if "coord_key" not in user_df.columns:
        user_df = create_coord_key(user_df)

    if "coord_key" not in clinvar_df.columns:
        clinvar_df = create_coord_key(clinvar_df)

    # Merge on coordinate key
    matched = user_df.merge(
        clinvar_df, on="coord_key", how="inner", suffixes=("_user", "_clinvar")
    )

    # Add confidence score
    matched["match_confidence"] = matched.apply(
        lambda row: calculate_match_confidence(
            "coords_exact",
            review_status=row.get("review_status", None),
        ),
        axis=1,
    )

    logger.info(f"Coordinate matches: {len(matched):,}")
    return matched


def match_by_position_23andme_improved(
    user_df: pd.DataFrame, clinvar_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Match 23andMe variants by position AND verify genotype matches alleles.

    IMPROVEMENT over original: Checks if genotype is consistent with
    ClinVar ref/alt alleles to prevent false positives.

    Args:
        user_df: 23andMe DataFrame with chromosome, position, genotype
        clinvar_df: ClinVar DataFrame with chromosome, position, ref, alt

    Returns:
        Merged DataFrame with verified position matches
    """
    if not all(col in user_df.columns for col in ["chromosome", "position"]):
        logger.warning("User DataFrame missing position columns")
        return pd.DataFrame()

    if not all(col in clinvar_df.columns for col in ["chromosome", "position"]):
        logger.warning("ClinVar DataFrame missing position columns")
        return pd.DataFrame()

    # Merge on chromosome and position
    merged = user_df.merge(
        clinvar_df,
        on=["chromosome", "position"],
        how="inner",
        suffixes=("_user", "_clinvar"),
    )

    if len(merged) == 0:
        return pd.DataFrame()

    # Verify genotype matches ref/alt alleles
    def genotype_matches(row: pd.Series) -> bool:
        """Check if genotype is consistent with ref/alt."""
        try:
            # CRITICAL FIX: Handle column suffixes after merge
            genotype = str(row.get("genotype", "")).upper()
            
            # Try different possible column names after merge
            ref = None
            alt = None
            
            # Check for clinvar columns (preferred)
            if "ref_allele_clinvar" in row.index:
                ref = str(row.get("ref_allele_clinvar", "")).upper()
            elif "ref_allele" in row.index:
                ref = str(row.get("ref_allele", "")).upper()
            
            if "alt_allele_clinvar" in row.index:
                alt = str(row.get("alt_allele_clinvar", "")).upper()
            elif "alt_allele" in row.index:
                alt = str(row.get("alt_allele", "")).upper()

            if not genotype or not ref or not alt:
                return False

            # Filter out NaN strings
            if ref in ["NAN", "NONE", ""] or alt in ["NAN", "NONE", ""]:
                return False

            # 23andMe genotype is 2 characters (e.g., "AG", "AA", "GG")
            if len(genotype) != 2:
                return False

            alleles_in_genotype = set(genotype)
            
            # CRITICAL FIX: Simplified logic (removed redundant union)
            # Must contain alt allele AND only use ref or alt
            expected_alleles = {ref, alt}
            return alt in alleles_in_genotype and alleles_in_genotype.issubset(expected_alleles)

        except Exception as e:
            logger.debug(f"Genotype check failed: {e}")
            return False

    # Filter to only verified matches
    verified = merged[merged.apply(genotype_matches, axis=1)].copy()

    # Add confidence score
    verified["match_confidence"] = verified.apply(
        lambda row: calculate_match_confidence(
            "position_with_allele",
            review_status=row.get("review_status", None),
        ),
        axis=1,
    )

    logger.info(
        f"Position matching: {len(merged):,} total, {len(verified):,} verified"
    )
    return verified


def deduplicate_matches(df: pd.DataFrame, strategy: str = "best") -> pd.DataFrame:
    """
    Deduplicate matched variants, keeping best quality matches.

    Args:
        df: DataFrame with matched variants
        strategy: 'best' (highest confidence), 'first', or 'all'

    Returns:
        Deduplicated DataFrame
    """
    if len(df) == 0:
        return df

    # Create user variant key for deduplication
    if "chromosome_user" in df.columns and "position_user" in df.columns:
        df["_dedup_key"] = (
            df["chromosome_user"].astype(str)
            + ":"
            + df["position_user"].astype(str)
        )
    elif "coord_key" in df.columns:
        df["_dedup_key"] = df["coord_key"]
    elif "rsid" in df.columns:
        df["_dedup_key"] = df["rsid"]
    else:
        logger.warning("Cannot deduplicate: no suitable key found")
        return df

    original_count = len(df)

    if strategy == "best":
        # Keep match with highest confidence per user variant
        if "match_confidence" in df.columns:
            df = df.sort_values("match_confidence", ascending=False)
            df = df.drop_duplicates(subset="_dedup_key", keep="first")
        else:
            df = df.drop_duplicates(subset="_dedup_key", keep="first")

    elif strategy == "first":
        df = df.drop_duplicates(subset="_dedup_key", keep="first")

    elif strategy == "all":
        # Keep all matches (no deduplication)
        pass

    df = df.drop(columns=["_dedup_key"], errors="ignore")

    removed = original_count - len(df)
    if removed > 0:
        logger.info(f"Deduplication removed {removed:,} duplicate matches")

    return df


def match_variants_hybrid(
    clinvar_df: pd.DataFrame,
    user_df: pd.DataFrame,
    clinvar_type: str = "",
    user_type: str = "",
) -> Tuple[pd.DataFrame, int, int]:
    """
    Hybrid matching: rsID first, then coordinates, with quality scoring.

    IMPROVEMENTS over original:
    1. Uses improved 23andMe matching with genotype verification
    2. Adds match_confidence scoring to all matches
    3. Better deduplication (keeps highest quality matches)

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

    logger.info(f"{'='*60}")
    logger.info(f"MATCHING: {clinvar_type} × {user_type}")
    logger.info(f"{'='*60}")

    matches: List[pd.DataFrame] = []
    rsid_count: int = 0
    coord_count: int = 0

    # Try rsID matching first
    rsid_matched: pd.DataFrame = pd.DataFrame()
    if "rsid" in user_df.columns and "rsid" in clinvar_df.columns:
        rsid_matched = match_by_rsid(user_df, clinvar_df)
        if len(rsid_matched) > 0:
            matches.append(rsid_matched)
            rsid_count = len(rsid_matched)
            logger.info(f"✓ rsID: {rsid_count:,} matches")

    # Try coordinate matching for unmatched variants
    if rsid_count > 0 and "rsid" in user_df.columns:
        matched_rsids: Set[Any] = set(rsid_matched["rsid"])
        unmatched = user_df[~user_df["rsid"].isin(matched_rsids)]
    else:
        unmatched = user_df

    if len(unmatched) > 0:
        logger.info(f"Attempting coordinate matching on {len(unmatched):,}...")

        # Use improved 23andMe matching if applicable
        if user_type == "23andme":
            coord_matched = match_by_position_23andme_improved(unmatched, clinvar_df)
        else:
            coord_matched = match_by_coordinates(unmatched, clinvar_df)

        if len(coord_matched) > 0:
            matches.append(coord_matched)
            coord_count = len(coord_matched)
            logger.info(f"✓ Coordinate: {coord_count:,} matches")

    # Combine all matches
    if not matches:
        raise ValueError(f"No matches found: {clinvar_type} × {user_type}")

    combined = pd.concat(matches, ignore_index=True)

    # Improved deduplication (keeps best quality)
    combined = deduplicate_matches(combined, strategy="best")

    coverage = len(combined) / len(user_df) * 100
    logger.info(f"{'='*60}")
    logger.info(f"TOTAL: {len(combined):,} matches ({coverage:.1f}% coverage)")

    # Show confidence distribution
    if "match_confidence" in combined.columns:
        avg_conf = combined["match_confidence"].mean()
        logger.info(f"Average match confidence: {avg_conf:.2f}")

    logger.info(f"{'='*60}")

    return combined, rsid_count, coord_count


__all__ = [
    "match_by_rsid",
    "match_by_coordinates",
    "match_by_position_23andme_improved",
    "match_variants_hybrid",
    "calculate_match_confidence",
    "deduplicate_matches",
]
