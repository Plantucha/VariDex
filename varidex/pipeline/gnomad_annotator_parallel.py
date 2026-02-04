#!/usr/bin/env python3
"""
Parallel gnomAD annotator using multiprocessing
"""

import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import pysam
from tqdm import tqdm

logger = logging.getLogger(__name__)


def query_gnomad_batch(args):
    """Query gnomAD for a batch of variants (for multiprocessing)"""
    variants_batch, gnomad_dir = args
    results = []

    for idx, row in variants_batch.iterrows():
        chrom = str(row.get("chromosome", row.get("chromosome_user", row.get("CHROM"))))
        pos = int(row.get("position", row.get("position_user", row.get("POS"))))
        ref = str(row.get("ref", row.get("ref_allele", row.get("REF", ""))))
        alt = str(row.get("alt", row.get("alt_allele", row.get("ALT", ""))))

        # Format chromosome
        chrom = chrom.replace("chr", "")

        # Get gnomAD file path
        gnomad_file = Path(gnomad_dir) / f"gnomad.exomes.r2.1.1.sites.{chrom}.vcf.bgz"

        af = None
        if gnomad_file.exists():
            try:
                tbx = pysam.TabixFile(str(gnomad_file))
                for record in tbx.fetch(chrom, pos - 1, pos):
                    fields = record.split("\t")
                    if len(fields) >= 8:
                        info = fields[7]
                        if "AF=" in info:
                            af_str = info.split("AF=")[1].split(";")[0]
                            af = float(af_str)
                            break
            except Exception:
                pass

        results.append((idx, af))

    return results


def annotate_with_gnomad_parallel(
    df: pd.DataFrame, gnomad_dir: Path, n_workers: int = 4
) -> pd.DataFrame:
    """
    Annotate variants with gnomAD frequencies using parallel processing.

    Args:
        df: DataFrame with variants
        gnomad_dir: Path to gnomAD VCF files
        n_workers: Number of parallel workers

    Returns:
        DataFrame with gnomad_af column added
    """
    logger.info(
        f"Annotating {len(df):,} variants with gnomAD (parallel, {n_workers} workers)..."
    )

    # Split dataframe into batches
    batch_size = max(100, len(df) // (n_workers * 4))
    batches = []
    for i in range(0, len(df), batch_size):
        batch = df.iloc[i : i + batch_size]
        batches.append((batch, gnomad_dir))

    # Initialize results
    gnomad_afs = pd.Series([None] * len(df), index=df.index)

    # Process in parallel
    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        futures = {
            executor.submit(query_gnomad_batch, batch): batch for batch in batches
        }

        with tqdm(total=len(df), desc="Querying gnomAD (parallel)", unit="var") as pbar:
            for future in as_completed(futures):
                try:
                    results = future.result()
                    for idx, af in results:
                        gnomad_afs[idx] = af
                        pbar.update(1)
                except Exception as e:
                    logger.warning(f"Batch failed: {e}")
                    pbar.update(batch_size)

    # Add to dataframe
    result = df.copy()
    result["gnomad_af"] = gnomad_afs

    found_count = result["gnomad_af"].notna().sum()
    logger.info(
        f"✓ gnomAD annotation complete: {found_count:,}/{len(df):,} ({100*found_count/len(df):.1f}%) variants found"
    )

    return result


def apply_frequency_acmg_criteria(df: pd.DataFrame) -> pd.DataFrame:
    """Apply BA1, BS1, PM2 based on gnomAD frequencies"""
    logger.info("Applying frequency-based ACMG criteria...")

    result = df.copy()

    # Initialize columns
    result["BA1"] = False
    result["BS1"] = False
    result["PM2"] = False

    # Apply criteria
    has_af = result["gnomad_af"].notna()

    # BA1: AF > 5% (benign stand-alone)
    result.loc[has_af & (result["gnomad_af"] > 0.05), "BA1"] = True

    # BS1: AF > 1% (benign strong)
    result.loc[
        has_af & (result["gnomad_af"] > 0.01) & (result["gnomad_af"] <= 0.05), "BS1"
    ] = True

    # PM2: AF < 0.01% (pathogenic moderate - very rare)
    result.loc[has_af & (result["gnomad_af"] < 0.0001), "PM2"] = True

    ba1_count = result["BA1"].sum()
    bs1_count = result["BS1"].sum()
    pm2_count = result["PM2"].sum()

    logger.info(f"  BA1 (>5%): {ba1_count:,} variants")
    logger.info(f"  BS1 (>1%): {bs1_count:,} variants")
    logger.info(f"  PM2 (<0.01%): {pm2_count:,} variants")

    return result
