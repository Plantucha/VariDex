"""
gnomAD annotator - Auto-optimized for any system
"""

import logging
import multiprocessing as mp
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def detect_optimal_workers():
    """Auto-detect optimal number of workers for current system."""
    cpu_count = mp.cpu_count()

    if cpu_count <= 2:
        return 1
    elif cpu_count <= 4:
        return cpu_count - 1
    elif cpu_count <= 8:
        return cpu_count - 2
    else:
        # High-end systems: leave 2 cores, cap at 20
        return min(cpu_count - 2, 20)


def annotate_with_gnomad(
    df: pd.DataFrame,
    gnomad_dir: Path,
    n_workers: int = None,
    batch_size: int = None,
) -> pd.DataFrame:
    """
    Annotate DataFrame with gnomAD allele frequencies.
    Auto-detects optimal configuration if not specified.

    Args:
        df: DataFrame with columns: chromosome, position, ref_allele, alt_allele
        gnomad_dir: Path to gnomAD VCF files
        n_workers: Number of parallel workers (auto-detected if None)
        batch_size: Variants per batch (auto-detected if None)

    Returns:
        DataFrame with added gnomad_af column
    """
    # Auto-detect optimal configuration
    if n_workers is None:
        n_workers = detect_optimal_workers()

    if batch_size is None:
        # Auto-detect based on available RAM
        try:
            import psutil

            ram_gb = psutil.virtual_memory().available / (1024**3)
            if ram_gb < 8:
                batch_size = 250
            elif ram_gb < 16:
                batch_size = 500
            elif ram_gb < 32:
                batch_size = 1000
            else:
                batch_size = 2000
        except:
            batch_size = 500  # Conservative default

    logger.info(f"Auto-optimized: {n_workers} workers, batch_size={batch_size}")

    # Check if parallel module exists, otherwise fall back to sequential
    try:
        from varidex.integrations.gnomad.query_parallel import (
            annotate_with_gnomad_parallel,
        )

        # Convert DataFrame to list of dicts
        variants = df[["chromosome", "position", "ref_allele", "alt_allele"]].to_dict(
            "records"
        )

        # Annotate in parallel
        frequencies = annotate_with_gnomad_parallel(
            variants=variants,
            gnomad_dir=gnomad_dir,
            n_workers=n_workers,
            batch_size=100,
        )

        df["gnomad_af"] = frequencies

    except ImportError:
        # Fall back to sequential (old method)
        logger.warning("Parallel module not available, using sequential method")
        from tqdm import tqdm

        from varidex.integrations.gnomad import GnomADQuerier

        frequencies = []
        with GnomADQuerier(gnomad_dir) as querier:
            for idx, row in tqdm(
                df.iterrows(), total=len(df), desc="Querying gnomAD", unit="var"
            ):
                try:
                    result = querier.query(
                        str(row["chromosome"]),
                        int(row["position"]),
                        str(row["ref_allele"]),
                        str(row["alt_allele"]),
                    )
                    frequencies.append(result.af)
                except Exception as e:
                    logger.debug(f"Error querying variant at index {idx}: {e}")
                    frequencies.append(None)

        df["gnomad_af"] = frequencies

    return df


def apply_frequency_acmg_criteria(df: pd.DataFrame) -> pd.DataFrame:
    """Apply ACMG frequency-based evidence codes."""
    df["BA1"] = df["gnomad_af"] > 0.05  # >5% = Benign stand-alone
    df["BS1"] = (df["gnomad_af"] > 0.01) & (
        df["gnomad_af"] <= 0.05
    )  # 1-5% = Benign strong
    df["PM2"] = df["gnomad_af"] < 0.0001  # <0.01% = Pathogenic moderate (rare)

    return df
