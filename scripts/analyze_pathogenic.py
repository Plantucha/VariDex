#!/usr/bin/env python3
"""Analyze the pathogenic (PVS1+PM2) variants."""

import pandas as pd

# Load the pathogenic variants
df = pd.read_csv("output/pathogenic_review.csv")

print("=" * 70)
print("🔴 PATHOGENIC VARIANT ANALYSIS (PVS1+PM2)")
print("=" * 70)
print(f"\nTotal: {len(df):,} variants\n")

# Top genes
print("=== Top 20 Genes with Pathogenic Variants ===")
gene_counts = df["gene"].value_counts().head(20)
for gene, count in gene_counts.items():
    print(f"  {gene}: {count}")

# ClinVar agreement
print("\n=== ClinVar Classification Agreement ===")
clinvar_counts = df["clinical_sig"].value_counts().head(10)
for sig, count in clinvar_counts.items():
    print(f"  {sig}: {count}")

# Variant types
print("\n=== Molecular Consequences ===")
# Extract first consequence type
df["consequence_simple"] = df["molecular_consequence"].str.extract(r"SO:\d+\|([^,;]+)")
consequence_counts = df["consequence_simple"].value_counts().head(10)
for cons, count in consequence_counts.items():
    print(f"  {cons}: {count}")

# Sample variants
print("\n=== Sample Pathogenic Variants ===")
print(f"{'rsID':<15} {'Chr:Pos':<15} {'Gene':<15} {'Type':<20} {'ClinVar':<20}")
print("-" * 85)
for idx, row in df.head(10).iterrows():
    cons = (
        str(row["molecular_consequence"]).split("|")[1].split(",")[0]
        if "|" in str(row["molecular_consequence"])
        else "N/A"
    )
    print(
        f"{row['rsid']:<15} {str(row['CHROM'])+':'+str(row['POS']):<15} {str(row['gene'])[:14]:<15} {cons[:19]:<20} {str(row['clinical_sig'])[:19]:<20}"
    )

# Chromosome distribution
print("\n=== Chromosome Distribution ===")
chr_counts = df["CHROM"].value_counts().sort_index()
for chrom, count in chr_counts.items():
    print(f"  Chr{chrom}: {count}")

print(f"\n{'='*70}")
print("✅ These variants need clinical review!")
