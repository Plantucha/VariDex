"""PM3: Detected in trans with pathogenic variant (compound het)"""
import pandas as pd


class PM3Classifier:
    def apply_pm3(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply PM3: compound heterozygous check"""
        df["PM3"] = False

        pathogenic_genes = df[
            df.clinical_sig.str.contains("Pathogenic", na=False) &
            ~df.clinical_sig.str.contains("Benign", na=False)
        ].gene.dropna().unique()

        count = 0
        for gene in pathogenic_genes:
            gene_variants = df[df.gene == gene]
            pathogenic_in_gene = gene_variants[
                gene_variants.clinical_sig.str.contains("Pathogenic", na=False) &
                ~gene_variants.clinical_sig.str.contains("Benign", na=False)
            ]

            if len(pathogenic_in_gene) >= 2:
                for idx in pathogenic_in_gene.index:
                    genotype = str(df.at[idx, "genotype"])
                    if genotype in ["AG", "AC", "AT", "GC", "GT", "CT"]:
                        df.at[idx, "PM3"] = True
                        count += 1

        pm3_pct = count / len(df) * 100
        print(f"⭐ PM3: {count} potential compound heterozygotes ({pm3_pct:.1f}%)")
        return df
