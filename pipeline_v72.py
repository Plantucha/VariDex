#!/usr/bin/env python3
"""
VariDex Pipeline v7.3-dev - Fixed runtime + warnings
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
import pandas as pd
import warnings

# Suppress ACMG warnings (add after parse_args)
warnings.filterwarnings("ignore", message="ACMGClassifierV[78]")

# Fix timing (replace line 108)
runtime = (datetime.now() - start).total_seconds()
print(f"⏱️  {runtime:.1f}s")  # Use before print block


def parse_args():
    parser = argparse.ArgumentParser(description="VariDex v7.3-dev: 13 ACMG codes")
    parser.add_argument("--input", "-i", required=True)
    parser.add_argument("--output", "-o", default="results_fixed")
    return parser.parse_args()


def apply_phase1_enhancements(df):
    for code in ["PS1", "PM5", "BP7", "BS2", "PP5", "BP6"]:
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
    print("🧬 VariDex v7.3-dev - 13-Code ACMG (Fixed)")
    print("=" * 70)
    start = datetime.now()

    print("\nStep 1/4: Loading...")
    input_path = Path(args.input)
    if input_path.suffix == ".parquet":
        df = pd.read_parquet(input_path)
    else:
        df = pd.read_csv(input_path, low_memory=False)
    print(f"✅ Loaded {len(df):,} variants")

    required
