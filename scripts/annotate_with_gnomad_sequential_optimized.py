#!/usr/bin/env python3
"""
Annotate with gnomAD - OPTIMIZED SEQUENTIAL VERSION
Sometimes sequential is faster for I/O-bound tasks!
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import time
from tqdm import tqdm

# Patch tqdm
import tqdm.std as tqdm_std

original_tqdm_init = tqdm_std.tqdm.__init__


def patched_tqdm_init(self, *args, **kwargs):
    original_tqdm_init(self, *args, **kwargs)


tqdm_std.tqdm.__init__ = patched_tqdm_init

from varidex.io.loaders.clinvar import load_clinvar_file
from varidex.io.loaders.user import load_user_file
from varidex.io import matching
from varidex.integrations.gnomad.query import GnomADQuerier

print("=" * 80)
print("📥 GNOMAD ANNOTATION - OPTIMIZED SEQUENTIAL")
print("=" * 80)
print("\nNote: Sequential can be faster for I/O-bound compressed VCF files")

print("\nLoading ClinVar...")
clinvar = load_clinvar_file("clinvar/clinvar_GRCh37.vcf")
print(f"✓ {len(clinvar):,} variants")

print("\nLoading user genome...")
user = load_user_file("data/raw.txt")
print(f"✓ {len(user):,} variants")

print("\nMatching...")
matched = matching.match_variants_hybrid(clinvar, user, "vcf", "23andme")[0]
print(f"✓ {len(matched):,} matched")

print(f"\n⚡ Annotating {len(matched):,} variants with gnomAD (sequential)...")
start_time = time.time()

frequencies = []

with GnomADQuerier(Path("gnomad")) as querier:
    for idx, row in tqdm(
        matched.iterrows(), total=len(matched), desc="Querying gnomAD", unit="var"
    ):
        try:
            result = querier.query(
                str(row["chromosome"]),
                int(row["position"]),
                str(row["ref_allele"]),
                str(row["alt_allele"]),
            )
            frequencies.append(result.af)
        except Exception as e:
            frequencies.append(None)

matched["gnomad_af"] = frequencies

elapsed = time.time() - start_time
rate = len(matched) / elapsed if elapsed > 0 else 0

print(f"\n⏱️  Annotation completed in {elapsed:.1f}s ({rate:.1f} variants/sec)")

# Apply ACMG criteria
print("\nApplying frequency criteria...")
matched["BA1"] = matched["gnomad_af"] > 0.05
matched["BS1"] = (matched["gnomad_af"] > 0.01) & (matched["gnomad_af"] <= 0.05)
matched["PM2"] = matched["gnomad_af"] < 0.0001

matched["clinvar_class"] = matched["clinical_sig"].str.replace("_", " ", regex=False)

output = Path("output/michal_gnomad_sequential.csv")
output.parent.mkdir(exist_ok=True)
matched.to_csv(output, index=False)

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
total = len(matched)
with_af = matched["gnomad_af"].notna().sum()
ba1 = matched["BA1"].sum()
bs1 = matched["BS1"].sum()
pm2 = matched["PM2"].sum()

print(f"\nTotal: {total:,}")
print(f"With gnomAD: {with_af:,} ({with_af/total*100:.1f}%)")
print(f"\n🟢 BA1 (>5%): {ba1:,}")
print(f"🟢 BS1 (>1%): {bs1:,}")
print(f"🔴 PM2 (<0.01%): {pm2:,}")
print(f"\n⏱️  Time: {elapsed/60:.1f} minutes ({rate:.1f} var/s)")
print(f"\n✅ {output}")
