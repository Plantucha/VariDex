#!/usr/bin/env python3
"""
Add PVS1 and BP7 ACMG criteria based on variant consequences.

PVS1: Null variants (nonsense, frameshift, splice) - Very Strong Pathogenic
BP7: Synonymous variants with no splice impact - Supporting Benign
"""

import pandas as pd
from pathlib import Path
import re


def is_lof_variant(consequence: str) -> bool:
    """
    Check if variant is loss-of-function (PVS1 eligible).

    PVS1 applies to:
    - Nonsense (stop gain)
    - Frameshift
    - Canonical splice site (±1 or 2)
    - Initiation codon
    - Single/multi-exon deletion
    """
    if pd.isna(consequence):
        return False

    consequence = consequence.lower()
    lof_terms = [
        "nonsense",
        "stop_gained",
        "frameshift",
        "splice_acceptor",
        "splice_donor",
        "start_lost",
        "initiation_codon",
    ]

    return any(term in consequence for term in lof_terms)


def is_synonymous_variant(consequence: str) -> bool:
    """
    Check if variant is synonymous (BP7 eligible).

    BP7 applies to synonymous variants that:
    - Don't affect splicing
    - Are in coding regions
    """
    if pd.isna(consequence):
        return False

    consequence = consequence.lower()

    # Must be synonymous
    if "synonymous" not in consequence:
        return False

    # Exclude if affects splicing
    if any(term in consequence for term in ["splice", "splicing", "splice_region"]):
        return False

    return True


def apply_consequence_criteria(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply PVS1 and BP7 criteria based on molecular consequences.

    Args:
        df: DataFrame with molecular_consequence column

    Returns:
        DataFrame with PVS1 and BP7 columns added
    """
    print("\nApplying consequence-based ACMG criteria...")

    # Apply PVS1
    df["PVS1"] = df["molecular_consequence"].apply(is_lof_variant)
    pvs1_count = df["PVS1"].sum()
    print(f"  🔴 PVS1 (LOF variants): {pvs1_count:,}")

    # Apply BP7
    df["BP7"] = df["molecular_consequence"].apply(is_synonymous_variant)
    bp7_count = df["BP7"].sum()
    print(f"  🟢 BP7 (synonymous): {bp7_count:,}")

    return df


def update_acmg_classification(row) -> str:
    """
    Update ACMG classification based on all criteria.

    Simplified classification rules:
    - PVS1 alone = Likely Pathogenic
    - PVS1 + PM2 = Pathogenic
    - BA1 alone = Benign
    - BP7 + BS1 = Benign
    """
    # Benign stand-alone
    if row.get("BA1", False):
        return "Benign (BA1)"

    # Very strong pathogenic
    if row.get("PVS1", False):
        if row.get("PM2", False):
            return "Pathogenic (PVS1+PM2)"
        return "Likely Pathogenic (PVS1)"

    # Strong benign
    if row.get("BS1", False):
        if row.get("BP7", False):
            return "Benign (BS1+BP7)"
        return "Likely Benign (BS1)"

    # Supporting benign
    if row.get("BP7", False):
        return "Likely Benign (BP7)"

    # Moderate pathogenic
    if row.get("PM2", False):
        return "VUS (PM2 only)"

    return "VUS"


def main():
    print("=" * 70)
    print("📥 ADDING CONSEQUENCE-BASED ACMG CRITERIA")
    print("=" * 70)

    # Load gnomAD-annotated data
    input_file = Path("output/michal_gnomad_annotated.csv")
    if not input_file.exists():
        print(f"❌ Error: {input_file} not found")
        print("   Run gnomAD annotation first!")
        return

    print(f"\nLoading {input_file}...")
    df = pd.read_csv(input_file)
    print(f"✓ Loaded {len(df):,} variants")

    # Check for required column
    if "molecular_consequence" not in df.columns:
        print("❌ Error: molecular_consequence column not found")
        return

    # Apply new criteria
    df = apply_consequence_criteria(df)

    # Update classifications
    print("\nUpdating ACMG classifications...")
    df["acmg_final_auto"] = df.apply(update_acmg_classification, axis=1)

    # Save enhanced results
    output_file = Path("output/michal_full_acmg.csv")
    df.to_csv(output_file, index=False)

    # Generate summary
    print("\n" + "=" * 70)
    print("SUMMARY - ACMG Criteria Applied")
    print("=" * 70)

    total = len(df)

    # Frequency criteria
    ba1 = df["BA1"].sum()
    bs1 = df["BS1"].sum()
    pm2 = df["PM2"].sum()

    # Consequence criteria
    pvs1 = df["PVS1"].sum()
    bp7 = df["BP7"].sum()

    # Combined
    with_criteria = df[df["BA1"] | df["BS1"] | df["PM2"] | df["PVS1"] | df["BP7"]]
    criteria_count = len(with_criteria)

    print(f"Total variants: {total:,}")
    print(f"With ACMG criteria: {criteria_count:,} ({criteria_count/total*100:.1f}%)")
    print(f"\nFrequency-based (gnomAD):")
    print(f"  🟢 BA1 (>5%): {ba1:,}")
    print(f"  🟢 BS1 (>1%): {bs1:,}")
    print(f"  🔴 PM2 (<0.01%): {pm2:,}")
    print(f"\nConsequence-based:")
    print(f"  🔴 PVS1 (LOF): {pvs1:,}")
    print(f"  🟢 BP7 (synonymous): {bp7:,}")

    # Classification breakdown
    print(f"\nAutomated Classifications:")
    class_counts = df["acmg_final_auto"].value_counts()
    for classification, count in class_counts.head(10).items():
        print(f"  {classification}: {count:,}")

    print(f"\n✅ Saved to: {output_file}")
    print(f"\n🎯 Now using 5 of 28 ACMG criteria!")


if __name__ == "__main__":
    main()
