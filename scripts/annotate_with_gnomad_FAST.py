#!/usr/bin/env python3
"""
Annotate with gnomAD - RESTORED FAST VERSION (5x speedup!)
Uses the commit c11e7e4 implementation
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Patch tqdm
import tqdm.std as tqdm_std
original_tqdm_init = tqdm_std.tqdm.__init__
def patched_tqdm_init(self, *args, **kwargs):
    original_tqdm_init(self, *args, **kwargs)
tqdm_std.tqdm.__init__ = patched_tqdm_init

import pandas as pd
import time

from varidex.io.loaders.clinvar import load_clinvar_file
from varidex.io.loaders.user import load_user_file
from varidex.io import matching

# Import the FAST parallel version
from varidex.pipeline.gnomad_annotator_parallel import (
    annotate_with_gnomad_parallel,
    apply_frequency_acmg_criteria,
)

print("=" * 80)
print("📥 GNOMAD ANNOTATION - RESTORED FAST VERSION (5x SPEEDUP)")
print("=" * 80)
print("\n⚡ Using commit c11e7e4 implementation:")
print("   - ProcessPoolExecutor with 6 workers")
print("   - Direct pysam.TabixFile queries")
print("   - Batch processing")
print("   - Original performance: 9m28s → 1m53s")
print("=" * 80)

print("\nLoading ClinVar...")
start_total = time.time()
clinvar = load_clinvar_file("clinvar/clinvar_GRCh37.vcf")
print(f"✓ {len(clinvar):,} variants")

print("\nLoading user genome...")
user = load_user_file("data/raw.txt")
print(f"✓ {len(user):,} variants")

print("\nMatching...")
matched = matching.match_variants_hybrid(clinvar, user, "vcf", "23andme")[0]
print(f"✓ {len(matched):,} matched")

print(f"\n⚡ Annotating with gnomAD (FAST parallel version)...")
print(f"   Expected: ~2 minutes (5x faster than 9.5 min)")
start_annot = time.time()

# Use the FAST parallel version with 6 workers
matched_annotated = annotate_with_gnomad_parallel(
    matched,
    Path("gnomad"),
    n_workers=6  # Same as original fast version
)

elapsed_annot = time.time() - start_annot
rate = len(matched) / elapsed_annot

print(f"\n✓ Annotation: {elapsed_annot/60:.1f} min ({rate:.1f} var/s)")

print("\nApplying ACMG frequency criteria...")
result = apply_frequency_acmg_criteria(matched_annotated)

result["clinvar_class"] = result["clinical_sig"].str.replace("_", " ", regex=False)

output = Path("output/michal_gnomad_FAST.csv")
output.parent.mkdir(exist_ok=True)
result.to_csv(output, index=False)

elapsed_total = time.time() - start_total

print("\n" + "=" * 80)
print("RESULTS")
print("=" * 80)

total = len(result)
with_af = result["gnomad_af"].notna().sum()
ba1 = result["BA1"].sum()
bs1 = result["BS1"].sum()
pm2 = result["PM2"].sum()

print(f"\nTotal variants:   {total:,}")
print(f"With gnomAD data: {with_af:,} ({with_af/total*100:.1f}%)")

print(f"\nACMG Evidence Codes:")
print(f"  🟢 BA1 (>5%):    {ba1:,} variants")
print(f"  🟢 BS1 (1-5%):   {bs1:,} variants")
print(f"  🔴 PM2 (<0.01%): {pm2:,} variants")

pathogenic_pm2 = result[
    (result['PM2'] == True) & 
    (result['clinical_sig'].str.contains('athogenic', na=False, case=False))
]
print(f"\n⭐ Pathogenic + PM2: {len(pathogenic_pm2):,} variants")

print(f"\n⏱️  Performance:")
print(f"  Annotation: {elapsed_annot/60:.1f} min ({rate:.1f} var/s)")
print(f"  Total time: {elapsed_total/60:.1f} min")

# Compare to sequential
sequential_time = 9.5  # minutes
speedup = sequential_time / (elapsed_annot / 60)
print(f"  Speedup vs sequential: {speedup:.1f}x ⚡")

print(f"\n✅ Results: {output}")
print("=" * 80)
