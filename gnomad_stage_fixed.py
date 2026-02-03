"""
gnomAD Population Frequency Annotation Stage for VariDex Pipeline.

This stage annotates variants with gnomAD population frequencies and applies
frequency-based ACMG criteria (BA1, BS1, PM2).

Development version - not for clinical or production use.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from varidex.pipeline.gnomad_annotator import (
    annotate_with_gnomad,
    apply_frequency_acmg_criteria,
)


class GnomadAnnotationStage:
    """Pipeline stage for gnomAD frequency annotation and ACMG criteria."""

    def __init__(self, gnomad_dir: Optional[Path] = None) -> None:
        """Initialize gnomAD annotation stage.

        Args:
            gnomad_dir: Directory containing gnomAD VCF files.
                        If None, this stage is skipped.
        """
        self.gnomad_dir = gnomad_dir
        self.enabled = gnomad_dir is not None

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names for gnomAD annotator.

        The matcher may create columns with suffixes like _user, _clinvar.
        We need to map them to the canonical names expected by gnomad_annotator.
        """
        result = df.copy()

        # Map of canonical name -> possible column names
        column_mappings = {
            'chromosome': ['chromosome', 'chrom', 'chr', 'chromosome_user', 'chromosome_clinvar'],
            'position': ['position', 'pos', 'start', 'position_user', 'position_clinvar'],
            'ref_allele': ['ref_allele', 'ref', 'reference', 'ref_allele_user', 'ref_allele_clinvar'],
            'alt_allele': ['alt_allele', 'alt', 'alternate', 'alt_allele_user', 'alt_allele_clinvar'],
        }

        for canonical, candidates in column_mappings.items():
            if canonical in result.columns:
                continue

            for candidate in candidates:
                if candidate in result.columns:
                    result[canonical] = result[candidate]
                    break

        # Check if we have all required columns
        required = ['chromosome', 'position', 'ref_allele', 'alt_allele']
        missing = [col for col in required if col not in result.columns]

        if missing:
            print(f"⚠️  Warning: Missing columns after normalization: {missing}")
            print(f"   Available columns: {list(result.columns)[:20]}")
            print("   gnomAD annotation may fail")

        return result

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """Annotate variants with gnomAD frequencies and apply ACMG criteria.

        Args:
            df: DataFrame with matched variants.

        Returns:
            DataFrame with added gnomAD frequency columns and BA1, BS1, PM2 flags.
        """
        if not self.enabled:
            print("⚠️  gnomAD stage skipped (no --gnomad-dir provided)")
            return df

        print()
        print("📊 Step: gnomAD Population Frequency Annotation")
        print("=" * 70)

        # Normalize column names
        df = self._normalize_columns(df)

        # Check if normalization was successful
        required = ['chromosome', 'position', 'ref_allele', 'alt_allele']
        missing = [col for col in required if col not in df.columns]

        if missing:
            print(f"❌ Error: Cannot proceed without columns: {missing}")
            print("   Skipping gnomAD annotation")
            return df

        print(f"Annotating {len(df):,} variants with gnomAD...")

        try:
            # Annotate with gnomAD frequencies
            result = annotate_with_gnomad(df, self.gnomad_dir)

            print("Applying BA1, BS1, PM2 frequency criteria...")

            # Apply frequency-based ACMG criteria
            result = apply_frequency_acmg_criteria(result)

            # Count applied criteria
            ba1_count = result.get("BA1", pd.Series([False])).sum()
            bs1_count = result.get("BS1", pd.Series([False])).sum()
            pm2_count = result.get("PM2", pd.Series([False])).sum()

            print()
            print(
                f"⭐ gnomAD criteria applied: "
                f"BA1={ba1_count}, BS1={bs1_count}, PM2={pm2_count}"
            )
            print("✅ Complete")
            print()

            return result

        except Exception as e:
            print(f"❌ Error during gnomAD annotation: {e}")
            print("   Continuing without gnomAD data")
            return df

    def __repr__(self) -> str:
        status = "enabled" if self.enabled else "disabled"
        return f"GnomadAnnotationStage({status}, dir={self.gnomad_dir})"
