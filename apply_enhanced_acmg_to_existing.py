#!/usr/bin/env python3
"""
Apply enhanced ACMG classification to existing complete_results.csv

Much faster than re-running the whole pipeline!
"""

import logging
import pandas as pd
from pathlib import Path
from varidex.pipeline.acmg_classifier_stage import apply_full_acmg_classification

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

print("=" * 80)
print("APPLYING ENHANCED ACMG TO EXISTING RESULTS")
print("=" * 80)

# Load existing results
input_file = Path("output/complete_results.csv")
logger.info(f"\n📂 Loading {input_file}...")
df = pd.read_csv(input_file, low_memory=False)
logger.info(f"✅ Loaded {len(df):,} variants")

# Apply enhanced ACMG
logger.info("\n🧬 Applying enhanced ACMG classification (8 codes)...")
result = apply_full_acmg_classification(df)

# Save enhanced results
output_file = Path("output/complete_results_ENHANCED_ACMG.csv")
result.to_csv(output_file, index=False)
logger.info(f"\n✅ Saved: {output_file}")

# Create priority files
logger.info("\n📊 Creating priority files...")

# Priority files
pathogenic = result[result["clinical_sig"].str.contains("athogenic", na=False)]

# Priority 1: PVS1
pvs1 = pathogenic[pathogenic["PVS1"]]
pvs1_file = Path("output/PRIORITY_1_PVS1_loss_of_function.csv")
pvs1.to_csv(pvs1_file, index=False)
logger.info(f"  Priority 1 (PVS1): {len(pvs1):,} → {pvs1_file}")

# Priority 2: PM2 (rare)
pm2 = pathogenic[pathogenic["PM2"]]
pm2_file = Path("output/PRIORITY_2_PM2_rare_pathogenic.csv")
pm2.to_csv(pm2_file, index=False)
logger.info(f"  Priority 2 (PM2): {len(pm2):,} → {pm2_file}")

# Benign with strong evidence
benign = result[result["clinical_sig"].str.contains("enign", na=False)]
ba1 = benign[benign["BA1"]]
ba1_file = Path("output/benign_BA1_common.csv")
ba1.to_csv(ba1_file, index=False)
logger.info(f"  Benign (BA1): {len(ba1):,} → {ba1_file}")

# Summary statistics
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

logger.info(f"\n📈 Evidence Distribution:")
for code in ["PVS1", "PM2", "PM4", "PP2", "BA1", "BS1", "BP1", "BP3"]:
    count = result[code].sum()
    pct = count / len(result) * 100
    bar = "█" * int(pct / 2)
    logger.info(f"  {code}: {count:,} ({pct:.1f}%) {bar}")

with_evidence = result[result["evidence_summary"] != ""]
logger.info(
    f"\n🎯 Variants with ACMG evidence: {len(with_evidence):,} ({len(with_evidence)/len(result)*100:.1f}%)"
)

logger.info(f"\n📁 Output directory: output/")
print("=" * 80)
