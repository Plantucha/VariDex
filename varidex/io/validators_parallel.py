#!/usr/bin/env python3
"""
varidex/io/validators_parallel.py - Parallel Validation v1.1.0

Parallel processing for chromosome and position validation.
Used for large datasets (1M+ variants) to speed up validation.

v1.1.0: Added progress bars for user feedback

Performance:
- Sequential: ~10-15 seconds for 4M variants
- Parallel (8 cores): ~2-3 seconds for 4M variants

NOTE: Parallel processing disabled due to memory issues with large datasets.
      Sequential mode is fast enough and more reliable.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple
from multiprocessing import Pool, cpu_count
from functools import partial
from tqdm import tqdm

logger = logging.getLogger(__name__)

VALID_CHROMOSOMES: List[str] = [str(i) for i in range(1, 23)] + ["X", "Y", "MT"]

CHROMOSOME_MAX_POSITIONS: Dict[str, int] = {
    "1": 250_000_000,
    "2": 243_000_000,
    "3": 198_000_000,
    "4": 191_000_000,
    "5": 181_000_000,
    "6": 171_000_000,
    "7": 160_000_000,
    "8": 146_000_000,
    "9": 142_000_000,
    "10": 136_000_000,
    "11": 135_000_000,
    "12": 134_000_000,
    "13": 115_000_000,
    "14": 107_000_000,
    "15": 103_000_000,
    "16": 90_500_000,
    "17": 84_000_000,
    "18": 80_500_000,
    "19": 59_000_000,
    "20": 64_500_000,
    "21": 48_000_000,
    "22": 52_000_000,
    "X": 156_000_000,
    "Y": 57_000_000,
    "MT": 17_000,
}


def _validate_chunk(
    chunk_data: Tuple[pd.DataFrame, int], max_positions: Dict[str, int]
) -> Tuple[pd.DataFrame, int, Dict[str, int]]:
    """
    Validate a single chunk of data (called by worker processes).

    Args:
        chunk_data: Tuple of (DataFrame chunk, chunk_id)
        max_positions: Dict of chromosome max positions

    Returns:
        Tuple of (valid DataFrame, chunk_id, warning_counts)
    """
    chunk, chunk_id = chunk_data

    if "chromosome" not in chunk.columns or "position" not in chunk.columns:
        return chunk, chunk_id, {}

    # Create invalid mask (vectorized)
    invalid_mask = (chunk["position"] < 1) | chunk["position"].isna()

    # Count warnings per chromosome
    warning_counts = {}

    # Check each chromosome's max position
    for chrom, max_pos in max_positions.items():
        chrom_mask = (chunk["chromosome"] == chrom) & (chunk["position"] > max_pos)
        if chrom_mask.any():
            warning_counts[chrom] = chrom_mask.sum()
        invalid_mask |= chrom_mask

    # Filter invalid rows
    valid_chunk = chunk[~invalid_mask].reset_index(drop=True)

    return valid_chunk, chunk_id, warning_counts


def validate_position_ranges_parallel(
    df: pd.DataFrame, n_workers: int = None
) -> pd.DataFrame:
    """
    Parallel validation of chromosome positions with progress bar.

    NOTE: Parallel processing is currently DISABLED (threshold set very high)
          to prevent MemoryError on systems with limited RAM.
          Sequential validation is fast enough for most use cases.

    Args:
        df: DataFrame with chromosome and position columns
        n_workers: Number of parallel workers (default: CPU count)

    Returns:
        Validated DataFrame with invalid positions removed
    """
    if "chromosome" not in df.columns or "position" not in df.columns:
        return df

    # DISABLED: Use sequential for all datasets (memory safety)
    # Original threshold was 100_000, now set to 50M to effectively disable
    if len(df) < 50_000_000:
        # Use sequential for small datasets
        return _validate_sequential(df)

    # Determine workers
    if n_workers is None:
        n_workers = max(1, cpu_count() - 1)  # Leave one core free

    orig_len = len(df)

    # Split into chunks
    chunk_size = max(10_000, len(df) // (n_workers * 4))  # 4 chunks per worker
    chunks = [
        (df.iloc[i : i + chunk_size].copy(), idx)
        for idx, i in enumerate(range(0, len(df), chunk_size))
    ]

    print(f"  ⚡ Parallel validation: {len(chunks)} chunks, {n_workers} workers")

    # Process chunks in parallel with progress bar
    validate_func = partial(_validate_chunk, max_positions=CHROMOSOME_MAX_POSITIONS)

    try:
        with Pool(processes=n_workers) as pool:
            # Use tqdm to show progress
            results = list(
                tqdm(
                    pool.imap(validate_func, chunks),
                    total=len(chunks),
                    desc="  Validating",
                    unit="chunk",
                    leave=False,
                )
            )
    except Exception as e:
        logger.warning(f"Parallel validation failed, falling back to sequential: {e}")
        return _validate_sequential(df)

    # Combine results
    valid_chunks = []
    all_warnings = {}

    for valid_chunk, chunk_id, warnings in results:
        valid_chunks.append(valid_chunk)
        # Aggregate warnings
        for chrom, count in warnings.items():
            all_warnings[chrom] = all_warnings.get(chrom, 0) + count

    # Log warnings
    for chrom, count in sorted(all_warnings.items()):
        max_pos = CHROMOSOME_MAX_POSITIONS.get(chrom, 0)
        logger.warning(f"{count} variants on {chrom} exceed max {max_pos:,}")

    # Concatenate valid chunks
    if not valid_chunks:
        return pd.DataFrame()

    result = pd.concat(valid_chunks, ignore_index=True)

    removed = orig_len - len(result)
    if removed > 0:
        logger.info(f"Filtered {removed:,} invalid positions ({len(result):,} valid)")

    return result


def _validate_sequential(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sequential validation with progress indication.

    Args:
        df: DataFrame to validate

    Returns:
        Validated DataFrame
    """
    orig_len = len(df)
    invalid_mask = (df["position"] < 1) | df["position"].isna()

    # Show progress for chromosome checking
    chrom_items = list(CHROMOSOME_MAX_POSITIONS.items())
    for chrom, max_pos in tqdm(
        chrom_items, desc="  Checking chromosomes", unit="chr", leave=False
    ):
        chrom_mask = (df["chromosome"] == chrom) & (df["position"] > max_pos)
        if chrom_mask.any():
            logger.warning(
                f"{chrom_mask.sum()} variants on {chrom} exceed max {max_pos:,}"
            )
        invalid_mask |= chrom_mask

    result = df[~invalid_mask].reset_index(drop=True)

    removed = orig_len - len(result)
    if removed > 0:
        logger.info(f"Filtered {removed:,} invalid positions")

    return result


def filter_valid_chromosomes_parallel(
    df: pd.DataFrame, n_workers: int = None
) -> pd.DataFrame:
    """
    Parallel filtering to valid chromosomes.

    This is fast even without parallelization (simple filter),
    but included for API consistency.

    Args:
        df: DataFrame with chromosome column
        n_workers: Number of workers (unused, kept for API)

    Returns:
        DataFrame with only valid chromosomes
    """
    if "chromosome" not in df.columns:
        return df

    orig_len = len(df)

    # Simple vectorized filter (already fast)
    result = df[df["chromosome"].isin(VALID_CHROMOSOMES)].copy()

    removed = orig_len - len(result)
    if removed > 0:
        logger.info(
            f"Filtered to valid chromosomes: {orig_len:,} → {len(result):,} "
            f"({removed:,} removed)"
        )

    return result


__all__ = [
    "validate_position_ranges_parallel",
    "filter_valid_chromosomes_parallel",
]
