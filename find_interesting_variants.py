#!/usr/bin/env python3
"""
find_interesting_variants.py - Find variants that will show evidence assignment
"""

import pandas as pd

print("="*70)
print("FINDING INTERESTING TEST VARIANTS")
print("="*70)
print()

# Load matched variants
matched_df = pd.read_csv('test_output/matched_variants.csv')
print(f"Total variants: {len(matched_df):,}")
print()

# Load gene lists
from varidex.core.config import LOF_GENES, MISSENSE_RARE_GENES

print(f"LOF genes: {sorted(LOF_GENES)}")
print(f"Missense-rare genes: {sorted(MISSENSE_RARE_GENES)}")
print()

# Helper to extract data
def extract_gene(info_str):
    if 'GENEINFO=' not in str(info_str):
        return ''
    return str(info_str).split('GENEINFO=')[-1].split(';')[0].split(':')[0]

def extract_mc(info_str):
    if 'MC=' not in str(info_str):
        return ''
    mc = str(info_str).split('MC=')[-1].split(';')[0]
    return mc.split('|')[1] if '|' in mc else mc

# Extract genes and consequences
matched_df['gene_extracted'] = matched_df['INFO'].apply(extract_gene)
matched_df['mc_extracted'] = matched_df['INFO'].apply(extract_mc)

print("="*70)
print("1. PATHOGENIC VARIANTS (for PP2)")
print("="*70)

# Find pathogenic missense variants
pathogenic = matched_df[
    matched_df['clinical_sig'].str.contains('Pathogenic', case=False, na=False) &
    ~matched_df['clinical_sig'].str.contains('Conflicting', case=False, na=False) &
    matched_df['mc_extracted'].str.contains('missense', case=False, na=False)
].head(5)

if len(pathogenic) > 0:
    print(f"Found {len(pathogenic)} pathogenic missense variants:")
    for idx, row in pathogenic.iterrows():
        gene = row['gene_extracted']
        in_missense_rare = gene in MISSENSE_RARE_GENES
        print(f"  {row['rsid']:<15} {gene:<10} {row['clinical_sig']:<30} {'✓ PP2!' if in_missense_rare else ''}")
else:
    print("❌ No pathogenic missense variants found")
print()

print("="*70)
print("2. BENIGN VARIANTS (for BP1, BS1)")
print("="*70)

# Find benign variants
benign = matched_df[
    matched_df['clinical_sig'].str.contains('Benign', case=False, na=False) &
    ~matched_df['clinical_sig'].str.contains('Conflicting', case=False, na=False)
].head(5)

if len(benign) > 0:
    print(f"Found {len(benign)} benign variants:")
    for idx, row in benign.iterrows():
        gene = row['gene_extracted']
        mc = row['mc_extracted']
        in_lof = gene in LOF_GENES
        is_missense = 'missense' in mc.lower()
        print(f"  {row['rsid']:<15} {gene:<10} {mc:<20} {row['clinical_sig']:<30} {'✓ BP1!' if (in_lof and is_missense) else ''}")
else:
    print("❌ No benign variants found")
print()

print("="*70)
print("3. LOF VARIANTS (for PVS1)")
print("="*70)

# Find LOF variants
lof_terms = ['frameshift', 'nonsense', 'stop_gain', 'splice']
lof = matched_df[
    matched_df['mc_extracted'].str.contains('|'.join(lof_terms), case=False, na=False)
].head(5)

if len(lof) > 0:
    print(f"Found {len(lof)} LOF variants:")
    for idx, row in lof.iterrows():
        gene = row['gene_extracted']
        in_lof = gene in LOF_GENES
        print(f"  {row['rsid']:<15} {gene:<10} {row['mc_extracted']:<30} {row['clinical_sig']:<30} {'✓ PVS1!' if in_lof else ''}")
else:
    print("❌ No LOF variants found")
print()

print("="*70)
print("4. VARIANTS IN CURATED GENES")
print("="*70)

# Find variants in LOF genes
in_lof = matched_df[matched_df['gene_extracted'].isin(LOF_GENES)].head(5)
if len(in_lof) > 0:
    print(f"Variants in LOF genes ({len(in_lof)}):")
    for idx, row in in_lof.iterrows():
        print(f"  {row['rsid']:<15} {row['gene_extracted']:<10} {row['mc_extracted']:<20} {row['clinical_sig']}")
else:
    print("❌ No variants in LOF genes")
print()

# Find variants in missense-rare genes
in_missense = matched_df[matched_df['gene_extracted'].isin(MISSENSE_RARE_GENES)].head(5)
if len(in_missense) > 0:
    print(f"Variants in missense-rare genes ({len(in_missense)}):")
    for idx, row in in_missense.iterrows():
        print(f"  {row['rsid']:<15} {row['gene_extracted']:<10} {row['mc_extracted']:<20} {row['clinical_sig']}")
else:
    print("❌ No variants in missense-rare genes")
print()

print("="*70)
print("GENE STATISTICS")
print("="*70)
gene_counts = matched_df['gene_extracted'].value_counts()
print(f"Total unique genes: {len(gene_counts)}")
print(f"Top 10 genes:")
for gene, count in gene_counts.head(10).items():
    in_lof = "✓ LOF" if gene in LOF_GENES else ""
    in_mr = "✓ MR" if gene in MISSENSE_RARE_GENES else ""
    print(f"  {gene:<10} {count:>6} variants  {in_lof} {in_mr}")
print()

print("="*70)
print("MOLECULAR CONSEQUENCE STATISTICS")
print("="*70)
mc_counts = matched_df['mc_extracted'].value_counts()
print(f"Top consequence types:")
for mc, count in mc_counts.head(10).items():
    print(f"  {mc:<30} {count:>6} variants")
print()

print("="*70)
print("CLINICAL SIGNIFICANCE STATISTICS")
print("="*70)
sig_counts = matched_df['clinical_sig'].value_counts()
print(f"Clinical significance breakdown:")
for sig, count in sig_counts.head(10).items():
    print(f"  {sig:<50} {count:>6} variants")
