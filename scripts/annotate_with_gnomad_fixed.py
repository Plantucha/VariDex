#!/usr/bin/env python3
"""
Annotate matched variants with gnomAD - Compatibility Fix
"""

# MUST patch tqdm BEFORE any imports that use it
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Monkey-patch tqdm to avoid pandas compatibility issue
import tqdm.std as tqdm_std

original_tqdm_init = tqdm_std.tqdm.__init__


def patched_tqdm_init(self, *args, **kwargs):
    original_tqdm_init(self, *args, **kwargs)


tqdm_std.tqdm.__init__ = patched_tqdm_init

# Disable pandas progress_apply
import pandas as pd

if hasattr(pd.core.frame.NDFrame, "progress_apply"):
    delattr(pd.core.frame.NDFrame, "progress_apply")

# Now safe to import everything else
from varidex.io.loaders.clinvar import load_clinvar_file
from varidex.io.loaders.user import load_user_file
from varidex.io import matching
from varidex.pipeline.gnomad_annotator import (
    annotate_with_gnomad,
    apply_frequency_acmg_criteria,
)

print("=" * 70)
print("📥 GNOMAD ANNOTATION PIPELINE v6.4.0")
print("=" * 70)

print("\nLoading ClinVar...")
clinvar = load_clinvar_file("clinvar/clinvar_GRCh37.vcf")
print(f"✓ {len(clinvar):,} variants")

print("\nLoading user genome...")
user = load_user_file("data/raw.txt")
print(f"✓ {len(user):,} variants")

print("\nMatching...")
matched = matching.match_variants_hybrid(clinvar, user, "vcf", "23andme")[0]
print(f"✓ {len(matched):,} matched")

print("\nAnnotating with gnomAD (~3 min)...")
matched_annotated = annotate_with_gnomad(matched, Path("gnomad"))

print("\nApplying frequency criteria...")
result = apply_frequency_acmg_criteria(matched_annotated)

result["clinvar_class"] = result["clinical_sig"].str.replace("_", " ", regex=False)

output = Path("output/michal_gnomad_annotated.csv")
output.parent.mkdir(exist_ok=True)
result.to_csv(output, index=False)

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
total = len(result)
with_af = result["gnomad_af"].notna().sum()
ba1 = result["BA1"].sum()
bs1 = result["BS1"].sum()
pm2 = result["PM2"].sum()

print(f"Total: {total:,}")
print(f"With gnomAD: {with_af:,} ({with_af/total*100:.1f}%)")
print(f"\n🟢 BA1 (>5%): {ba1:,}")
print(f"🟢 BS1 (>1%): {bs1:,}")
print(f"🔴 PM2 (<0.01%): {pm2:,}")
print(f"\n✅ {output}")
