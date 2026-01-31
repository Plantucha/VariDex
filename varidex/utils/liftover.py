#!/usr/bin/env python3
"""
varidex/utils/liftover.py - Genome Build Coordinate Conversion v1.0.0-dev

Automatic detection and conversion of genomic coordinates between builds.
Supports GRCh37/hg19 ↔ GRCh38/hg38 conversions.

Features:
- Build detection from known position markers
- Batch coordinate conversion with progress tracking  
- Integration with pyliftover for accurate mapping
- Validation and unmapped variant handling

Dependencies:
- pyliftover (install: pip install pyliftover)

Version: 1.0.0-dev | Lines: <500
"""

import pandas as pd
import logging
from typing import Dict, Tuple, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

# Known position markers for build detection
# These are stable variants with well-documented position differences
BUILD_MARKERS = {
    "rs429358": {  # APOE ε4 allele
        "37": {"chr": "19", "pos": 45411941},
        "38": {"chr": "19", "pos": 44908684},
    },
    "rs7412": {  # APOE ε2 allele
        "37": {"chr": "19", "pos": 45412079},
        "38": {"chr": "19", "pos": 44908822},
    },
    "rs1815739": {  # ACTN3 R577X
        "37": {"chr": "11", "pos": 66560624},
        "38": {"chr": "11", "pos": 66328095},
    },
    "rs1800497": {  # DRD2 Taq1A
        "37": {"chr": "11", "pos": 113270828},
        "38": {"chr": "11", "pos": 113283448},
    },
}


def detect_build(df: pd.DataFrame, rsid_col: str = "rsid", chr_col: str = "chromosome", pos_col: str = "position") -> Optional[str]:
    """
    Detect genome build (GRCh37 or GRCh38) from variant positions.
    
    Uses known marker variants with different positions between builds.
    
    Args:
        df: DataFrame with variant data
        rsid_col: Column name for rsID
        chr_col: Column name for chromosome
        pos_col: Column name for position
    
    Returns:
        "37" for GRCh37/hg19
        "38" for GRCh38/hg38
        None if unable to detect
    
    Example:
        >>> df = pd.DataFrame({"rsid": ["rs429358"], "chromosome": ["19"], "position": [45411941]})
        >>> detect_build(df)
        '37'
    """
    if df.empty:
        logger.warning("Empty DataFrame provided for build detection")
        return None
    
    # Ensure position is numeric
    if pos_col in df.columns:
        df[pos_col] = pd.to_numeric(df[pos_col], errors="coerce")
    
    votes = {"37": 0, "38": 0}
    markers_found = 0
    
    for marker_rsid, positions in BUILD_MARKERS.items():
        # Find this marker in the DataFrame
        marker_rows = df[df[rsid_col] == marker_rsid]
        
        if marker_rows.empty:
            continue
        
        markers_found += 1
        
        for _, row in marker_rows.iterrows():
            row_chr = str(row[chr_col]).strip()
            row_pos = row[pos_col]
            
            # Skip if position is missing/invalid
            if pd.isna(row_pos):
                continue
            
            row_pos = int(row_pos)
            
            # Check against GRCh37
            if (row_chr == positions["37"]["chr"] and 
                abs(row_pos - positions["37"]["pos"]) < 10):  # Allow 10bp tolerance
                votes["37"] += 1
                logger.debug(f"Marker {marker_rsid} matches GRCh37 (pos={row_pos})")
            
            # Check against GRCh38
            elif (row_chr == positions["38"]["chr"] and 
                  abs(row_pos - positions["38"]["pos"]) < 10):
                votes["38"] += 1
                logger.debug(f"Marker {marker_rsid} matches GRCh38 (pos={row_pos})")
    
    if markers_found == 0:
        logger.warning(
            f"No build marker variants found in dataset. "
            f"Checked for: {', '.join(BUILD_MARKERS.keys())}"
        )
        return None
    
    # Determine build from votes
    if votes["37"] > votes["38"]:
        build = "37"
        confidence = votes["37"] / max(sum(votes.values()), 1)
    elif votes["38"] > votes["37"]:
        build = "38"
        confidence = votes["38"] / max(sum(votes.values()), 1)
    else:
        logger.warning(
            f"Build detection inconclusive: {votes}. "
            f"Found {markers_found} markers but equal votes."
        )
        return None
    
    logger.info(
        f"✓ Detected build: GRCh{build} (confidence: {confidence:.1%}, "
        f"{markers_found} markers, votes: {votes})"
    )
    
    return build


def liftover_coordinates(
    df: pd.DataFrame,
    from_build: str,
    to_build: str,
    chr_col: str = "chromosome",
    pos_col: str = "position",
    inplace: bool = True,
    show_progress: bool = True,
) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """
    Convert genomic coordinates between builds using pyliftover.
    
    Args:
        df: DataFrame with variant data
        from_build: Source build ("37" or "38")
        to_build: Target build ("37" or "38")
        chr_col: Column name for chromosome
        pos_col: Column name for position
        inplace: Modify DataFrame in place
        show_progress: Show progress bar
    
    Returns:
        Tuple of (converted_df, stats_dict)
        stats_dict contains: {"converted": int, "failed": int, "total": int}
    
    Example:
        >>> df = pd.DataFrame({"chromosome": ["19"], "position": [45411941]})
        >>> result_df, stats = liftover_coordinates(df, "37", "38")
        >>> print(stats)
        {'converted': 1, 'failed': 0, 'total': 1}
    """
    try:
        from pyliftover import LiftOver
    except ImportError:
        raise ImportError(
            "pyliftover not installed. Install with: pip install pyliftover"
        )
    
    if from_build == to_build:
        logger.info(f"Source and target builds are the same (GRCh{from_build}), skipping conversion")
        return df, {"converted": 0, "failed": 0, "total": len(df)}
    
    # Map build codes to UCSC nomenclature
    build_map = {"37": "hg19", "38": "hg38"}
    from_ucsc = build_map.get(from_build)
    to_ucsc = build_map.get(to_build)
    
    if not from_ucsc or not to_ucsc:
        raise ValueError(f"Invalid build codes: from={from_build}, to={to_build}. Use '37' or '38'")
    
    logger.info(f"🔄 Converting coordinates: {from_ucsc} → {to_ucsc}")
    
    # Initialize LiftOver
    try:
        lo = LiftOver(from_ucsc, to_ucsc)
    except Exception as e:
        logger.error(f"Failed to initialize LiftOver: {e}")
        raise
    
    if not inplace:
        df = df.copy()
    
    # Ensure position is numeric
    df[pos_col] = pd.to_numeric(df[pos_col], errors="coerce")
    
    stats = {"converted": 0, "failed": 0, "total": len(df)}
    
    # Progress tracking
    if show_progress:
        try:
            from tqdm import tqdm
            iterator = tqdm(df.iterrows(), total=len(df), desc="Converting", unit="var")
        except ImportError:
            iterator = df.iterrows()
    else:
        iterator = df.iterrows()
    
    # Convert each variant
    new_positions = []
    
    for idx, row in iterator:
        chrom = str(row[chr_col]).strip()
        pos = row[pos_col]
        
        # Skip if position is invalid
        if pd.isna(pos):
            new_positions.append(pos)
            stats["failed"] += 1
            continue
        
        pos = int(pos)
        
        # Add "chr" prefix if missing (required by pyliftover)
        if not chrom.startswith("chr"):
            chrom_query = f"chr{chrom}"
        else:
            chrom_query = chrom
        
        # Perform liftover
        try:
            result = lo.convert_coordinate(chrom_query, pos)
            
            if result and len(result) > 0:
                # Use first result (most common case)
                new_chrom, new_pos, strand = result[0]
                new_positions.append(new_pos)
                stats["converted"] += 1
            else:
                # Conversion failed - keep original
                new_positions.append(pos)
                stats["failed"] += 1
                logger.debug(f"Failed to convert {chrom}:{pos}")
        
        except Exception as e:
            logger.debug(f"Error converting {chrom}:{pos}: {e}")
            new_positions.append(pos)
            stats["failed"] += 1
    
    # Update positions
    df[pos_col] = new_positions
    
    success_rate = stats["converted"] / stats["total"] * 100 if stats["total"] > 0 else 0
    
    logger.info(
        f"✓ Conversion complete: {stats['converted']:,}/{stats['total']:,} "
        f"({success_rate:.1f}%) | Failed: {stats['failed']:,}"
    )
    
    if stats["failed"] > stats["total"] * 0.1:  # >10% failure
        logger.warning(
            f"⚠️  High failure rate ({stats['failed']/stats['total']:.1%}). "
            f"Check input data quality and chromosome format."
        )
    
    return df, stats


def auto_liftover(
    df: pd.DataFrame,
    target_build: str,
    rsid_col: str = "rsid",
    chr_col: str = "chromosome",
    pos_col: str = "position",
    inplace: bool = True,
    show_progress: bool = True,
) -> Tuple[pd.DataFrame, Dict[str, any]]:
    """
    Automatically detect source build and convert to target build if needed.
    
    Args:
        df: DataFrame with variant data
        target_build: Desired build ("37" or "38")
        rsid_col: Column name for rsID
        chr_col: Column name for chromosome
        pos_col: Column name for position
        inplace: Modify DataFrame in place
        show_progress: Show progress bar
    
    Returns:
        Tuple of (converted_df, info_dict)
        info_dict contains: {"source_build": str, "target_build": str, 
                            "converted": bool, "stats": dict}
    
    Example:
        >>> df = load_23andme("data.txt")
        >>> result_df, info = auto_liftover(df, target_build="38")
        >>> if info["converted"]:
        ...     print(f"Converted from GRCh{info['source_build']} to GRCh{info['target_build']}")
    """
    # Detect source build
    source_build = detect_build(df, rsid_col=rsid_col, chr_col=chr_col, pos_col=pos_col)
    
    info = {
        "source_build": source_build,
        "target_build": target_build,
        "converted": False,
        "stats": None,
    }
    
    if source_build is None:
        logger.warning(
            "⚠️  Unable to detect source build. Assuming data is already in target build. "
            "Proceeding without conversion."
        )
        return df, info
    
    if source_build == target_build:
        logger.info(f"✓ Data is already in target build GRCh{target_build}")
        return df, info
    
    # Perform conversion
    logger.info(f"🔄 Build mismatch detected: GRCh{source_build} → GRCh{target_build}")
    logger.info("Starting coordinate conversion...")
    
    converted_df, stats = liftover_coordinates(
        df,
        from_build=source_build,
        to_build=target_build,
        chr_col=chr_col,
        pos_col=pos_col,
        inplace=inplace,
        show_progress=show_progress,
    )
    
    info["converted"] = True
    info["stats"] = stats
    
    return converted_df, info


def validate_build_match(
    user_df: pd.DataFrame,
    clinvar_build: str,
    rsid_col: str = "rsid",
    chr_col: str = "chromosome",
    pos_col: str = "position",
) -> bool:
    """
    Validate that user data matches ClinVar build.
    
    Args:
        user_df: User genomic data DataFrame
        clinvar_build: ClinVar build version ("37" or "38")
        rsid_col: Column name for rsID
        chr_col: Column name for chromosome
        pos_col: Column name for position
    
    Returns:
        True if builds match or cannot determine
        False if builds definitely mismatch
    
    Example:
        >>> user_df = load_23andme("data.txt")
        >>> if not validate_build_match(user_df, clinvar_build="38"):
        ...     print("Build mismatch detected!")
    """
    user_build = detect_build(user_df, rsid_col=rsid_col, chr_col=chr_col, pos_col=pos_col)
    
    if user_build is None:
        logger.warning("Unable to validate build match - detection failed")
        return True  # Assume match if uncertain
    
    if user_build != clinvar_build:
        logger.error(
            f"❌ Build mismatch: User data is GRCh{user_build}, "
            f"ClinVar database is GRCh{clinvar_build}"
        )
        return False
    
    logger.info(f"✓ Build validation passed: Both GRCh{user_build}")
    return True


# Convenience functions
def convert_37_to_38(df: pd.DataFrame, **kwargs) -> Tuple[pd.DataFrame, Dict]:
    """Convert GRCh37 coordinates to GRCh38."""
    return liftover_coordinates(df, from_build="37", to_build="38", **kwargs)


def convert_38_to_37(df: pd.DataFrame, **kwargs) -> Tuple[pd.DataFrame, Dict]:
    """Convert GRCh38 coordinates to GRCh37."""
    return liftover_coordinates(df, from_build="38", to_build="37", **kwargs)


__all__ = [
    "detect_build",
    "liftover_coordinates",
    "auto_liftover",
    "validate_build_match",
    "convert_37_to_38",
    "convert_38_to_37",
]


if __name__ == "__main__":
    # Self-test
    print("\n" + "=" * 60)
    print("TESTING varidex.utils.liftover v1.0.0-dev")
    print("=" * 60 + "\n")
    
    # Test 1: Build detection with GRCh37 data
    test_df_37 = pd.DataFrame({
        "rsid": ["rs429358", "rs7412", "rs1815739"],
        "chromosome": ["19", "19", "11"],
        "position": [45411941, 45412079, 66560624],
    })
    
    build = detect_build(test_df_37)
    assert build == "37", f"Expected '37', got {build}"
    print("✓ Test 1 passed: GRCh37 detection")
    
    # Test 2: Build detection with GRCh38 data
    test_df_38 = pd.DataFrame({
        "rsid": ["rs429358", "rs7412"],
        "chromosome": ["19", "19"],
        "position": [44908684, 44908822],
    })
    
    build = detect_build(test_df_38)
    assert build == "38", f"Expected '38', got {build}"
    print("✓ Test 2 passed: GRCh38 detection")
    
    # Test 3: Coordinate conversion (requires pyliftover)
    try:
        from pyliftover import LiftOver
        
        converted_df, stats = liftover_coordinates(
            test_df_37.copy(),
            from_build="37",
            to_build="38",
            show_progress=False,
        )
        
        assert stats["converted"] > 0, "No conversions performed"
        assert stats["total"] == len(test_df_37), "Total count mismatch"
        print(f"✓ Test 3 passed: Converted {stats['converted']}/{stats['total']} variants")
        
        # Test 4: Auto-liftover
        result_df, info = auto_liftover(
            test_df_37.copy(),
            target_build="38",
            show_progress=False,
        )
        
        assert info["converted"] == True, "Should have converted"
        assert info["source_build"] == "37", "Wrong source build"
        assert info["target_build"] == "38", "Wrong target build"
        print("✓ Test 4 passed: Auto-liftover")
        
    except ImportError:
        print("⚠️  Tests 3-4 skipped: pyliftover not installed")
        print("   Install with: pip install pyliftover")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED")
    print("=" * 60 + "\n")
