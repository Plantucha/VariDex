#!/usr/bin/env python3
"""
🧬 VariDex gnomAD Stage - Complete Fixed File with CPU Auto-Detection
Copy-paste this entire file to replace varidex/pipeline/gnomad_stage.py
Black-formatted, production-ready, no raw data changes.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import pandas as pd

from varidex.pipeline.gnomad_annotator import (
    annotate_with_gnomad,
    apply_frequency_acmg_criteria,
)
from varidex.utils.cpu_utils import get_optimal_workers


class GnomadAnnotationStage:
    """Pipeline stage for gnomAD frequency annotation and ACMG criteria."""

    def __init__(
        self, gnomad_dir: Optional[Path] = None, max_workers: Optional[int] = None
    ) -> None:
        self.gnomad_dir = gnomad_dir
        self.enabled = gnomad_dir is not None
        # Auto-detect optimal workers for I/O-bound tasks (gnomAD lookups)
        self.max_workers = max_workers or get_optimal_workers("io_bound")

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names and clean data for gnomAD annotator."""
        result = df.copy()

        # Map columns (prefer ClinVar for reliability)
        if "chromosome_clinvar" in result.columns:
            result["chromosome"] = result["chromosome_clinvar"]
        elif "chromosome_user" in result.columns:
            result["chromosome"] = result["chromosome_user"]
        elif "CHROM" in result.columns:
            result["chromosome"] = result["CHROM"]

        if "position_clinvar" in result.columns:
            result["position"] = result["position_clinvar"]
        elif "position_user" in result.columns:
            result["position"] = result["position_user"]
        elif "POS" in result.columns:
            result["position"] = result["POS"]

        if "ref_allele" not in result.columns and "REF" in result.columns:
            result["ref_allele"] = result["REF"]

        if "alt_allele" not in result.columns and "ALT" in result.columns:
            result["alt_allele"] = result["ALT"]

        # Filter out rows with NaN in critical columns
        required = ["chromosome", "position", "ref_allele", "alt_allele"]
        for col in required:
            if col in result.columns:
                before = len(result)
                result = result[result[col].notna()]
                removed = before - len(result)
                if removed > 0:
                    print(f"  Filtered {removed} rows with NaN in {col}")

        # Ensure position is integer
        if "position" in result.columns:
            result["position"] = result["position"].astype(int)

        return result

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """Annotate variants with gnomAD frequencies and apply ACMG criteria."""
        if not self.enabled:
            print("⚠️  gnomAD stage skipped (no --gnomad-dir provided)")
            return df

        print()
        print("📊 Step: gnomAD Population Frequency Annotation")
        print("=" * 70)

        original_count = len(df)
        original_index = df.index.copy()

        # Normalize column names and filter NaNs
        df_clean = self._normalize_columns(df)

        # Check if we have data left
        if len(df_clean) == 0:
            print("❌ Error: No valid variants after filtering NaN values")
            print("   Skipping gnomAD annotation")
            return df

        if len(df_clean) < original_count:
            print(
                f"  Using {len(df_clean):,}/{original_count:,} variants "
                "(filtered NaN values)"
            )

        print(f"Annotating {len(df_clean):,} variants with gnomAD...")
        print(f"Using {self.max_workers} parallel workers (I/O-bound optimization)")

        try:
            result = annotate_with_gnomad(
                df_clean, self.gnomad_dir, n_workers=self.max_workers  # ✅ FIXED: Changed from max_workers
            )

            print("Applying BA1, BS1, PM2 frequency criteria...")
            result = apply_frequency_acmg_criteria(result)

            # FIXED: Proper DataFrame column counting
            ba1_count = result["BA1"].sum() if "BA1" in result.columns else 0
            bs1_count = result["BS1"].sum() if "BS1" in result.columns else 0
            pm2_count = result["PM2"].sum() if "PM2" in result.columns else 0

            print()
            print(
                f"⭐ gnomAD criteria applied: "
                f"BA1={ba1_count}, BS1={bs1_count}, PM2={pm2_count}"
            )
            print("✅ Complete")
            print()

            # FIXED: Index-preserving merge for ALL cases
            df_out = df.copy()
            common_index = original_index.intersection(result.index)

            for col in result.columns:
                if col.startswith("gnomad") or col in ["BA1", "BS1", "PM2"]:
                    df_out.loc[common_index, col] = result.loc[common_index, col]

            print(
                f"  Propagated gnomAD data to {len(common_index):,} matching variants"
            )

            return df_out

        except Exception as e:
            print(f"❌ Error during gnomAD annotation: {e}")
            print("   Continuing without gnomAD data")
            import traceback

            traceback.print_exc()
            return df

    def __repr__(self) -> str:
        status = "enabled" if self.enabled else "disabled"
        return (
            f"GnomadAnnotationStage({status}, "
            f"dir={self.gnomad_dir}, workers={self.max_workers})"
        )
