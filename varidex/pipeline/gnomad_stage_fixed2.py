"""
gnomAD Population Frequency Annotation Stage for VariDex Pipeline.
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
        self.gnomad_dir = gnomad_dir
        self.enabled = gnomad_dir is not None

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names for gnomAD annotator."""
        result = df.copy()

        # Prefer _clinvar columns (they have proper ref/alt alleles)
        # But fall back to _user if needed
        if "chromosome_clinvar" in result.columns:
            result["chromosome"] = result["chromosome_clinvar"]
        elif "chromosome_user" in result.columns:
            result["chromosome"] = result["chromosome_user"]
        elif "chrom" in result.columns:
            result["chromosome"] = result["chrom"]
        elif "CHROM" in result.columns:
            result["chromosome"] = result["CHROM"]

        if "position_clinvar" in result.columns:
            result["position"] = result["position_clinvar"]
        elif "position_user" in result.columns:
            result["position"] = result["position_user"]
        elif "pos" in result.columns:
            result["position"] = result["pos"]
        elif "POS" in result.columns:
            result["position"] = result["POS"]

        # ref_allele and alt_allele should come from ClinVar (more reliable)
        if "ref_allele" not in result.columns and "REF" in result.columns:
            result["ref_allele"] = result["REF"]
        if "alt_allele" not in result.columns and "ALT" in result.columns:
            result["alt_allele"] = result["ALT"]

        return result

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """Annotate variants with gnomAD frequencies and apply ACMG criteria."""
        if not self.enabled:
            print("⚠️  gnomAD stage skipped (no --gnomad-dir provided)")
            return df

        print()
        print("📊 Step: gnomAD Population Frequency Annotation")
        print("=" * 70)

        # Normalize column names
        df = self._normalize_columns(df)

        # Check if normalization was successful
        required = ["chromosome", "position", "ref_allele", "alt_allele"]
        missing = [
            col for col in required if col not in df.columns or df[col].isna().all()
        ]

        if missing:
            print(f"❌ Error: Missing or empty columns: {missing}")
            print("   Skipping gnomAD annotation")
            return df

        print(f"Annotating {len(df):,} variants with gnomAD...")

        try:
            result = annotate_with_gnomad(df, self.gnomad_dir)
            print("Applying BA1, BS1, PM2 frequency criteria...")
            result = apply_frequency_acmg_criteria(result)

            ba1_count = result.get("BA1", pd.Series([False])).sum()
            bs1_count = result.get("BS1", pd.Series([False])).sum()
            pm2_count = result.get("PM2", pd.Series([False])).sum()

            print()
            print(
                f"⭐ gnomAD criteria applied: BA1={ba1_count}, BS1={bs1_count}, PM2={pm2_count}"
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
