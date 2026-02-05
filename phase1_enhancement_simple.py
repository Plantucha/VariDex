#!/usr/bin/env python3
"""
Phase 1 ACMG Enhancement - Simple Version

Run directly: python3 phase1_enhancement_simple.py
Or import: from phase1_enhancement_simple import add_phase1_codes
"""

import pandas as pd

print("=" * 70)
print("Phase 1 ACMG Enhancement Module - LOADED")
print("=" * 70)
print()


def add_phase1_codes(results_df):
    """Add BP7, PP5, BP6, BS2 codes to results."""

    print(f"Processing {len(results_df):,} variants...")

    # Add columns
    for code in ["PS1", "PM5", "BP7", "BS2", "PP5", "BP6"]:
        if code not in results_df.columns:
            results_df[code] = False

    counts = {"BP7": 0, "PP5": 0, "BP6": 0, "BS2": 0}

    for idx, row in results_df.iterrows():
        cons = str(row.get("molecular_consequence", "")).lower()
        rev = str(row.get("review_status", "")).lower()
        sig = str(row.get("clinical_sig", "")).lower()
        af = row.get("gnomad_af")

        # BP7
        if ("synonymous" in cons or "silent" in cons) and "splice" not in cons:
            results_df.at[idx, "BP7"] = True
            counts["BP7"] += 1

        # PP5/BP6
        if "expert_panel" in rev or "practice_guideline" in rev:
            if "pathogenic" in sig and "benign" not in sig:
                results_df.at[idx, "PP5"] = True
                counts["PP5"] += 1
            elif "benign" in sig:
                results_df.at[idx, "BP6"] = True
                counts["BP6"] += 1

        # BS2
        if pd.notna(af) and af > 0.01 and "pathogenic" in sig and "benign" not in sig:
            results_df.at[idx, "BS2"] = True
            counts["BS2"] += 1

    print(
        f"Added: BP7={counts['BP7']:,}, PP5={counts['PP5']:,}, BP6={counts['BP6']:,}, BS2={counts['BS2']:,}"
    )
    return results_df


if __name__ == "__main__":
    print("USAGE:")
    print("-" * 70)
    print()
    print("1. Import into your pipeline:")
    print("   from phase1_enhancement_simple import add_phase1_codes")
    print("   results_df = add_phase1_codes(results_df)")
    print()
    print("2. Test with cached results:")
    print()

    from pathlib import Path

    cached = Path("output/complete_results.csv")

    if cached.exists():
        print(f"   Found: {cached}")
        print("   Testing...")
        df = pd.read_csv(cached, nrows=100)
        df = add_phase1_codes(df)
        print("   ✅ Test successful!")
    else:
        print(f"   ❌ Test file not found: {cached}")
        print("   Generate it first with your pipeline")

    print()
    print("=" * 70)
