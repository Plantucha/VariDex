#!/usr/bin/env python3
"""
varidex/acmg/criteria_pm5.py v7.3.0-dev

PM5: Novel missense at same amino acid position as known pathogenic variant
FIXED: Now uses protein position instead of genomic position

ACMG Definition:
- PM5 (Moderate Pathogenic): Novel missense change at amino acid residue
  where DIFFERENT missense change determined to be pathogenic

Example:
- Known pathogenic: BRCA1 p.Arg1699Trp (codon 1699)
- Your variant: BRCA1 p.Arg1699Gln (same codon 1699, different change)
- Conclusion: PM5 applies

Development version - not for production use.
"""
import logging
import re
import pandas as pd
from typing import Set, Tuple, Optional

logger = logging.getLogger(__name__)


class PM5Classifier:
    """
    PM5 Classifier with protein position-based matching.

    FIXED: Uses (gene, protein_position) instead of (gene, genomic_position)
    """

    def __init__(self, clinvar_df: pd.DataFrame):
        """Build index of pathogenic protein positions"""
        self.pathogenic_positions = self._build_pathogenic_index(clinvar_df)

    def _extract_protein_position(self, hgvs_p: str) -> Optional[int]:
        """
        Extract protein position from HGVS protein notation.

        Examples:
            p.Arg1699Trp -> 1699
            p.Glu255del -> 255
            p.Met1? -> 1
            p.Arg123fs -> 123
            p.Glu45_Glu47del -> 45

        Args:
            hgvs_p: HGVS protein notation (e.g., "p.Arg1699Trp")

        Returns:
            Protein position as integer, or None if cannot parse
        """
        if pd.isna(hgvs_p) or not isinstance(hgvs_p, str):
            return None

        hgvs_p = hgvs_p.strip()

        if not hgvs_p.startswith("p."):
            return None

        # Pattern to extract position from various HGVS formats
        # Matches: p.Arg1699Trp, p.R1699W, p.Glu255del, p.Arg123fs, etc.
        patterns = [
            r"p\.[A-Z][a-z]{2}(\d+)",  # Three-letter AA code
            r"p\.([A-Z])(\d+)",  # Single-letter AA code
            r"p\.[A-Z][a-z]{2}(\d+)_[A-Z][a-z]{2}\d+",  # Range (take first)
        ]

        for pattern in patterns:
            match = re.search(pattern, hgvs_p)
            if match:
                # Get the first captured group that's a number
                for group in match.groups():
                    try:
                        return int(group)
                    except (ValueError, TypeError):
                        continue

        return None

    def _build_pathogenic_index(
        self, clinvar_df: pd.DataFrame
    ) -> Set[Tuple[str, int]]:
        """
        Extract pathogenic protein positions as hash set.

        FIXED: Uses protein position from HGVS notation instead of genomic position.

        Args:
            clinvar_df: ClinVar DataFrame with columns:
                - gene: Gene symbol
                - protein_change or hgvsp: HGVS protein notation
                - clinical_sig: Clinical significance

        Returns:
            Set of (gene, protein_position) tuples
        """
        pathogenic = clinvar_df[
            clinvar_df.clinical_sig.str.contains("Pathogenic", na=False)
            & ~clinvar_df.clinical_sig.str.contains("Benign", na=False)
        ]

        positions = set()

        # Try multiple column names for protein change
        protein_col = None
        for col in ["protein_change", "hgvsp", "hgvs_p", "amino_acid_change"]:
            if col in pathogenic.columns:
                protein_col = col
                break

        if protein_col is None:
            logger.warning(
                "PM5: No protein change column found "
                "(tried: protein_change, hgvsp, hgvs_p, amino_acid_change)"
            )
            return positions

        valid_mask = pathogenic.gene.notna() & pathogenic[protein_col].notna()
        valid_pathogenic = pathogenic[valid_mask]

        success_count = 0
        fail_count = 0

        for _, row in valid_pathogenic.iterrows():
            protein_pos = self._extract_protein_position(row[protein_col])

            if protein_pos is not None:
                positions.add((str(row.gene), int(protein_pos)))
                success_count += 1
            else:
                fail_count += 1

        logger.info(
            f"PM5: Indexed {len(positions):,} pathogenic protein positions "
            f"({success_count:,} parsed, {fail_count:,} failed)"
        )

        return positions

    def apply_pm5(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply PM5 with protein position-based matching.

        FIXED: Matches on (gene, protein_position) instead of genomic position

        Args:
            df: Variant DataFrame with columns:
                - gene: Gene symbol
                - molecular_consequence: Variant type
                - protein_change or hgvsp: HGVS protein notation

        Returns:
            DataFrame with PM5 column added
        """
        df["PM5"] = False

        missense_mask = df.molecular_consequence.str.contains(
            "missense", na=False, case=False
        )

        if missense_mask.sum() == 0:
            logger.info("⭐ PM5: 0 missense variants")
            return df

        logger.info(f"PM5: Checking {missense_mask.sum():,} missense variants...")

        protein_col = None
        for col in ["protein_change", "hgvsp", "hgvs_p", "amino_acid_change"]:
            if col in df.columns:
                protein_col = col
                break

        if protein_col is None:
            logger.warning(
                "PM5: No protein change column found in input data - "
                "PM5 cannot be applied"
            )
            return df

        def check_position(row):
            """Check if variant position matches pathogenic position"""
            if pd.notna(row.gene) and pd.notna(row[protein_col]):
                protein_pos = self._extract_protein_position(row[protein_col])
                if protein_pos is not None:
                    key = (str(row.gene), int(protein_pos))
                    return key in self.pathogenic_positions
            return False

        pm5_hits = df[missense_mask].apply(check_position, axis=1)

        df.loc[missense_mask, "PM5"] = pm5_hits

        pm5_count = int(df["PM5"].sum())
        pm5_pct = pm5_count / len(df) * 100 if len(df) > 0 else 0

        logger.info(
            f"⭐ PM5: {pm5_count} novel missense at pathogenic "
            f"protein positions ({pm5_pct:.1f}%)"
        )

        if pm5_count > 0:
            pm5_genes = df[df.PM5].gene.value_counts().head(5)
            logger.info(
                f"   Top: {', '.join([f'{g}({c})' for g, c in pm5_genes.items()])}"
            )

        return df


class PM5ClassifierOptimized(PM5Classifier):
    """
    Optimized PM5 with NumPy vectorization.

    Inherits protein position matching from base class.
    """

    def apply_pm5(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ultra-fast PM5 with vectorized operations"""
        import numpy as np

        df["PM5"] = False

        missense_mask = df.molecular_consequence.str.contains(
            "missense", na=False, case=False
        )

        if missense_mask.sum() == 0:
            logger.info("⭐ PM5: 0 missense variants")
            return df

        logger.info(f"PM5: Checking {missense_mask.sum():,} missense variants...")

        protein_col = None
        for col in ["protein_change", "hgvsp", "hgvs_p", "amino_acid_change"]:
            if col in df.columns:
                protein_col = col
                break

        if protein_col is None:
            logger.warning("PM5: No protein change column found")
            return df

        missense_df = df[missense_mask]
        genes = missense_df["gene"].astype(str).values
        protein_changes = missense_df[protein_col].values

        positions = np.array(
            [self._extract_protein_position(pc) for pc in protein_changes]
        )

        pm5_hits = np.array(
            [
                (g, p) in self.pathogenic_positions if p is not None else False
                for g, p in zip(genes, positions)
            ]
        )

        df.loc[missense_mask, "PM5"] = pm5_hits

        pm5_count = int(pm5_hits.sum())
        pm5_pct = pm5_count / len(df) * 100 if len(df) > 0 else 0

        logger.info(
            f"⭐ PM5: {pm5_count} novel missense at pathogenic "
            f"protein positions ({pm5_pct:.1f}%)"
        )

        if pm5_count > 0:
            pm5_genes = df[df.PM5].gene.value_counts().head(5)
            logger.info(
                f"   Top: {', '.join([f'{g}({c})' for g, c in pm5_genes.items()])}"
            )

        return df


if __name__ == "__main__":
    print("PM5 Classifier Test (FIXED VERSION)")
    print("=" * 60)

    clinvar_test = pd.DataFrame(
        {
            "gene": ["BRCA1", "BRCA1", "TP53"],
            "protein_change": ["p.Arg1699Trp", "p.Glu255del", "p.Arg273His"],
            "clinical_sig": ["Pathogenic", "Pathogenic", "Pathogenic"],
        }
    )

    variant_test = pd.DataFrame(
        {
            "gene": ["BRCA1", "BRCA1", "TP53", "BRCA2"],
            "molecular_consequence": ["missense", "missense", "missense", "missense"],
            "protein_change": [
                "p.Arg1699Gln",  # Same position as p.Arg1699Trp -> PM5
                "p.Glu255Lys",  # Same position as p.Glu255del -> PM5
                "p.Arg273Cys",  # Same position as p.Arg273His -> PM5
                "p.Val100Met",  # Different position -> no PM5
            ],
        }
    )

    print("\nClinVar pathogenic variants:")
    print(clinvar_test)

    print("\nTest variants:")
    print(variant_test)

    classifier = PM5Classifier(clinvar_test)
    result = classifier.apply_pm5(variant_test)

    print("\nResults:")
    print(result[["gene", "protein_change", "PM5"]])
    print("\nExpected: First 3 variants should have PM5=True")
