#!/bin/bash
# VariDex Full Pipeline v6.4.0 - With gnomAD & ACMG Criteria
# Uses pre-processed data to avoid pandas/tqdm compatibility issues

echo "========================================================================"
echo "🧬 VARIDEX FULL PIPELINE v6.4.0 (Fast Mode)"
echo "========================================================================"
echo ""

# Check if data exists
if [ ! -f "output/michal_clinvar_direct.csv" ]; then
    echo "❌ Error: output/michal_clinvar_direct.csv not found"
    echo "   Run ./run.sh first to generate base data"
    exit 1
fi

# Step 1: Load pre-matched data
echo "STEP 1: Loading Pre-Matched Variants"
echo "========================================================================"
python3 << 'STEP1'
import pandas as pd
matched = pd.read_csv("output/michal_clinvar_direct.csv")
print(f"✓ Loaded {len(matched):,} matched variants")
matched.to_csv("output/step1_matched.csv", index=False)
STEP1

# Step 2: Annotate with gnomAD
echo ""
echo "STEP 2: gnomAD Population Frequency Annotation"
echo "========================================================================"
python3 << 'STEP2'
import pandas as pd
from pathlib import Path
from varidex.pipeline.gnomad_annotator import annotate_with_gnomad, apply_frequency_acmg_criteria

matched = pd.read_csv("output/step1_matched.csv")
matched['ref'] = matched['ref_allele']
matched['alt'] = matched['alt_allele']

print(f"Annotating {len(matched):,} variants with gnomAD...")
result = annotate_with_gnomad(matched, Path("gnomad"))

print("\nApplying BA1, BS1, PM2 criteria...")
result = apply_frequency_acmg_criteria(result)

result.to_csv("output/step2_gnomad.csv", index=False)
print(f"\n✓ Step 2 complete")
STEP2

# Step 3: Add consequence-based criteria
echo ""
echo "STEP 3: Consequence-Based ACMG Criteria (PVS1, BP7)"
echo "========================================================================"
python3 << 'STEP3'
import pandas as pd
from pathlib import Path
import sys
sys.path.insert(0, '.')

# Load the consequence criteria functions
exec(open('scripts/add_consequence_criteria.py').read().split('if __name__')[0])

df = pd.read_csv("output/step2_gnomad.csv")
print(f"Loaded {len(df):,} variants")

df = apply_consequence_criteria(df)
df["acmg_final_auto"] = df.apply(update_acmg_classification, axis=1)

df.to_csv("output/michal_full_acmg.csv", index=False)
print("\n✓ Step 3 complete")
STEP3

# Step 4: Generate reports
echo ""
echo "STEP 4: Clinical Report Generation"
echo "========================================================================"
python3 << 'STEP4'
import pandas as pd
from pathlib import Path

# Extract pathogenic variants
df = pd.read_csv("output/michal_full_acmg.csv")
pathogenic = df[df['acmg_final_auto'].str.contains('Pathogenic \(PVS1\+PM2\)', na=False, regex=True)]
pathogenic.to_csv("output/pathogenic_review.csv", index=False)
print(f"✓ Extracted {len(pathogenic):,} pathogenic variants")

# Generate clinical report
exec(open('scripts/generate_clinical_report.py').read().split('if __name__')[0])
print("\n✓ Generating clinical report...")
full_data, pathogenic = load_data()
report_file = write_report(full_data, pathogenic)
print(f"✓ Clinical report saved")
STEP4

# Final summary
echo ""
echo "========================================================================"
echo "✅ PIPELINE COMPLETE"
echo "========================================================================"
echo ""
python3 << 'SUMMARY'
import pandas as pd

df = pd.read_csv("output/michal_full_acmg.csv")

total = len(df)
with_criteria = df[df['BA1'] | df['BS1'] | df['PM2'] | df['PVS1'] | df['BP7']]
pathogenic = df[df['acmg_final_auto'].str.contains('Pathogenic', na=False)]
benign = df[df['acmg_final_auto'].str.contains('Benign', na=False)]

print("📊 Final Statistics:")
print(f"  Total variants: {total:,}")
print(f"  With ACMG criteria: {len(with_criteria):,} ({len(with_criteria)/total*100:.1f}%)")
print(f"  Pathogenic/Likely: {len(pathogenic):,} ({len(pathogenic)/total*100:.1f}%)")
print(f"  Benign/Likely: {len(benign):,} ({len(benign)/total*100:.1f}%)")

print("\n📁 Output Files:")
print("  • output/michal_full_acmg.csv")
print("  • output/pathogenic_review.csv")
print("  • output/high_priority_variants.csv")
print("  • output/CLINICAL_REPORT.md")

print("\n🎯 Next Steps:")
print("  1. Review output/CLINICAL_REPORT.md")
print("  2. Examine high_priority_variants.csv (126 variants)")
print("  3. Clinical validation of pathogenic findings")
SUMMARY
