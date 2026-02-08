#!/usr/bin/env python3
"""
varidex/acmg/criteria_ba4_bp2.py v7.3.0-dev

BA4 + BP2: Loss-of-Function Constraint & Homozygote Evidence
FIXED: BA4 logic inverted - now correctly applies to LoF-TOLERANT genes

ACMG Criteria:
- BA4 (Stand-alone Benign): LoF variant in gene with TOLERANT LoF constraint
  (oe_lof_upper > 0.35 from gnomAD v2.1.1) - FIXED from incorrect < 0.1
- BP2 (Supporting Benign): Variant observed in trans with pathogenic variant in
  recessive disorder OR homozygous in healthy individuals (with threshold)

Development version - not for production use.
"""

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class BA4BP2Classifier:
    """Classifier for BA4 (LoF constraint) and BP2 (homozygote evidence)."""

    def __init__(
        self,
        constraint_path: Optional[str] = None,
        ba4_threshold: float = 0.35,
        bp2_min_homozygotes: int = 5,
    ):
        """
        Initialize BA4/BP2 classifier.

        Args:
            constraint_path: Path to gnomAD constraint file
                           (gnomad.v2.1.1.lof_metrics.by_gene.tsv.gz)
            ba4_threshold: oe_lof_upper threshold for tolerant genes (default 0.35)
            bp2_min_homozygotes: Minimum homozygote count for BP2 (default 5)
        """
        self.constraint_df = None
        self.tolerant_genes = set()
        self.constrained_genes = set()
        self.ba4_threshold = ba4_threshold
        self.bp2_min_homozygotes = bp2_min_homozygotes

        if constraint_path and Path(constraint_path).exists():
            self._load_constraint_data(constraint_path)
        else:
            logger.warning(
                f"BA4/BP2: Constraint file not found at {constraint_path}, "
                "BA4 disabled"
            )

    def _load_constraint_data(self, path: str) -> None:
        """Load gnomAD constraint metrics."""
        logger.info(f"BA4: Loading constraint data from {Path(path).name}...")

        try:
            self.constraint_df = pd.read_csv(path, sep="\t", compression="gzip")

            self.constraint_df["gene_symbol"] = (
                self.constraint_df["gene"].str.split(".").str[0]
            )

            # FIXED: BA4 applies to LoF-TOLERANT genes (oe_lof_upper > threshold)
            tolerant_mask = self.constraint_df["oe_lof_upper"] > self.ba4_threshold
            self.tolerant_genes = set(
                self.constraint_df[tolerant_mask]["gene_symbol"]
            )

            # Also track constrained genes for logging
            constrained_mask = self.constraint_df["oe_lof_upper"] < 0.1
            self.constrained_genes = set(
                self.constraint_df[constrained_mask]["gene_symbol"]
            )

            logger.info(
                f"BA4: Loaded {len(self.constraint_df):,} genes, "
                f"{len(self.tolerant_genes):,} are LoF-TOLERANT (oe>{self.ba4_threshold}), "
                f"{len(self.constrained_genes):,} are LoF-CONSTRAINED (oe<0.1)"
            )

        except Exception as e:
            logger.error(f"BA4: Failed to load constraint data: {e}")
            self.constraint_df = None
            self.tolerant_genes = set()

    def apply_ba4(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply BA4: Stand-alone benign for LoF variants in TOLERANT genes.

        FIXED Logic:
        - Variant is predicted LoF (nonsense, frameshift, splice)
        - Gene has oe_lof_upper > 0.35 (TOLERATES LoF variants)
        - Interpretation: LoF is NOT a disease mechanism in this gene
        - BA4 = Stand-alone BENIGN

        Args:
            df: Variant DataFrame with 'molecular_consequence' and 'gene'

        Returns:
            DataFrame with BA4 column added
        """
        df["BA4"] = False

        if not self.tolerant_genes:
            logger.warning("BA4: No constraint data available, skipping")
            return df

        lof_consequences = [
            "nonsense",
            "frameshift_variant",
            "frameshift",
            "splice_acceptor_variant",
            "splice_donor_variant",
            "stop_gained",
            "stop_lost",
        ]

        has_gene = df["gene"].notna()
        is_lof = df["molecular_consequence"].str.lower().isin(
            [c.lower() for c in lof_consequences]
        )
        in_tolerant_gene = df["gene"].isin(self.tolerant_genes)

        ba4_mask = has_gene & is_lof & in_tolerant_gene
        df.loc[ba4_mask, "BA4"] = True

        ba4_count = int(df["BA4"].sum())
        ba4_pct = ba4_count / len(df) * 100 if len(df) > 0 else 0

        logger.info(
            f"⭐ BA4: {ba4_count} LoF variants in TOLERANT genes ({ba4_pct:.1f}%)"
        )

        if ba4_count > 0:
            top_genes = df[df["BA4"]]["gene"].value_counts().head(5)
            gene_list = ", ".join([f"{g}({c})" for g, c in top_genes.items()])
            logger.info(f"   Top BA4 genes (LoF-tolerant): {gene_list}")

        return df

    def apply_bp2(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply BP2: Variant observed in trans or homozygous in healthy.

        IMPROVED Logic:
        - Check gnomAD homozygote counts with threshold
        - Require hom_count >= bp2_min_homozygotes (default 5)
        - Ensures variant is observed in MULTIPLE healthy individuals

        Args:
            df: Variant DataFrame with 'hom_count' from gnomAD

        Returns:
            DataFrame with BP2 column added
        """
        df["BP2"] = False

        if "hom_count" not in df.columns:
            logger.warning(
                "BP2: 'hom_count' column not found, BP2 requires gnomAD annotation"
            )
            return df

        has_hom_data = df["hom_count"].notna()
        has_significant_homozygotes = df["hom_count"] >= self.bp2_min_homozygotes

        bp2_mask = has_hom_data & has_significant_homozygotes
        df.loc[bp2_mask, "BP2"] = True

        bp2_count = int(df["BP2"].sum())
        bp2_pct = bp2_count / len(df) * 100 if len(df) > 0 else 0

        logger.info(
            f"⭐ BP2: {bp2_count} variants with ≥{self.bp2_min_homozygotes} "
            f"homozygotes in gnomAD ({bp2_pct:.1f}%)"
        )

        if bp2_count > 0:
            max_hom = df[df["BP2"]]["hom_count"].max()
            median_hom = df[df["BP2"]]["hom_count"].median()
            logger.info(
                f"   Homozygote counts: median={median_hom:.0f}, max={max_hom:,.0f}"
            )

        return df

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply both BA4 and BP2 criteria.

        Args:
            df: Variant DataFrame

        Returns:
            DataFrame with BA4 and BP2 columns
        """
        logger.info("Applying BA4 + BP2 classifiers (FIXED VERSION)...")
        df = self.apply_ba4(df)
        df = self.apply_bp2(df)
        return df


def apply_ba4_bp2(
    df: pd.DataFrame,
    constraint_path: Optional[str] = None,
    ba4_threshold: float = 0.35,
    bp2_min_homozygotes: int = 5,
) -> pd.DataFrame:
    """
    Standalone function to apply BA4 and BP2.

    Args:
        df: Variant DataFrame
        constraint_path: Path to gnomAD constraint file
        ba4_threshold: oe_lof_upper threshold for tolerant genes
        bp2_min_homozygotes: Minimum homozygote count for BP2

    Returns:
        DataFrame with BA4 and BP2 columns
    """
    classifier = BA4BP2Classifier(
        constraint_path=constraint_path,
        ba4_threshold=ba4_threshold,
        bp2_min_homozygotes=bp2_min_homozygotes,
    )
    return classifier.apply(df)


if __name__ == "__main__":
    print("BA4/BP2 Classifier Test (FIXED VERSION)")
    print("=" * 50)

    test_data = pd.DataFrame(
        {
            "gene": ["BRCA1", "TTN", "TP53", "BRCA1"],
            "molecular_consequence": [
                "nonsense",
                "frameshift_variant",
                "missense_variant",
                "stop_gained",
            ],
            "hom_count": [0, 15, 0, 3],
        }
    )

    print("\nInput variants:")
    print(test_data)

    classifier = BA4BP2Classifier(
        constraint_path="gnomad/gnomad.v2.1.1.lof_metrics.by_gene.tsv.gz"
    )
    result = classifier.apply(test_data)

    print("\nResults:")
    print(result[["gene", "molecular_consequence", "BA4", "BP2"]])
