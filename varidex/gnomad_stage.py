"""
gnomAD Population Frequency Annotation Stage for VariDex Pipeline.

This stage annotates variants with gnomAD population frequencies and applies
frequency-based ACMG criteria (BA1, BS1, PM2).

Development version - not for production use.
"""

from pathlib import Path
from typing import Optional

import pandas as pd

from varidex.pipeline.gnomad_annotator import (
    annotate_with_gnomad,
    apply_frequency_acmg_criteria,
)


class GnomadAnnotationStage:
    """Pipeline stage for gnomAD frequency annotation and ACMG criteria."""

    def __init__(self, gnomad_dir: Optional[Path] = None):
        """
        Initialize gnomAD annotation stage.

        Args:
            gnomad_dir: Path to directory containing gnomAD VCF files.
                       If None, this stage is skipped.
        """
        self.gnomad_dir = gnomad_dir
        self.enabled = gnomad_dir is not None

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Annotate variants with gnomAD frequencies and apply ACMG criteria.

        Args:
            df: DataFrame with matched variants containing chromosome, position,
                ref_allele, alt_allele columns.

        Returns:
            DataFrame with added gnomAD frequency columns and BA1, BS1, PM2 flags.
        """
        if not self.enabled:
            print("⚠️  gnomAD stage skipped (no --gnomad-dir provided)")
            return df

        print(f"\n📊 Step: gnomAD Population Frequency Annotation")
        print("=" * 70)

        # Ensure required columns exist
        if "ref" not in df.columns and "ref_allele" in df.columns:
            df["ref"] = df["ref_allele"]
        if "alt" not in df.columns and "alt_allele" in df.columns:
            df["alt"] = df["alt_allele"]

        print(f"Annotating {len(df):,} variants with gnomAD...")

        # Annotate with gnomAD frequencies
        result = annotate_with_gnomad(df, self.gnomad_dir)

        print("Applying BA1, BS1, PM2 frequency criteria...")

        # Apply frequency-based ACMG criteria
        result = apply_frequency_acmg_criteria(result)

        # Count newly applied criteria
        ba1_count = result.get("BA1", pd.Series([False])).sum()
        bs1_count = result.get("BS1", pd.Series([False])).sum()
        pm2_count = result.get("PM2", pd.Series([False])).sum()

        print(
            f"\n⭐ gnomAD criteria applied: BA1={ba1_count}, BS1={bs1_count}, PM2={pm2_count}"
        )
        print("✅ Complete\n")

        return result

    def __repr__(self) -> str:
        status = "enabled" if self.enabled else "disabled"
        return f"GnomadAnnotationStage({status}, dir={self.gnomad_dir})"
