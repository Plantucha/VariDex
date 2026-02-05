"""
gnomAD annotator - Using optimized GnomADLoader with parallel workers

Version: 2.0.0_dev - Integrated with GnomADLoader v1.1.0_dev
"""

import logging
import multiprocessing as mp
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def detect_optimal_workers():
    """
    Auto-detect optimal number of workers for current system.
    
    Returns worker count that balances CPU usage and I/O overhead.
    """
    cpu_count = mp.cpu_count()

    if cpu_count <= 2:
        return 1  # Sequential for low-end systems
    elif cpu_count <= 4:
        return cpu_count - 1  # Leave 1 core free
    elif cpu_count <= 8:
        return cpu_count - 2  # Leave 2 cores free
    else:
        # High-end systems: leave 2 cores, but don't exceed 20 workers
        # (diminishing returns due to I/O bottleneck)
        return min(cpu_count - 2, 20)


def annotate_with_gnomad(
    df: pd.DataFrame,
    gnomad_dir: Path,
    n_workers: int = None,
    batch_size: int = None,  # Deprecated, kept for compatibility
) -> pd.DataFrame:
    """
    Annotate DataFrame with gnomAD allele frequencies using GnomADLoader.
    
    Now uses the optimized GnomADLoader with ProcessPoolExecutor for
    parallel processing, providing 3-7x speedup on multi-core systems.

    Args:
        df: DataFrame with columns: chromosome, position, ref_allele, alt_allele
        gnomad_dir: Path to gnomAD VCF files
        n_workers: Number of parallel workers (auto-detected if None)
        batch_size: DEPRECATED - batch size is now handled internally

    Returns:
        DataFrame with added gnomad_af column and other population frequencies
    """
    # Auto-detect optimal configuration
    if n_workers is None:
        n_workers = detect_optimal_workers()
    
    # Log configuration
    if n_workers == 1:
        logger.info("Using sequential processing (1 worker)")
    else:
        logger.info(f"Using parallel processing with {n_workers} workers")

    # Try using the new GnomADLoader (v1.1.0_dev with parallel support)
    try:
        from varidex.io.loaders.gnomad import GnomADLoader

        print(f"Using optimized GnomADLoader with {n_workers} parallel workers")
        
        # Initialize loader with parallel workers
        with GnomADLoader(
            gnomad_dir=gnomad_dir,
            dataset="exomes",
            version="r2.1.1",
            max_workers=n_workers,
        ) as loader:
            # Use the built-in annotate_dataframe method
            # This automatically uses parallel processing for batch lookups
            result_df = loader.annotate_dataframe(df, show_progress=True)
            
            # The annotate_dataframe method adds all gnomAD columns
            # We need to merge back with original df
            return result_df

    except ImportError as e:
        logger.warning(
            f"New GnomADLoader not available ({e}), falling back to legacy method"
        )
        
        # Fall back to old parallel method if available
        try:
            from varidex.integrations.gnomad.query_parallel import (
                annotate_with_gnomad_parallel,
            )

            # Auto-detect batch size based on RAM
            if batch_size is None:
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

            logger.info(
                f"Legacy parallel: {n_workers} workers, batch_size={batch_size}"
            )

            # Convert DataFrame to list of dicts
            variants = df[
                ["chromosome", "position", "ref_allele", "alt_allele"]
            ].to_dict("records")

            # Annotate in parallel (old method)
            frequencies = annotate_with_gnomad_parallel(
                variants=variants,
                gnomad_dir=gnomad_dir,
                n_workers=n_workers,
                batch_size=batch_size,
            )

            df["gnomad_af"] = frequencies
            return df

        except ImportError:
            # Fall back to sequential (oldest method)
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
    """
    Apply ACMG frequency-based evidence codes.
    
    Evidence codes:
    - BA1: Allele frequency >5% in general population (Benign stand-alone)
    - BS1: Allele frequency >1% (Benign strong)
    - PM2: Allele frequency <0.01% or absent (Pathogenic moderate - rare)
    
    Args:
        df: DataFrame with gnomad_af column
        
    Returns:
        DataFrame with added BA1, BS1, PM2 columns
    """
    # BA1: >5% frequency = Benign stand-alone
    df["BA1"] = df["gnomad_af"] > 0.05
    
    # BS1: 1-5% frequency = Benign strong
    df["BS1"] = (df["gnomad_af"] > 0.01) & (df["gnomad_af"] <= 0.05)
    
    # PM2: <0.01% frequency = Pathogenic moderate (rare)
    # Note: NaN values (not found in gnomAD) are treated as rare
    df["PM2"] = (df["gnomad_af"] < 0.0001) | df["gnomad_af"].isna()

    return df
