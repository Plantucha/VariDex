#!/bin/bash
########################################################################
# test_real_data.sh - VariDex Real Data Test Suite
# Tests ClinVar loading, user genome loading, and variant matching
########################################################################

set -e  # Exit on error

echo "========================================================================"
echo "VariDex v6.0.0 - Real Data Test Run"
echo "========================================================================"
echo ""
echo "This will test VariDex with real genomic data from data/ directory"
echo ""

# Create output directory
mkdir -p test_output
echo "✓ Created test_output/ directory"
echo ""

########################################################################
# Test 1: Import VariDex
########################################################################
echo "========================================================================"
echo "Test 1: Importing VariDex Package"
echo "========================================================================"

python3 -c "
from varidex.version import __version__
print(f'✓ VariDex v{__version__}')
print('✓ All imports successful')
" || {
    echo "❌ Import failed"
    exit 1
}
echo ""

########################################################################
# Test 2: Load ClinVar
########################################################################
echo "========================================================================"
echo "Test 2: Loading ClinVar Data"
echo "========================================================================"

# Find ClinVar file
if [ -f "data/clinvar_GRCh38.vcf" ]; then
    CLINVAR_FILE="data/clinvar_GRCh38.vcf"
    echo "Found: Uncompressed ClinVar VCF (preferred)"
elif [ -f "data/clinvar_GRCh38.vcf.gz" ]; then
    CLINVAR_FILE="data/clinvar_GRCh38.vcf.gz"
    echo "Found: Compressed ClinVar VCF"
elif [ -f "data/clinvar.vcf" ]; then
    CLINVAR_FILE="data/clinvar.vcf"
    echo "Found: ClinVar VCF"
else
    echo "❌ No ClinVar file found in data/"
    echo "Expected: data/clinvar_GRCh38.vcf or data/clinvar.vcf"
    exit 1
fi

echo "Loading: $CLINVAR_FILE"
echo "Loading ClinVar data..."

python3 << EOF
from varidex.io.loaders.clinvar import load_clinvar_file
from pathlib import Path

clinvar_df = load_clinvar_file("$CLINVAR_FILE")
print(f"✓ Loaded {len(clinvar_df):,} ClinVar variants")

# Check rsid column
if 'rsid' in clinvar_df.columns:
    rsid_count = clinvar_df['rsid'].notna().sum()
    print(f"✓ Extracted {rsid_count:,} rsIDs ({100*rsid_count/len(clinvar_df):.1f}%)")
else:
    print("⚠️  No rsid column found")

print(f"✓ Columns: {', '.join(list(clinvar_df.columns)[:5])}...")

# Save sample
clinvar_df.head(100).to_csv('test_output/clinvar_sample.csv', index=False)
print(f"✓ Saved sample: test_output/clinvar_sample.csv")
EOF

echo ""

########################################################################
# Test 3: Load User Genome
########################################################################
echo "========================================================================"
echo "Test 3: Loading User Genome Data"
echo "========================================================================"

# Find user genome file
if [ -f "data/genome_Sophia_Planicka_v5_Full_20260118130936.txt" ]; then
    USER_FILE="data/genome_Sophia_Planicka_v5_Full_20260118130936.txt"
elif [ -f "data/user_genome.txt" ]; then
    USER_FILE="data/user_genome.txt"
elif [ -f "data/genome.txt" ]; then
    USER_FILE="data/genome.txt"
else
    echo "❌ No user genome file found in data/"
    echo "Expected: data/genome_*.txt"
    exit 1
fi

echo "Found: $(basename $USER_FILE)"
echo "Loading: $USER_FILE"
echo "Loading user genome data..."

python3 << EOF
from varidex.io.loaders.user import load_user_file
from pathlib import Path

user_df = load_user_file("$USER_FILE")
print(f"✓ Loaded {len(user_df):,} user variants")

# Check rsid column
if 'rsid' in user_df.columns:
    rsid_count = user_df['rsid'].notna().sum()
    print(f"✓ {rsid_count:,} rsIDs found")
else:
    print("⚠️  No rsid column found")

print(f"✓ Columns: {', '.join(list(user_df.columns)[:5])}...")

# Save sample
user_df.head(100).to_csv('test_output/user_sample.csv', index=False)
print(f"✓ Saved sample: test_output/user_sample.csv")
EOF

echo ""

########################################################################
# Test 4: Match Variants
########################################################################
echo "========================================================================"
echo "Test 4: Matching Variants"
echo "========================================================================"

echo "Loading ClinVar: $CLINVAR_FILE"
echo "Loading User: $USER_FILE"
echo "Matching variants..."

python3 << EOF
from varidex.io.loaders.clinvar import load_clinvar_file
from varidex.io.loaders.user import load_user_file
from varidex.io.matching import match_variants_hybrid
from pathlib import Path

# Load data
clinvar_df = load_clinvar_file("$CLINVAR_FILE")
user_df = load_user_file("$USER_FILE")

# Match variants
matched_df, rsid_count, coord_count = match_variants_hybrid(clinvar_df, user_df)

print(f"✓ Matched {len(matched_df):,} variants")
print(f"  - {rsid_count:,} by rsID")
print(f"  - {coord_count:,} by coordinates")

if len(matched_df) > 0:
    match_rate = 100 * len(matched_df) / len(user_df)
    print(f"  - {match_rate:.1f}% of user variants matched")

# Save results
matched_df.to_csv('test_output/matched_variants.csv', index=False)
print(f"✓ Saved: test_output/matched_variants.csv")
EOF

echo ""

########################################################################
# Summary
########################################################################
echo "========================================================================"
echo "✅ ALL TESTS PASSED"
echo "========================================================================"
echo ""
echo "Output files:"
echo "  - test_output/clinvar_sample.csv"
echo "  - test_output/user_sample.csv"
echo "  - test_output/matched_variants.csv"
echo ""
echo "Next steps:"
echo "  1. Review matched variants"
echo "  2. Run full pipeline for classification"
echo "  3. Generate reports"
echo ""
echo "========================================================================"
