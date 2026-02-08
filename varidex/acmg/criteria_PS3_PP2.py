#!/usr/bin/env python3
"""
varidex/acmg/criteria_PS3_PP2.py

PS3: Functional evidence from AlphaMissense + dbNSFP predictors

FIXED v7.3.0-dev: CADD threshold adjusted to 20 (top 1%, standard)
PP2: Missense constraint from gnomAD + gene lists

FIXED VERSION - Addresses double PP2 application issue
- Added apply_ps3_only() method (RECOMMENDED for integration)
- Added dependency checking with clear error messages
- Separated PS3 and PP2 logic to avoid Step 7 conflicts
"""

import logging
from typing import Dict, Optional, List, Tuple, Set
from dataclasses import dataclass
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class PS3Evidence:
    """PS3 functional evidence result."""

    applied: bool
    strength: str  # 'Supporting', 'Moderate', 'Strong'
    sources: List[str]
    scores: Dict[str, float]
    interpretation: str


@dataclass
class PP2Evidence:
    """PP2 missense constraint evidence result."""

    applied: bool
    gene_constrained: bool
    pli_score: Optional[float]
    missense_z_score: Optional[float]
    in_constraint_gene_list: bool


class PS3_PP2_Classifier:
    """
    ACMG PS3/PP2 criteria evaluator for DataFrame-based pipeline.

    PS3: Well-established functional studies show deleterious effect
    PP2: Missense variant in gene with low tolerance to missense variation

    USAGE NOTE: Use apply_ps3_only() if PP2 is already applied in Step 7!
    """

    def __init__(
        self,
        gnomad_constraint_path: Optional[str] = None,
        lof_genes: Optional[Set[str]] = None,
        missense_genes: Optional[Set[str]] = None,
    ):
        """
        Initialize criteria evaluator.

        Args:
            gnomad_constraint_path: Optional path to gnomAD constraint data
            lof_genes: Optional set of LoF-intolerant genes
            missense_genes: Optional set of missense-constrained genes
        """
        self.gnomad_path = (
            Path(gnomad_constraint_path) if gnomad_constraint_path else None
        )
        self.lof_genes = lof_genes or set()
        self.missense_genes = missense_genes or set()
        self.gnomad_constraint = None

        logger.info("Initialized PS3/PP2 criteria classifier")

    def apply_ps3_only(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply ONLY PS3 criterion, don't modify PP2.

        Use this method if PP2 is already applied elsewhere in your pipeline
        (e.g., in Step 7's apply_full_acmg_classification).

        Args:
            df: Input DataFrame with variant annotations

        Returns:
            DataFrame with PS3 column added (PP2 unchanged)
        """
        logger.info(f"Applying PS3 (functional evidence) to {len(df)} variants...")

        # Check required dependencies
        required_cols = ["REVEL_score", "CADD_phred"]
        missing_cols = [c for c in required_cols if c not in df.columns]

        if missing_cols:
            logger.error(f"❌ PS3 FAILED: Missing required columns: {missing_cols}")
            logger.error("   Ensure dbNSFP annotation (Step 6) completed successfully")
            df["PS3"] = False
            df["PS3_error"] = f"Missing columns: {', '.join(missing_cols)}"
            return df

        # Check optional but helpful columns
        optional_cols = ["AlphaMissense_score", "SIFT_score", "PolyPhen_score"]
        missing_optional = [c for c in optional_cols if c not in df.columns]
        if missing_optional:
            logger.warning(
                f"⚠️  PS3 sensitivity reduced: Missing {', '.join(missing_optional)}"
            )
            logger.warning("   PS3 will work but may apply to fewer variants")

        # Initialize PS3 column
        df["PS3"] = False
        ps3_count = 0

        # Apply PS3 to each variant
        for idx, row in df.iterrows():
            ps3_result = self._evaluate_ps3_for_row(row)
            if ps3_result.applied:
                df.at[idx, "PS3"] = True
                ps3_count += 1

        logger.info(
            f"  ✅ PS3 applied to {ps3_count} variants ({ps3_count/len(df)*100:.1f}%)"
        )

        return df

    def apply_pp2_only(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply ONLY PP2 criterion, don't modify PS3.

        Use this method ONLY if PP2 is NOT already applied in Step 7.
        Check your pipeline to avoid double application!

        Args:
            df: Input DataFrame with variant annotations

        Returns:
            DataFrame with PP2 column added (PS3 unchanged)
        """
        logger.info(f"Applying PP2 (missense constraint) to {len(df)} variants...")

        # Load constraint data if needed
        self._load_gnomad_constraint()

        # Initialize PP2 column
        df["PP2"] = False
        pp2_count = 0

        # Apply PP2 to missense variants
        for idx, row in df.iterrows():
            gene = row.get("gene", "")
            consequence = str(row.get("molecular_consequence", "")).lower()

            if "missense" in consequence:
                pp2_result = self._evaluate_pp2_for_gene(gene)
                if pp2_result.applied:
                    df.at[idx, "PP2"] = True
                    pp2_count += 1

        logger.info(
            f"  ✅ PP2 applied to {pp2_count} variants ({pp2_count/len(df)*100:.1f}%)"
        )

        return df

    def apply_ps3_pp2(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply both PS3 and PP2 criteria together.

        WARNING: Only use this if PP2 is NOT applied in Step 7!
        Otherwise you'll overwrite Step 7's PP2 values.

        For most pipelines, use apply_ps3_only() instead.

        Args:
            df: Input DataFrame with variant annotations

        Returns:
            DataFrame with PS3 and PP2 columns added
        """
        logger.warning(
            "⚠️  Applying both PS3 and PP2 - ensure PP2 not already applied in Step 7!"
        )

        df = self.apply_ps3_only(df)
        df = self.apply_pp2_only(df)

        return df

    def _evaluate_ps3_for_row(self, row: pd.Series) -> PS3Evidence:
        """
        Evaluate PS3 criterion using multiple functional predictors.

        Strategy:
        1. AlphaMissense score (if available)
        2. REVEL score
        3. CADD phred score
        4. Meta-predictor consensus (SIFT + PolyPhen)

        Thresholds (ACMG-compliant):
        - Strong: 3+ sources agree + high confidence
        - Moderate: 2+ sources agree
        - Supporting: 1 high-confidence source

        Args:
            row: DataFrame row with variant data

        Returns:
            PS3Evidence object with applied status and strength
        """
        deleterious_sources = []
        scores = {}

        # 1. AlphaMissense (most reliable single predictor)
        am_score = self._get_score(row, "AlphaMissense_score")
        if am_score is not None:
            scores["AlphaMissense"] = am_score
            if am_score >= 0.7:  # High pathogenicity threshold
                deleterious_sources.append("AlphaMissense")

        # 2. REVEL (ensemble predictor)
        revel_score = self._get_score(row, "REVEL_score")
        if revel_score is not None:
            scores["REVEL"] = revel_score
            if revel_score >= 0.5:  # REVEL pathogenic threshold
                deleterious_sources.append("REVEL")

        # 3. CADD (scaled C-score)
        cadd_score = self._get_score(row, "CADD_phred")
        if cadd_score is not None:
            scores["CADD"] = cadd_score
            if cadd_score >= 20:  # Top 1% most deleterious (standard)
                deleterious_sources.append("CADD")

        # 4. Meta-predictor: SIFT + PolyPhen agreement
        sift_score = self._get_score(row, "SIFT_score")
        poly_score = self._get_score(row, "PolyPhen_score")

        if sift_score is not None and poly_score is not None:
            scores["SIFT"] = sift_score
            scores["PolyPhen"] = poly_score

            # Both predict deleterious?
            sift_del = sift_score <= 0.05  # SIFT: lower = more deleterious
            poly_del = poly_score >= 0.85  # PolyPhen: higher = more deleterious

            if sift_del and poly_del:
                deleterious_sources.append("SIFT+PolyPhen")
                scores["Meta"] = 1.0

        # Determine strength
        applied = False
        strength = ""
        interpretation = ""

        num_sources = len(deleterious_sources)

        if num_sources >= 3:
            applied = True
            strength = "Strong"
            interpretation = f"PS3_Strong: {num_sources} independent sources converge"
        elif num_sources == 2:
            applied = True
            strength = "Moderate"
            interpretation = f"PS3_Moderate: {num_sources} sources agree"
        elif num_sources == 1:
            # Only apply Supporting if it's a high-confidence predictor
            if "AlphaMissense" in deleterious_sources or "REVEL" in deleterious_sources:
                applied = True
                strength = "Supporting"
                interpretation = "PS3_Supporting: High-confidence predictor"
            else:
                interpretation = (
                    f"PS3 not met (single low-confidence source insufficient)"
                )
        else:
            interpretation = f"PS3 not met ({num_sources} sources insufficient)"

        return PS3Evidence(
            applied=applied,
            strength=strength,
            sources=deleterious_sources,
            scores=scores,
            interpretation=interpretation,
        )

    def _evaluate_pp2_for_gene(self, gene: str) -> PP2Evidence:
        """
        Evaluate PP2 criterion for missense constraint.

        Criteria (any one sufficient):
        - Gene is in curated missense-constrained list, OR
        - gnomAD missense Z-score > 3.09 (p < 0.001), OR
        - pLI score > 0.9 (highly LoF intolerant)

        Args:
            gene: Gene symbol

        Returns:
            PP2Evidence object
        """
        if not gene:
            return PP2Evidence(
                applied=False,
                gene_constrained=False,
                pli_score=None,
                missense_z_score=None,
                in_constraint_gene_list=False,
            )

        # Check curated gene lists
        in_constraint_list = gene in self.lof_genes or gene in self.missense_genes

        # Get gnomAD metrics
        pli_score = self._get_pli_score(gene)
        missense_z = self._get_missense_z_score(gene)

        # Determine if gene is constrained (any criterion)
        gene_constrained = (
            in_constraint_list
            or (pli_score is not None and pli_score > 0.9)
            or (missense_z is not None and missense_z > 3.09)
        )

        applied = gene_constrained

        return PP2Evidence(
            applied=applied,
            gene_constrained=gene_constrained,
            pli_score=pli_score,
            missense_z_score=missense_z,
            in_constraint_gene_list=in_constraint_list,
        )

    def _load_gnomad_constraint(self):
        """Load gnomAD gene constraint metrics."""
        if self.gnomad_constraint is not None or self.gnomad_path is None:
            return

        if not self.gnomad_path.exists():
            logger.warning(f"gnomAD constraint file not found: {self.gnomad_path}")
            logger.warning("PP2 will only use curated gene lists")
            return

        try:
            logger.info(f"Loading gnomAD constraint from {self.gnomad_path}")
            self.gnomad_constraint = pd.read_csv(self.gnomad_path, sep="\t")
            logger.info(f"Loaded constraint for {len(self.gnomad_constraint)} genes")
        except Exception as e:
            logger.error(f"Failed to load gnomAD constraint: {e}")
            self.gnomad_constraint = None

    def _get_score(self, row: pd.Series, column: str) -> Optional[float]:
        """Safely extract score from row."""
        if column not in row.index:
            return None

        try:
            value = row[column]
            if pd.isna(value):
                return None
            return float(value)
        except (ValueError, TypeError):
            return None

    def _get_pli_score(self, gene: str) -> Optional[float]:
        """Get gnomAD pLI score for gene."""
        if (
            self.gnomad_constraint is None
            or gene not in self.gnomad_constraint["gene"].values
        ):
            return None

        try:
            row = self.gnomad_constraint[self.gnomad_constraint["gene"] == gene]
            if not row.empty and "pLI" in row.columns:
                pli = row["pLI"].iloc[0]
                return float(pli) if pd.notna(pli) else None
        except Exception as e:
            logger.warning(f"Error extracting pLI for {gene}: {e}")

        return None

    def _get_missense_z_score(self, gene: str) -> Optional[float]:
        """Get gnomAD missense Z-score for gene."""
        if (
            self.gnomad_constraint is None
            or gene not in self.gnomad_constraint["gene"].values
        ):
            return None

        try:
            row = self.gnomad_constraint[self.gnomad_constraint["gene"] == gene]
            if not row.empty and "missense_z" in row.columns:
                z_score = row["missense_z"].iloc[0]
                return float(z_score) if pd.notna(z_score) else None
        except Exception as e:
            logger.warning(f"Error extracting missense Z for {gene}: {e}")

        return None


def load_curated_gene_lists() -> Tuple[Set[str], Set[str]]:
    """
    Load curated lists of constrained genes.

    Returns:
        Tuple of (lof_genes, missense_genes)

    Note: Customize this for your clinical specialty!
    """
    # Example LoF-intolerant genes (from ClinGen, DECIPHER, etc.)
    lof_genes = {
        "BRCA1",
        "BRCA2",
        "TP53",
        "PTEN",
        "ATM",
        "CHEK2",
        "PALB2",
        "MLH1",
        "MSH2",
        "MSH6",
        "PMS2",
        "APC",
        "MUTYH",
        "DMD",
        "DYSF",
        "LMNA",
        "TTN",
        "MYH7",
        "MYBPC3",
        "SCN5A",
        "KCNQ1",
        "KCNH2",
        "RYR2",
    }

    # Example missense-constrained genes
    missense_genes = {
        "BRCA1",
        "BRCA2",
        "TP53",
        "PTEN",
        "APC",
        "PKD1",
        "PKD2",
        "COL4A3",
        "COL4A4",
        "COL4A5",
        "FBN1",
        "TGFBR1",
        "TGFBR2",
        "SMAD3",
    }

    return lof_genes, missense_genes


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Example usage - apply PS3 only (recommended)
    test_data = {
        "gene": ["BRCA1", "BRCA1", "APOE"],
        "molecular_consequence": [
            "missense_variant",
            "missense_variant",
            "missense_variant",
        ],
        "REVEL_score": [0.8, 0.3, 0.2],
        "CADD_phred": [28, 15, 10],
        "AlphaMissense_score": [0.9, 0.2, 0.1],
    }

    df = pd.DataFrame(test_data)

    classifier = PS3_PP2_Classifier()

    # Apply PS3 only (doesn't touch PP2)
    result_df = classifier.apply_ps3_only(df)

    print("\nPS3 Results:")
    print(result_df[["gene", "PS3", "REVEL_score", "CADD_phred"]])
    print(f"\nPS3 applied: {result_df['PS3'].sum()} variants")
