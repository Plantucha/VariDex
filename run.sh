#!/usr/bin/env bash
# VariDex Analysis Pipeline v7.0 - With Parallel Processing

set -e

echo "======================================================================"
echo "VariDex v7.0 - Genome Analysis Pipeline (PARALLEL)"
echo "======================================================================"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run analysis with improved matching
python3 << 'PYTHON_EOF'
from pathlib import Path
from varidex.io.loaders.user import load_user_file
from varidex.io.loaders.clinvar import load_clinvar_file
from varidex.io.matching_improved import match_variants_hybrid
import time

print("\n⏱️  Starting analysis...")
t0 = time.time()

# Load data
user_df = load_user_file(Path('data/raw.txt'), file_format='23andme')
clinvar_df = load_clinvar_file(Path('clinvar/clinvar_GRCh37.vcf'))

# Match variants (improved algorithm)
matched, rsid_count, coord_count = match_variants_hybrid(
    clinvar_df, user_df, 'vcf', '23andme'
)

elapsed = time.time() - t0

# Save results
matched.to_csv('output/results.csv', index=False)

# Report
print("\n" + "=" * 70)
print("RESULTS SUMMARY")
print("=" * 70)
print(f"\n⏱️  Total time: {elapsed:.1f}s")
print(f"\n✅ ClinVar variants: {len(clinvar_df):,}")
print(f"✅ User variants: {len(user_df):,}")
print(f"✅ Matches: {len(matched):,}")
print(f"   - rsID matches: {rsid_count:,}")
print(f"   - Coordinate matches: {coord_count:,}")

if 'clinical_sig' in matched.columns:
    pathogenic = matched[matched['clinical_sig'].str.contains('Pathogenic', case=False, na=False)]
    benign = matched[matched['clinical_sig'].str.contains('Benign', case=False, na=False)]
    uncertain = matched[matched['clinical_sig'].str.contains('Uncertain', case=False, na=False)]
    
    print(f"\n🏥 Clinical Significance:")
    print(f"   🔴 Pathogenic/Likely: {len(pathogenic):,}")
    print(f"   🟢 Benign/Likely: {len(benign):,}")
    print(f"   🟡 Uncertain (VUS): {len(uncertain):,}")

print(f"\n📄 Output: output/results.csv")
print("\n" + "=" * 70)
print("✅ ANALYSIS COMPLETE")
print("=" * 70)
PYTHON_EOF

echo ""
echo "Done! Results saved to output/results.csv"
