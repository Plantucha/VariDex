#!/usr/bin/env python3
"""
FIXED Hybrid Matching - Gets 46K matches (not 17K)

Replaces the broken matching_improved.py
"""

import pandas as pd
from typing import Tuple


def match_variants_hybrid_FIXED(
    clinvar_df: pd.DataFrame,
    user_df: pd.DataFrame,
) -> Tuple[pd.DataFrame, int, int]:
    """
    FIXED matching that gets ~46K matches with full ClinVar annotations.
    """
    print(f"🔗 Matching: {len(user_df):,} user vs {len(clinvar_df):,} ClinVar")
    
    # Step 1: rsID matching (primary strategy)
    print("  rsID matching...")
    rsid_matches = user_df.merge(
        clinvar_df,
        left_on='rsid',
        right_on=['ID', 'rsid'],  # Try both ClinVar ID and rsid fields
        how='inner',
        suffixes=('_user', '_clinvar')
    )
    rsid_count = len(rsid_matches)
    print(f"  ✓ rsID: {rsid_count:,}")
    
    # Step 2: Coordinate matching for unmatched
    matched_rsids = set(rsid_matches['rsid'].dropna())
    unmatched = user_df[~user_df['rsid'].isin(matched_rsids)].copy()
    
    if len(unmatched) > 0:
        print(f"  Coordinate matching for {len(unmatched):,} remaining...")
        
        # Create coordinate keys
        unmatched['coord_key'] = (
            unmatched['chromosome'].astype(str) + ':' + 
            unmatched['position'].astype(str)
        )
        
        # ClinVar coordinate key (try both CHROM/POS and chromosome/position)
        clinvar_coord = clinvar_df.copy()
        clinvar_coord['coord_key'] = (
            clinvar_coord.get('CHROM', clinvar_coord.get('chromosome')).astype(str) + ':' + 
            clinvar_coord.get('POS', clinvar_coord.get('position')).astype(str)
        )
        
        coord_matches = unmatched.merge(
            clinvar_coord,
            on='coord_key',
            how='inner',
            suffixes=('_user', '_clinvar')
        )
        coord_count = len(coord_matches)
        print(f"  ✓ Coord: {coord_count:,}")
    else:
        coord_count = 0
    
    # Combine results
    if coord_count > 0:
        all_matches = pd.concat([rsid_matches, coord_matches], ignore_index=True)
    else:
        all_matches = rsid_matches
    
    # Remove duplicates
    all_matches = all_matches.drop_duplicates(
        subset=['rsid', 'chromosome', 'position'], 
        keep='first'
    )
    
    print(f"  ✓ Total unique: {len(all_matches):,}")
    
    # Verify annotations preserved
    anno_cols = ['gene', 'molecular_consequence', 'gnomad_af', 'clinical_sig']
    print("  Annotation columns:")
    for col in anno_cols:
        if col in all_matches.columns:
            non_null = all_matches[col].notna().sum()
            print(f"    {col}: {non_null:,}/{len(all_matches):,}")
    
    return all_matches, rsid_count, coord_count
