"""
BA4 Classifier: LoF variants in genes with constrained LoF tolerance
ACMG/AMP Strong Benign evidence
"""

import pandas as pd

class BA4Classifier:
    def __init__(self, constraint_file: str = "gnomad/gnomad.v2.1.1.lof_metrics.by_gene.tsv.gz"):
        self.constraint_df = pd.read_csv(constraint_file, sep='\t')
        self.constraint_df['gene_symbol'] = self.constraint_df['gene'].str.split('.').str[0]
        print(f"BA4: Loaded {len(self.constraint_df):,} constrained genes")
        self.constrained_genes = set(self.constraint_df[self.constraint_df['oe_lof_upper'] < 0.1]['gene_symbol'])

    def apply_ba4(self, df: pd.DataFrame) -> pd.DataFrame:
        df['BA4'] = False
        
        # LoF variants
        lof_mask = df['molecular_consequence'].isin([
            'nonsense', 'frameshift_variant', 'splice_acceptor_variant', 
            'splice_donor_variant', 'stop_gained', 'stop_lost'
        ])
        
        # Constrained gene + LoF
        gene_match = df['gene'].isin(self.constrained_genes)
        
        df.loc[lof_mask & gene_match, 'BA4'] = True
        
        ba4_count = df['BA4'].sum()
        print(f"⭐ BA4: {ba4_count} LoF variants in constrained genes (oe<0.1)")
        
        if ba4_count > 0:
            top_genes = df[df['BA4']]['gene'].value_counts().head(3)
            print(f"  Top: {', '.join(top_genes.index.tolist())}")
        
        return df
