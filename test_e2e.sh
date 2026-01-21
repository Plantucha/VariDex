#!/bin/bash
# test_e2e.sh - End-to-End VariDex Pipeline Test
# Tests the complete workflow from data loading to classification

set -e  # Exit on any error

echo "======================================================================"
echo "VariDex v6.0.0 - END-TO-END PIPELINE TEST"
echo "======================================================================"
echo
echo "This will test the complete VariDex workflow:"
echo "  1. Load ClinVar data"
echo "  2. Load user genome data"
echo "  3. Match variants"
echo "  4. Classify variants (ACMG)"
echo "  5. Generate summary reports"
echo
read -p "Press Enter to start..."
echo

# ======================================================================
# STEP 1: Environment Check
# ======================================================================
echo "======================================================================"
echo "STEP 1: Environment Check"
echo "======================================================================"
echo

if [ ! -d "data" ]; then
    echo "❌ Error: data/ directory not found"
    echo "   Please ensure data/clinvar_GRCh38.vcf exists"
    exit 1
fi

if [ ! -d "varidex" ]; then
    echo "❌ Error: varidex/ package not found"
    exit 1
fi

echo "✓ data/ directory exists"
echo "✓ varidex/ package exists"
echo

# Check for required data files
if [ -f "data/clinvar_GRCh38.vcf" ]; then
    echo "✓ ClinVar VCF found"
    CLINVAR_SIZE=$(du -h data/clinvar_GRCh38.vcf | cut -f1)
    echo "  Size: $CLINVAR_SIZE"
elif [ -f "data/clinvar_GRCh38.vcf.gz" ]; then
    echo "✓ ClinVar VCF.GZ found"
    CLINVAR_SIZE=$(du -h data/clinvar_GRCh38.vcf.gz | cut -f1)
    echo "  Size: $CLINVAR_SIZE"
else
    echo "❌ Error: No ClinVar file found"
    exit 1
fi

# Find user genome file
USER_GENOME=$(ls data/genome_*.txt 2>/dev/null | head -1)
if [ -z "$USER_GENOME" ]; then
    echo "❌ Error: No user genome file found (data/genome_*.txt)"
    exit 1
fi
echo "✓ User genome found: $(basename $USER_GENOME)"
USER_SIZE=$(du -h "$USER_GENOME" | cut -f1)
echo "  Size: $USER_SIZE"
echo

# ======================================================================
# STEP 2: Clean Previous Results
# ======================================================================
echo "======================================================================"
echo "STEP 2: Clean Previous Test Results"
echo "======================================================================"
echo

if [ -d "test_output" ]; then
    echo "Cleaning test_output/..."
    rm -f test_output/*.csv
    echo "✓ Cleaned"
else
    mkdir -p test_output
    echo "✓ Created test_output/"
fi
echo

# ======================================================================
# STEP 3: Import Test
# ======================================================================
echo "======================================================================"
echo "STEP 3: Testing VariDex Imports"
echo "======================================================================"
echo

python3 << 'EOF'
import sys

print("Testing imports...")
try:
    from varidex.version import __version__
    print(f"✓ varidex v{__version__}")

    from varidex.core.config import LOF_GENES, MISSENSE_RARE_GENES
    print(f"✓ config.py loaded ({len(LOF_GENES)} LOF genes, {len(MISSENSE_RARE_GENES)} missense-rare genes)")

    from varidex.core.models import VariantData, ACMGEvidenceSet
    print(f"✓ models.py loaded")

    from varidex.io.loaders.clinvar import load_clinvar
    print(f"✓ ClinVar loader")

    from varidex.io.loaders.user import load_user_genome
    print(f"✓ User genome loader")

    from varidex.io.matching import match_variants_hybrid
    print(f"✓ Variant matcher")

    from varidex.core.classifier.engine import ACMGClassifier
    from varidex.core.classifier.config import ACMGConfig
    print(f"✓ ACMG classifier")

    print()
    print("✓ All imports successful")
    sys.exit(0)

except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    echo "❌ Import test failed"
    exit 1
fi
echo

# ======================================================================
# STEP 4: Load ClinVar Data
# ======================================================================
echo "======================================================================"
echo "STEP 4: Loading ClinVar Data"
echo "======================================================================"
echo

python3 << 'EOF'
import sys
from varidex.io.loaders.clinvar import load_clinvar

print("Loading ClinVar VCF...")
try:
    clinvar_df = load_clinvar("data/")

    if clinvar_df is None or len(clinvar_df) == 0:
        print("❌ Failed to load ClinVar data")
        sys.exit(1)

    print(f"✓ Loaded {len(clinvar_df):,} ClinVar variants")
    print(f"  Columns: {list(clinvar_df.columns)[:5]}...")

    # Save sample
    sample = clinvar_df.head(100)
    sample.to_csv('test_output/clinvar_sample.csv', index=False)
    print(f"✓ Saved sample: test_output/clinvar_sample.csv")

    # Count rsIDs
    rsid_count = clinvar_df['ID'].notna().sum()
    print(f"  rsIDs: {rsid_count:,} ({rsid_count/len(clinvar_df)*100:.1f}%)")

    sys.exit(0)

except Exception as e:
    print(f"❌ ClinVar loading failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    exit 1
fi
echo

# ======================================================================
# STEP 5: Load User Genome Data
# ======================================================================
echo "======================================================================"
echo "STEP 5: Loading User Genome Data"
echo "======================================================================"
echo

python3 << EOF
import sys
from varidex.io.loaders.user import load_user_genome

print("Loading user genome...")
try:
    user_df = load_user_genome("$USER_GENOME")

    if user_df is None or len(user_df) == 0:
        print("❌ Failed to load user genome")
        sys.exit(1)

    print(f"✓ Loaded {len(user_df):,} user variants")
    print(f"  Columns: {list(user_df.columns)}")

    # Save sample
    sample = user_df.head(100)
    sample.to_csv('test_output/user_sample.csv', index=False)
    print(f"✓ Saved sample: test_output/user_sample.csv")

    # Count variant types
    if 'variant_id_type' in user_df.columns:
        type_counts = user_df['variant_id_type'].value_counts()
        print(f"  Variant types:")
        for vtype, count in type_counts.items():
            print(f"    {vtype}: {count:,}")

    sys.exit(0)

except Exception as e:
    print(f"❌ User genome loading failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    exit 1
fi
echo

# ======================================================================
# STEP 6: Match Variants
# ======================================================================
echo "======================================================================"
echo "STEP 6: Matching Variants (ClinVar ⟷ User)"
echo "======================================================================"
echo

python3 << 'EOF'
import sys
from varidex.io.loaders.clinvar import load_clinvar
from varidex.io.loaders.user import load_user_genome
from varidex.io.matching import match_variants_hybrid

print("Loading data...")
try:
    clinvar_df = load_clinvar("data/")
    user_df = load_user_genome(next(iter([f for f in __import__('pathlib').Path('data').glob('genome_*.txt')])))

    print(f"✓ ClinVar: {len(clinvar_df):,} variants")
    print(f"✓ User: {len(user_df):,} variants")
    print()

    print("Matching variants...")
    matched_df = match_variants_hybrid(clinvar_df, user_df)

    if matched_df is None or len(matched_df) == 0:
        print("❌ No matches found")
        sys.exit(1)

    print(f"✓ Matched {len(matched_df):,} variants")
    print(f"  Match rate: {len(matched_df)/len(user_df)*100:.1f}% of user variants")

    # Save results
    matched_df.to_csv('test_output/matched_variants.csv', index=False)
    print(f"✓ Saved: test_output/matched_variants.csv")

    sys.exit(0)

except Exception as e:
    print(f"❌ Matching failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    exit 1
fi
echo

# ======================================================================
# STEP 7: ACMG Classification
# ======================================================================
echo "======================================================================"
echo "STEP 7: ACMG Classification (Interesting Variants)"
echo "======================================================================"
echo

python3 test_classification_interesting.py

if [ $? -ne 0 ]; then
    echo "❌ Classification failed"
    exit 1
fi
echo

# ======================================================================
# STEP 8: Generate Summary Report
# ======================================================================
echo "======================================================================"
echo "STEP 8: Summary Report"
echo "======================================================================"
echo

python3 << 'EOF'
import pandas as pd

# Load results
matched_df = pd.read_csv('test_output/matched_variants.csv')
classified_df = pd.read_csv('test_output/classified_interesting.csv')

print("="*70)
print("VARIDEX PIPELINE - FINAL SUMMARY")
print("="*70)
print()

print("Data Processing:")
print(f"  User genome variants: {matched_df['rsid'].nunique():,}")
print(f"  ClinVar matches: {len(matched_df):,}")
print(f"  Match rate: {len(matched_df)/matched_df['rsid'].nunique()*100:.1f}%")
print()

print("Classification Results (sample):")
print(f"  Variants classified: {len(classified_df)}")
print()

# Evidence summary
print("Evidence Codes Assigned:")
evidence_summary = {
    'PVS': classified_df['pvs'].sum(),
    'PS': classified_df['ps'].sum(),
    'PM': classified_df['pm'].sum(),
    'PP': classified_df['pp'].sum(),
    'BA': classified_df['ba'].sum(),
    'BS': classified_df['bs'].sum(),
    'BP': classified_df['bp'].sum()
}
total_evidence = sum(evidence_summary.values())

print(f"  Pathogenic: PVS={evidence_summary['PVS']} PS={evidence_summary['PS']} PM={evidence_summary['PM']} PP={evidence_summary['PP']}")
print(f"  Benign: BA={evidence_summary['BA']} BS={evidence_summary['BS']} BP={evidence_summary['BP']}")
print(f"  Total: {total_evidence} evidence codes")
print()

# Classification breakdown
print("ACMG Classifications:")
for classification, count in classified_df['acmg_classification'].value_counts().items():
    print(f"  {classification}: {count}")
print()

print("Performance:")
avg_time = classified_df['duration_ms'].mean()
print(f"  Average: {avg_time:.2f}ms per variant")
print(f"  Throughput: ~{1000/avg_time:.0f} variants/second")
print()

print("Output Files:")
print("  ✓ test_output/clinvar_sample.csv")
print("  ✓ test_output/user_sample.csv")
print("  ✓ test_output/matched_variants.csv")
print("  ✓ test_output/classified_interesting.csv")
print()

print("="*70)
EOF

echo
echo "======================================================================"
echo "✅ END-TO-END TEST COMPLETE"
echo "======================================================================"
echo
echo "All pipeline stages completed successfully:"
echo "  ✓ ClinVar data loaded"
echo "  ✓ User genome loaded"
echo "  ✓ Variants matched"
echo "  ✓ ACMG classification performed"
echo "  ✓ Evidence codes assigned"
echo
echo "Review results in test_output/"
echo
