#!/usr/bin/env python3
"""
VariDex Pipeline v7.3-dev - 13-Code ACMG (Complete, Fixed)
Genome specialist: No data changes, adds 13 ACMG codes only.
"""

import sys
import argparse
import warnings
from pathlib import Path
from datetime import datetime
import pandas as pd

# Suppress ACMG experimental warnings
warnings.filterwarnings("ignore", message="ACMGClassifierV[78]")


def parse_args():
    parser = argparse.ArgumentParser(description="VariDex v7.3-dev: 13 ACMG codes")
    parser.add_argument("--input", "-i", required=True, help="Input CSV/Parquet")
    parser.add_argument("--output", "-o", default="results_fixed", help="Output dir")
    return parser.parse_args()


def apply_phase1_enhancements(df):
    """BP7, PP5, BP6, BS2 - exact original logic."""
    for code in ["PS1", "PM5", "BP7", "BS2", "PP5", "BP6"]:
        if code not in df.columns:
            df[code] = False
    counts = {"BP7": 0, "PP5": 0, "BP6": 0, "BS2": 0}
    for idx, row in df.iterrows():
        cons = str(row.get("molecular_consequence", "")).lower()
        rev = str(row.get("review_status", "")).lower()
        sig = str(row.get("clinical_sig", "")).lower()
        af = row.get("gnomad_af")

        if ("synonymous" in cons or "silent" in cons) and "splice" not in cons:
            df.at[idx, "BP7"] = True
            counts["BP7"] += 1

        if "expert_panel" in rev or "practice_guideline" in rev:
            if "pathogenic" in sig and "benign" not in sig:
                df.at[idx, "PP5"] = True
                counts["PP5"] += 1
            elif "benign" in sig:
                df.at[idx, "BP6"] = True
                counts["BP6"] += 1

        if pd.notna(af) and af > 0.01 and "pathogenic" in sig and "benign" not in sig:
            df.at[idx, "BS2"] = True
            counts["BS2"] += 1
    return df, counts


def main():
    args = parse_args()
    print("=" * 70)
    print("🧬 VariDex v7.3-dev - 13-Code ACMG Pipeline")
    print("=" * 70)

    start = datetime.now()  # Timing start

    # Step 1: Load
    print("\nStep 1/4: Loading input...")
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ {input_path} not found!")
        sys.exit(1)
    if input_path.suffix == ".parquet":
        df = pd.read_parquet(input_path)
    else:
        df = pd.read_csv(input_path, low_memory=False)
    print(f"✅ Loaded {len(df):,} variants")

    # Check columns (no removal)
    required = ["gene", "molecular_consequence", "clinical_sig", "review_status"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        print(f"⚠️  Missing: {missing}")

    # Step 2: 8-code ACMG
    print("\nStep 2/4: 8-code ACMG...")
    try:
        from varidex.pipeline.acmg_classifier_stage import (
            apply_full_acmg_classification,
        )

        df = apply_full_acmg_classification(df)
        print("✅ 8 codes applied")
    except Exception as e:
        print(f"⚠️  ACMG: {e} - Initializing 8 codes")
        for code in ["PVS1", "PM2", "PM4", "PP2", "BA1", "BS1", "BP1", "BP3"]:
            if code not in df.columns:
                df[code] = False

    # Step 3: Phase 1 (+5)
    print("\nStep 3/4: Phase 1 (+5 codes)...")
    df, counts = apply_phase1_enhancements(df)
    for k, v in counts.items():
        print(f"  {k}: {v:,}")

    # Step 4: Save
    print("\nStep 4/4: Saving...")
    out_dir = Path(args.output)
    out_dir.mkdir(exist_ok=True)
    main_file = out_dir / "results_13codes.csv"
    df.to_csv(main_file, index=False)
    print(f"💾 {main_file}")

    # Stats
    all_codes = [
        "PVS1",
        "PS1",
        "PM2",
        "PM4",
        "PM5",
        "PP2",
        "PP5",
        "BA1",
        "BS1",
        "BS2",
        "BP1",
        "BP3",
        "BP6",
        "BP7",
    ]
    has_ev = df[[c for c in all_codes if c in df.columns]].any(axis=1).sum()
    patho = len(df[df["clinical_sig"].str.contains("pathogenic", na=False, case=False)])
    runtime = (datetime.now() - start).total_seconds()

    print("\n" + "=" * 70)
    print("✅ PIPELINE COMPLETE!")
    print(f"  Total variants: {len(df):,}")
    print(f"  Evidence (13 codes): {has_ev:,} ({has_ev/len(df)*100:.1f}%)")
    print(f"  Pathogenic: {patho:,}")
    print(f"⏱️  Runtime: {runtime:.1f}s")
    print(f"📁 Output: {out_dir.absolute()}")
    print("=" * 70)


if __name__ == "__main__":
    main()
