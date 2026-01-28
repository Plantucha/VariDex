"""
varidex/pipeline/gnomad_annotator.py v6.4.0-dev

Annotate variants with gnomAD frequencies during pipeline execution.

Development version - not for production use.
"""

import pandas as pd
from pathlib import Path
from typing import Optional
import logging
from tqdm import tqdm

logger = logging.getLogger(__name__)


def annotate_with_gnomad(
    df: pd.DataFrame, gnomad_dir: Path, batch_size: int = 1000
) -> pd.DataFrame:
    """
    Annotate DataFrame with gnomAD allele frequencies.

    Args:
        df: DataFrame with columns: chromosome, position, ref, alt
        gnomad_dir: Path to gnomAD VCF files
        batch_size: Process in batches for progress tracking

    Returns:
        DataFrame with added gnomad_af column
    """
    from varidex.integrations.gnomad import GnomADQuerier

    logger.info(f"Annotating {len(df):,} variants with gnomAD frequencies...")

    # Initialize results list
    frequencies = []

    with GnomADQuerier(gnomad_dir) as querier:
        for idx, row in tqdm(
            df.iterrows(), total=len(df), desc="Querying gnomAD", unit="var"
        ):
            try:
                result = querier.query(
                    str(row["chromosome"]),
                    int(row["position"]),
                    str(row["ref"]),
                    str(row["alt"]),
                )
                frequencies.append(result.af)
            except Exception as e:
                logger.debug(f"Error querying variant at index {idx}: {e}")
                frequencies.append(None)

    # Add frequency column
    df["gnomad_af"] = frequencies

    found_count = sum(1 for f in frequencies if f is not None)
    logger.info(
        f"✓ gnomAD annotation complete: {found_count:,}/{len(df):,} "
        f"({found_count/len(df)*100:.1f}%) variants found"
    )

    return df


def apply_frequency_acmg_criteria(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply BA1, BS1, PM2 criteria based on gnomad_af column.

    Args:
        df: DataFrame with gnomad_af column

    Returns:
        DataFrame with BA1, BS1, PM2 columns added
    """
    from varidex.acmg.frequency_criteria import evaluate_frequency_criteria

    logger.info("Applying frequency-based ACMG criteria...")

    ba1_list = []
    bs1_list = []
    pm2_list = []

    for af in df["gnomad_af"]:
        criteria = evaluate_frequency_criteria(af)
        ba1_list.append(criteria.BA1)
        bs1_list.append(criteria.BS1)
        pm2_list.append(criteria.PM2)

    df["BA1"] = ba1_list
    df["BS1"] = bs1_list
    df["PM2"] = pm2_list

    ba1_count = sum(ba1_list)
    bs1_count = sum(bs1_list)
    pm2_count = sum(pm2_list)

    logger.info(f"  BA1 (>5%): {ba1_count:,} variants")
    logger.info(f"  BS1 (>1%): {bs1_count:,} variants")
    logger.info(f"  PM2 (<0.01%): {pm2_count:,} variants")

    return df
