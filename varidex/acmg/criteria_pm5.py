"""PM5: Novel missense at same position as known pathogenic"""
import pandas as pd


class PM5Classifier:
    def __init__(self, clinvar_df: pd.DataFrame):
        """Build index of pathogenic positions from ClinVar"""
        self.pathogenic_positions = self._build_pathogenic_index(clinvar_df)

    def _build_pathogenic_index(self, clinvar_df):
        """Extract positions with known pathogenic variants"""
        pathogenic = clinvar_df[
            clinvar_df.clinical_sig.str.contains("Pathogenic", na=False)
            & ~clinvar_df.clinical_sig.str.contains("Benign", na=False)
        ]

        positions = {}
        for _, row in pathogenic.iterrows():
            gene = row.get("gene")
            pos = row.get("position")
            if pd.notna(gene) and pd.notna(pos):
                key = f"{gene}:{pos}"
                positions[key] = positions.get(key, 0) + 1

        print(f"PM5: Indexed {len(positions):,} pathogenic positions")
        return positions

    def apply_pm5(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply PM5: novel missense at pathogenic position"""
        df["PM5"] = False

        missense_mask = df.molecular_consequence.str.contains("missense", na=False, case=False)

        if missense_mask.sum() == 0:
            print("⭐ PM5: 0 missense variants")
            return df

        print(f"PM5: Checking {missense_mask.sum():,} missense variants...")

        count = 0
        for idx in df[missense_mask].index:
            gene = df.at[idx, "gene"]
            pos = df.at[idx, "position"]
            key = f"{gene}:{pos}"

            if key in self.pathogenic_positions:
                df.at[idx, "PM5"] = True
                count += 1

        pm5_pct = count / len(df) * 100
        print(f"⭐ PM5: {count} novel missense at pathogenic positions ({pm5_pct:.1f}%)")

        if count > 0:
            pm5_genes = df[df.PM5 == True].gene.value_counts().head(5)
            print(f"   Top: {', '.join([f'{g}({c})' for g, c in pm5_genes.items()])}")

        return df
