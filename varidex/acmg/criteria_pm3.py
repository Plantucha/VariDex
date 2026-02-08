#!/usr/bin/env python3
"""
varidex/acmg/criteria_pm3.py v7.3.0-dev

PM3: Detected in trans with pathogenic variant (compound heterozygote)
FIXED: Added phasing limitation documentation and conservative approach

ACMG Definition:
- PM3 (Moderate Pathogenic): For recessive disorders, detected in trans
  with a pathogenic variant

LIMITATION:
- Phasing data (trio/parental genotypes) required to confirm trans configuration
- Without phasing, cannot distinguish cis vs trans variants
- Current implementation: Conservative approach with distance heuristic

Development version - not for production use.
"""
import logging
import pandas as pd
from typing import Optional

logger = logging.getLogger(__name__)


class PM3Classifier:
    """
    PM3 Classifier for compound heterozygote detection.

    IMPORTANT: This implementation has limitations without phasing data.
    See apply_pm3() docstring for details.
    """

    def __init__(
        self,
        require_phasing: bool = False,
        distance_threshold: int = 1000000,
        enable_distance_heuristic: bool = True,
    ):
        """
        Initialize PM3 classifier.

        Args:
            require_phasing: If True, disable PM3 unless phasing data available
            distance_threshold: Minimum distance (bp) between variants to assume trans
            enable_distance_heuristic: Use distance as proxy for phasing
        """
        self.require_phasing = require_phasing
        self.distance_threshold = distance_threshold
        self.enable_distance_heuristic = enable_distance_heuristic

        if require_phasing:
            logger.warning(
                "PM3: Phasing required but not available - PM3 will be disabled"
            )

    def apply_pm3(
        self, df: pd.DataFrame, has_phasing_data: bool = False
    ) -> pd.DataFrame:
        """
        Apply PM3: compound heterozygous check.

        PHASING LIMITATION:
        ==================
        PM3 requires variants to be in TRANS (on different chromosomes).
        Without phasing data (trio/parental genotypes), we cannot definitively
        determine if two heterozygous variants are in trans or cis.

        Current Implementation:
        - If has_phasing_data=True: Use phasing information (NOT YET IMPLEMENTED)
        - If enable_distance_heuristic=True: Assume trans if variants are
          >1 Mb apart (conservative heuristic)
        - If require_phasing=True: Disable PM3 entirely

        WARNING: This may produce false positives if variants are in cis.

        Args:
            df: Variant DataFrame with columns:
                - gene: Gene symbol
                - clinical_sig: Clinical significance
                - genotype: Genotype (heterozygous alleles)
                - position: Genomic position (for distance heuristic)
            has_phasing_data: Whether phasing information is available

        Returns:
            DataFrame with PM3 column added
        """
        df["PM3"] = False
        df["PM3_confidence"] = None

        if self.require_phasing and not has_phasing_data:
            logger.warning("⚠️  PM3: Disabled - phasing data required but not available")
            return df

        pathogenic_genes = df[
            df.clinical_sig.str.contains("Pathogenic", na=False)
            & ~df.clinical_sig.str.contains("Benign", na=False)
        ].gene.dropna().unique()

        count = 0
        low_confidence_count = 0

        for gene in pathogenic_genes:
            gene_variants = df[df.gene == gene]
            pathogenic_in_gene = gene_variants[
                gene_variants.clinical_sig.str.contains("Pathogenic", na=False)
                & ~gene_variants.clinical_sig.str.contains("Benign", na=False)
            ]

            if len(pathogenic_in_gene) >= 2:
                pathogenic_indices = list(pathogenic_in_gene.index)

                for i, idx1 in enumerate(pathogenic_indices):
                    for idx2 in pathogenic_indices[i + 1 :]:
                        genotype1 = str(df.at[idx1, "genotype"])
                        genotype2 = str(df.at[idx2, "genotype"])

                        het_genotypes = ["AG", "AC", "AT", "GC", "GT", "CT"]
                        is_het1 = genotype1 in het_genotypes
                        is_het2 = genotype2 in het_genotypes

                        if is_het1 and is_het2:
                            apply_pm3 = False
                            confidence = "unknown"

                            if has_phasing_data:
                                # TODO: Implement actual phasing check
                                # For now, placeholder
                                logger.warning(
                                    "PM3: Phasing data provided but parsing "
                                    "not implemented"
                                )
                                apply_pm3 = False
                                confidence = "no_phasing_parser"

                            elif self.enable_distance_heuristic:
                                if "position" in df.columns:
                                    pos1 = df.at[idx1, "position"]
                                    pos2 = df.at[idx2, "position"]

                                    if pd.notna(pos1) and pd.notna(pos2):
                                        distance = abs(int(pos2) - int(pos1))

                                        if distance > self.distance_threshold:
                                            apply_pm3 = True
                                            confidence = "distance_heuristic"
                                        else:
                                            confidence = "too_close"
                                            low_confidence_count += 1
                                    else:
                                        confidence = "no_position"
                                else:
                                    confidence = "no_position_column"

                            if apply_pm3:
                                df.at[idx1, "PM3"] = True
                                df.at[idx1, "PM3_confidence"] = confidence
                                df.at[idx2, "PM3"] = True
                                df.at[idx2, "PM3_confidence"] = confidence
                                count += 2

        pm3_pct = count / len(df) * 100 if len(df) > 0 else 0

        if self.enable_distance_heuristic:
            logger.info(
                f"⭐ PM3: {count} potential compound heterozygotes "
                f"({pm3_pct:.1f}%) [distance heuristic: >{self.distance_threshold/1e6:.1f}Mb]"
            )
            if low_confidence_count > 0:
                logger.warning(
                    f"⚠️  PM3: {low_confidence_count} pairs too close to confidently "
                    f"assign trans (PM3 not applied)"
                )
        else:
            logger.info(
                f"⭐ PM3: {count} potential compound heterozygotes "
                f"({pm3_pct:.1f}%) [NO PHASING - may include false positives]"
            )

        if count > 0:
            pm3_genes = df[df.PM3].gene.value_counts()
            logger.info(
                f"   Genes with PM3: {', '.join([f'{g}({c})' for g, c in pm3_genes.items()])}"
            )

        return df


def apply_pm3(
    df: pd.DataFrame,
    require_phasing: bool = False,
    distance_threshold: int = 1000000,
    enable_distance_heuristic: bool = True,
    has_phasing_data: bool = False,
) -> pd.DataFrame:
    """
    Standalone function to apply PM3.

    Args:
        df: Variant DataFrame
        require_phasing: Disable PM3 if no phasing data
        distance_threshold: Minimum distance to assume trans (default 1 Mb)
        enable_distance_heuristic: Use distance as phasing proxy
        has_phasing_data: Whether phasing info is available

    Returns:
        DataFrame with PM3 column
    """
    classifier = PM3Classifier(
        require_phasing=require_phasing,
        distance_threshold=distance_threshold,
        enable_distance_heuristic=enable_distance_heuristic,
    )
    return classifier.apply_pm3(df, has_phasing_data=has_phasing_data)


if __name__ == "__main__":
    print("PM3 Classifier Test (FIXED VERSION)")
    print("=" * 60)

    test_data = pd.DataFrame(
        {
            "gene": ["BRCA1", "BRCA1", "TP53", "BRCA1"],
            "clinical_sig": ["Pathogenic", "Pathogenic", "Pathogenic", "Benign"],
            "genotype": ["AG", "CT", "AG", "GG"],
            "position": [43000000, 43500000, 7500000, 43000100],
        }
    )

    print("\nInput variants:")
    print(test_data)

    classifier = PM3Classifier(enable_distance_heuristic=True)
    result = classifier.apply_pm3(test_data)

    print("\nResults:")
    print(result[["gene", "clinical_sig", "genotype", "PM3", "PM3_confidence"]])
