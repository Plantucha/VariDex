#!/usr/bin/env python3
"""
Detailed Report: Top 10 PVS1 (Loss of Function) Variants

PVS1 = Very Strong Evidence for Pathogenicity
These are loss-of-function variants in genes intolerant to LOF mutations.
"""

import pandas as pd
from pathlib import Path

print("=" * 80)
print("TOP 10 PVS1 VARIANTS - HIGHEST PRIORITY")
print("=" * 80)
print("\nPVS1: Loss of function variant in gene where LOF is known mechanism")
print("These are the MOST IMPORTANT variants to review clinically!")
print()

# Load PVS1 variants
pvs1_file = Path("output/PRIORITY_1_PVS1_loss_of_function.csv")
df = pd.read_csv(pvs1_file, low_memory=False)

print(f"Total PVS1 variants: {len(df):,}\n")

# Sort by additional evidence (more evidence = higher priority)
# Calculate total evidence codes
df["total_evidence_codes"] = (
    df["PVS1"].astype(int)
    + df["PM2"].astype(int)
    + df["PM4"].astype(int)
    + df["PP2"].astype(int)
    + df["BA1"].astype(int)
    + df["BS1"].astype(int)
    + df["BP1"].astype(int)
    + df["BP3"].astype(int)
)

# Sort by: 1) Total evidence, 2) gnomAD frequency (rarer = more concerning)
df_sorted = df.sort_values(
    by=["total_evidence_codes", "gnomad_af"], ascending=[False, True]
)

# Get top 10
top10 = df_sorted.head(10)

print("=" * 80)
print("DETAILED REPORT - TOP 10 PVS1 VARIANTS")
print("=" * 80)

for idx, (i, row) in enumerate(top10.iterrows(), 1):
    print(f"\n{'='*80}")
    print(f"VARIANT #{idx}")
    print(f"{'='*80}")

    # Basic info
    print(f"\n📍 Location:")
    print(f"   Chromosome: {row['chromosome']}")
    print(f"   Position: {row['position']:,}")
    print(f"   Change: {row['ref_allele']} → {row['alt_allele']}")

    # Gene info
    print(f"\n🧬 Gene:")
    print(f"   Name: {row['gene']}")
    print(f"   Consequence: {row.get('molecular_consequence', 'N/A')}")

    # Clinical significance
    print(f"\n⚕️  Clinical Significance:")
    print(f"   ClinVar: {row['clinical_sig']}")
    print(f"   Review Status: {row.get('review_status', 'N/A')}")

    # Population frequency
    gnomad_af = row["gnomad_af"]
    if pd.notna(gnomad_af):
        print(f"\n📊 Population Frequency:")
        print(f"   gnomAD AF: {gnomad_af:.6f}")
        if gnomad_af > 0:
            print(f"   Approximately 1 in {int(1/gnomad_af):,} people")
        else:
            print(f"   Not found in gnomAD (extremely rare)")
    else:
        print(f"\n📊 Population Frequency:")
        print(f"   gnomAD AF: Not available")

    # ACMG Evidence
    print(f"\n🏷️  ACMG Evidence Codes:")
    evidence_codes = []
    if row["PVS1"]:
        evidence_codes.append("PVS1 (Very Strong Pathogenic)")
    if row["PM2"]:
        evidence_codes.append("PM2 (Rare in population)")
    if row["PM4"]:
        evidence_codes.append("PM4 (Protein length change)")
    if row["PP2"]:
        evidence_codes.append("PP2 (Missense in constrained gene)")
    if row["BA1"]:
        evidence_codes.append("BA1 (Common - benign)")
    if row["BS1"]:
        evidence_codes.append("BS1 (Moderately common)")
    if row["BP1"]:
        evidence_codes.append("BP1 (Missense in LOF gene)")
    if row["BP3"]:
        evidence_codes.append("BP3 (In-frame indel)")

    for code in evidence_codes:
        print(f"   ✓ {code}")

    print(f"\n   Total Evidence Codes: {row['total_evidence_codes']}")
    print(f"   Summary: {row.get('evidence_summary', 'N/A')}")

    # ACMG Classification
    print(f"\n🔬 ACMG Classification:")
    print(f"   {row['acmg_classification']}")
    print(f"   Reason: {row.get('classification_reason', 'N/A')}")

    # Clinical interpretation
    print(f"\n💡 Clinical Interpretation:")
    if row["PVS1"] and row["PM2"]:
        print(f"   ⚠️  HIGH PRIORITY: Loss of function + rare variant")
        print(f"   Likely to be clinically significant")
    elif row["PVS1"]:
        print(f"   ⚠️  Loss of function in constrained gene")
        print(f"   Review for clinical significance")

    if "stop_gained" in str(row.get("molecular_consequence", "")).lower():
        print(f"   ⚠️  Nonsense mutation (premature stop codon)")
    elif "frameshift" in str(row.get("molecular_consequence", "")).lower():
        print(f"   ⚠️  Frameshift mutation (disrupts protein)")

# Summary statistics
print(f"\n{'='*80}")
print("SUMMARY STATISTICS - ALL PVS1 VARIANTS")
print(f"{'='*80}")

print(f"\n📊 Gene Distribution (Top 10 genes with PVS1 variants):")
gene_counts = df["gene"].value_counts().head(10)
for gene, count in gene_counts.items():
    pct = count / len(df) * 100
    print(f"   {gene}: {count} variants ({pct:.1f}%)")

print(f"\n📊 Clinical Significance Distribution:")
clinvar_dist = df["clinical_sig"].value_counts()
for sig, count in clinvar_dist.items():
    pct = count / len(df) * 100
    print(f"   {sig}: {count} ({pct:.1f}%)")

print(f"\n📊 Consequence Types:")
# Parse molecular_consequence for common types
consequences = (
    df["molecular_consequence"]
    .str.extract(
        r"(stop_gained|frameshift|splice_acceptor|splice_donor|start_lost)",
        expand=False,
    )
    .value_counts()
)
for cons, count in consequences.items():
    pct = count / len(df) * 100
    print(f"   {cons}: {count} ({pct:.1f}%)")

print(f"\n📊 Additional Evidence:")
print(f"   PVS1 + PM2 (rare): {(df['PVS1'] & df['PM2']).sum()} variants")
print(f"   PVS1 + PM4 (protein length): {(df['PVS1'] & df['PM4']).sum()} variants")
print(f"   PVS1 only: {(df['PVS1'] & ~df['PM2'] & ~df['PM4']).sum()} variants")

# Frequency analysis
print(f"\n📊 Frequency Analysis (gnomAD):")
with_af = df[df["gnomad_af"].notna()]
print(f"   Variants with gnomAD data: {len(with_af)}")
if len(with_af) > 0:
    print(f"   Mean AF: {with_af['gnomad_af'].mean():.6f}")
    print(f"   Median AF: {with_af['gnomad_af'].median():.6f}")
    rare = (with_af["gnomad_af"] < 0.0001).sum()
    print(f"   Very rare (AF < 0.01%): {rare} ({rare/len(with_af)*100:.1f}%)")

print(f"\n{'='*80}")
print("END OF REPORT")
print(f"{'='*80}")
print(f"\n💾 Full list saved to: {pvs1_file}")
print(f"\n⚠️  RECOMMENDATION: Review these variants with a clinical geneticist")
