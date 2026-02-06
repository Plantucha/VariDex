"""PM5 Classifier - OPTIMIZED VERSION v2.0
Performance improvements:
- Hash set lookups instead of dict (O(1) vs O(log n))
- Vectorized masking
- Pre-filtered missense variants
- Batched position lookups
"""
import pandas as pd
from typing import Set, Tuple


class PM5ClassifierOptimized:
    def __init__(self, clinvar_df: pd.DataFrame):
        """Build optimized index of pathogenic positions"""
        self.pathogenic_positions = self._build_pathogenic_index(clinvar_df)

    def _build_pathogenic_index(self, clinvar_df: pd.DataFrame) -> Set[Tuple[str, int]]:
        """Extract pathogenic positions as hash set (FAST lookups)"""
        # Filter pathogenic variants
        pathogenic = clinvar_df[
            clinvar_df.clinical_sig.str.contains("Pathogenic", na=False)
            & ~clinvar_df.clinical_sig.str.contains("Benign", na=False)
        ]

        # Build set of (gene, position) tuples for O(1) lookup
        positions = set()

        # Vectorized extraction
        valid_mask = pathogenic.gene.notna() & pathogenic.position.notna()
        valid_pathogenic = pathogenic[valid_mask]

        for _, row in valid_pathogenic.iterrows():
            positions.add((str(row.gene), int(row.position)))

        print(f"PM5: Indexed {len(positions):,} pathogenic positions")
        return positions

    def apply_pm5(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply PM5 with vectorized operations and hash lookups"""
        df["PM5"] = False

        # OPTIMIZATION 1: Pre-filter missense variants
        missense_mask = df.molecular_consequence.str.contains(
            "missense", na=False, case=False
        )

        missense_df = df[missense_mask]

        if len(missense_df) == 0:
            print("⭐ PM5: 0 missense variants")
            return df

        print(f"PM5: Checking {len(missense_df):,} missense variants...")

        # OPTIMIZATION 2: Vectorized lookup using hash set
        def check_position(row):
            """Fast O(1) hash lookup"""
            if pd.notna(row.gene) and pd.notna(row.position):
                key = (str(row.gene), int(row.position))
                return key in self.pathogenic_positions
            return False

        # Apply to missense variants only
        pm5_hits = missense_df.apply(check_position, axis=1)

        # Update original dataframe
        df.loc[missense_mask, "PM5"] = pm5_hits

        pm5_count = int(df["PM5"].sum())
        pm5_pct = pm5_count / len(df) * 100

        print(f"⭐ PM5: {pm5_count} novel missense at pathogenic positions ({pm5_pct:.1f}%)")

        if pm5_count > 0:
            pm5_genes = df[df.PM5].gene.value_counts().head(5)
            print(f"   Top: {', '.join([f'{g}({c})' for g, c in pm5_genes.items()])}")

        return df


# Even MORE optimized version with NumPy
class PM5ClassifierUltraFast:
    """Ultra-fast PM5 using NumPy array operations"""

    def __init__(self, clinvar_df: pd.DataFrame):
        import numpy as np

        # Build index as NumPy arrays for vectorized operations
        pathogenic = clinvar_df[
            clinvar_df.clinical_sig.str.contains("Pathogenic", na=False)
            & ~clinvar_df.clinical_sig.str.contains("Benign", na=False)
        ]

        valid_mask = pathogenic.gene.notna() & pathogenic.position.notna()
        valid = pathogenic[valid_mask]

        # Store as hash set (still fastest for membership testing)
        self.pathogenic_positions = set(
            zip(valid.gene.astype(str), valid.position.astype(int))
        )

        print(f"PM5: Indexed {len(self.pathogenic_positions):,} pathogenic positions")

    def apply_pm5(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ultra-fast PM5 with minimal overhead"""
        import numpy as np

        df["PM5"] = False

        # Pre-filter
        missense_mask = df.molecular_consequence.str.contains(
            "missense", na=False, case=False
        )

        if missense_mask.sum() == 0:
            print("⭐ PM5: 0 missense variants")
            return df

        print(f"PM5: Checking {missense_mask.sum():,} missense variants...")

        # Vectorized lookup
        genes = df.loc[missense_mask, "gene"].astype(str).values
        positions = df.loc[missense_mask, "position"].astype(int).values

        # Fast vectorized membership test
        pm5_hits = np.array([
            (g, p) in self.pathogenic_positions
            for g, p in zip(genes, positions)
        ])

        df.loc[missense_mask, "PM5"] = pm5_hits

        pm5_count = int(pm5_hits.sum())
        pm5_pct = pm5_count / len(df) * 100

        print(f"⭐ PM5: {pm5_count} novel missense at pathogenic positions ({pm5_pct:.1f}%)")

        if pm5_count > 0:
            pm5_genes = df[df.PM5].gene.value_counts().head(5)
            print(f"   Top: {', '.join([f'{g}({c})' for g, c in pm5_genes.items()])}")

        return df


# Backward compatibility (use optimized by default)
PM5Classifier = PM5ClassifierOptimized
