#!/usr/bin/env python3
"""
Annotate matched variants with gnomAD frequencies and apply ACMG criteria.
"""

import pandas as pd
from pathlib import Path
import sys
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from varidex.io.loaders.clinvar import load_clinvar_file
from varidex.io.loaders.user import load_user_file
from varidex.io import matching
from varidex.pipeline.gnomad_annotator import (
    annotate_with_gnomad,
    apply_frequency_acmg_criteria,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("=" * 70)
print("📥 GNOMAD ANNOTATION PIPELINE v6.4.0")
print("=" * 70)

print("\nLoading ClinVar...")
clinvar = load_clinvar_file("clinvar/clinvar_GRCh37.vcf")
print(f"✓ Loaded {len(clinvar):,} ClinVar variants")

print("\nLoading user genome...")
user = load_user_file("data/raw.txt")
print(f"✓ Loaded {len(user):,} user variants")

print("\nMatching variants...")
matched = matching.match_variants_hybrid(clinvar, user, "vcf", "23andme")[0]
print(f"✓ Matched {len(matched):,} variants")

print("\n" + "=" * 70)
print("ANNOTATING WITH GNOMAD")
print("=" * 70)
gnomad_dir = Path("gnomad")
matched_annotated = annotate_with_gnomad(matched, gnomad_dir)

matched_with_criteria = apply_frequency_acmg_criteria(matched_annotated)

matched_with_criteria["clinvar_class"] = matched_with_criteria[
    "clinical_sig"
].str.replace("_", " ", regex=False)

output_dir = Path("output")
output_dir.mkdir(exist_ok=True)
output_file = output_dir / "michal_gnomad_annotated.csv"
matched_with_criteria.to_csv(output_file, index=False)

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

total = len(matched_with_criteria)
with_af = matched_with_criteria["gnomad_af"].notna().sum()
ba1 = matched_with_criteria["BA1"].sum()
bs1 = matched_with_criteria["BS1"].sum()
pm2 = matched_with_criteria["PM2"].sum()

print(f"Total variants: {total:,}")
print(f"With gnomAD frequency: {with_af:,} ({with_af/total*100:.1f}%)")
print(f"\nACMG Frequency Criteria:")
print(f"  🟢 BA1 (>5% benign): {ba1:,}")
print(f"  🟢 BS1 (>1% benign): {bs1:,}")
print(f"  🔴 PM2 (<0.01% pathogenic): {pm2:,}")
print(f"\n✅ Saved to: {output_file}")
