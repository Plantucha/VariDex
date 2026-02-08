"""PP3/BP4: Computational prediction criteria - OPTIMIZED with fallback.

FIXED v7.3.0-dev: Stricter consensus requires >=3 tools AND >=3 concordant votes
Per ClinGen PP3/BP4 calibration guidelines (Brnich et al. 2020, PMID: 34955381)
"""

import pandas as pd


class PP3_BP4_Classifier:
    """
    PP3: Multiple lines of computational evidence support deleterious
    BP4: Multiple lines of computational evidence suggest benign

    Gracefully handles missing prediction data.
    """

    def __init__(self):
        self.thresholds = {
            "sift_deleterious": 0.05,
            "polyphen_damaging": 0.85,
            "cadd_pathogenic": 20,
            "revel_pathogenic": 0.5,
            "consensus_required": 3,
        }

    def apply_pp3_bp4(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply PP3/BP4 based on computational predictions."""
        df["PP3"] = False
        df["BP4"] = False

        # Check available prediction columns
        pred_cols = self._get_prediction_columns(df)

        if not pred_cols:
            print("PP3/BP4: ⚠️  No prediction scores available")
            print("PP3/BP4: To enable, add SIFT/PolyPhen/CADD/REVEL annotations")
            print("⭐ PP3: 0 variants (no prediction data)")
            print("⭐ BP4: 0 variants (no prediction data)")
            return df

        print(
            f"PP3/BP4: Using {len(pred_cols)} prediction tools: {', '.join(pred_cols)}"
        )

        pp3_count = 0
        bp4_count = 0

        # Apply consensus logic
        for idx, row in df.iterrows():
            deleterious_votes = 0
            benign_votes = 0
            total_tools = 0

            # SIFT (lower = more deleterious)
            if "SIFT_score" in pred_cols:
                val = row.get("SIFT_score")
                if pd.notna(val):
                    total_tools += 1
                    if val <= self.thresholds["sift_deleterious"]:
                        deleterious_votes += 1
                    elif val >= 0.5:
                        benign_votes += 1

            # PolyPhen (higher = more damaging)
            if "PolyPhen_score" in pred_cols:
                val = row.get("PolyPhen_score")
                if pd.notna(val):
                    total_tools += 1
                    if val >= self.thresholds["polyphen_damaging"]:
                        deleterious_votes += 1
                    elif val <= 0.2:
                        benign_votes += 1

            # CADD (higher = more pathogenic)
            if "CADD_phred" in pred_cols:
                val = row.get("CADD_phred")
                if pd.notna(val):
                    total_tools += 1
                    if val >= self.thresholds["cadd_pathogenic"]:
                        deleterious_votes += 1
                    elif val <= 10:
                        benign_votes += 1

            # REVEL (higher = more pathogenic)
            if "REVEL_score" in pred_cols:
                val = row.get("REVEL_score")
                if pd.notna(val):
                    total_tools += 1
                    if val >= self.thresholds["revel_pathogenic"]:
                        deleterious_votes += 1
                    elif val <= 0.15:
                        benign_votes += 1

            # FIXED: Strict consensus requires >=3 tools AND >=3 concordant votes
            # ClinGen PP3/BP4 calibration: prevents false positives from correlated tools
            if total_tools < 3:
                continue  # Skip if insufficient tools for reliable consensus

            if deleterious_votes >= 3:
                df.at[idx, "PP3"] = True
                pp3_count += 1
            elif benign_votes >= 3:
                df.at[idx, "BP4"] = True
                bp4_count += 1

        pp3_pct = pp3_count / len(df) * 100 if len(df) > 0 else 0
        bp4_pct = bp4_count / len(df) * 100 if len(df) > 0 else 0

        print(
            f"⭐ PP3: {pp3_count} variants with deleterious predictions ({pp3_pct:.1f}%)"
        )
        if pp3_count > 0:
            pp3_genes = df[df["PP3"]]["gene"].value_counts().head(5)
            print(f"   Top: {', '.join([f'{g}({c})' for g, c in pp3_genes.items()])}")

        print(f"⭐ BP4: {bp4_count} variants with benign predictions ({bp4_pct:.1f}%)")
        if bp4_count > 0:
            bp4_genes = df[df["BP4"]]["gene"].value_counts().head(5)
            print(f"   Top: {', '.join([f'{g}({c})' for g, c in bp4_genes.items()])}")

        return df

    def _get_prediction_columns(self, df: pd.DataFrame) -> list:
        """Detect available prediction score columns."""
        possible_cols = [
            "SIFT_score",
            "SIFT_pred",
            "PolyPhen_score",
            "PolyPhen_pred",
            "Polyphen2_HDIV_score",
            "CADD_phred",
            "CADD_raw",
            "REVEL_score",
            "MetaSVM_score",
            "MetaSVM_pred",
            "MutationTaster_score",
            "MutationTaster_pred",
        ]
        return [col for col in possible_cols if col in df.columns]
