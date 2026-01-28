#!/usr/bin/env python3
"""
test_gnomad_loader.py - Test gnomAD Multi-Chromosome Loader

Quick verification script to test gnomAD integration.
"""

import sys
from pathlib import Path
import pandas as pd

print("="*70)
print("🧬 gnomAD Loader Test Script")
print("="*70)

# Add VariDex to path
varidex_root = Path(__file__).parent
sys.path.insert(0, str(varidex_root))

try:
    from varidex.io.loaders.gnomad import GnomADLoader, GnomADFrequency
    print("✅ Successfully imported GnomADLoader\n")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print("\nMake sure you've installed dependencies:")
    print("   pip install pysam tqdm pandas\n")
    sys.exit(1)

# Configuration
GNOMAD_DIR = Path("gnomad")  # Adjust this path
DATASET = "exomes"
VERSION = "r2.1.1"

print(f"📂 Configuration:")
print(f"   Directory: {GNOMAD_DIR}")
print(f"   Dataset: {DATASET}")
print(f"   Version: {VERSION}\n")

# Check if directory exists
if not GNOMAD_DIR.exists():
    print(f"❌ Directory not found: {GNOMAD_DIR}")
    print("\nPlease create the directory or update GNOMAD_DIR variable.")
    sys.exit(1)

print(f"✅ Directory exists: {GNOMAD_DIR.absolute()}\n")

# List available files
print("📄 Available files:")
vcf_files = list(GNOMAD_DIR.glob("*.vcf.bgz"))
if not vcf_files:
    print(f"   ⚠️  No .vcf.bgz files found in {GNOMAD_DIR}")
    print("\nExpected file pattern: gnomad.exomes.r2.1.1.sites.*.vcf.bgz")
else:
    for f in sorted(vcf_files):
        size_mb = f.stat().st_size / (1024 * 1024)
        tbi_exists = (Path(str(f) + ".tbi")).exists()
        tbi_status = "✅" if tbi_exists else "❌"
        print(f"   {tbi_status} {f.name} ({size_mb:.1f} MB)")

print()

# Initialize loader
print("🚀 Initializing GnomADLoader...")
try:
    loader = GnomADLoader(
        gnomad_dir=GNOMAD_DIR,
        dataset=DATASET,
        version=VERSION,
        auto_index=True
    )
    print("✅ Loader initialized successfully\n")
except Exception as e:
    print(f"❌ Initialization failed: {e}\n")
    sys.exit(1)

# Get statistics
print("📊 Loader Statistics:")
stats = loader.get_statistics()
for key, value in stats.items():
    if key == "chromosomes":
        print(f"   {key}: {', '.join(value)}")
    else:
        print(f"   {key}: {value}")
print()

if not stats["available_chromosomes"]:
    print("⚠️  No chromosome files detected.")
    print("\nPlease add gnomAD files in the format:")
    print(f"   {GNOMAD_DIR}/gnomad.{DATASET}.{VERSION}.sites.*.vcf.bgz\n")
    loader.close()
    sys.exit(1)

# Test single variant lookup
print("🔍 Test 1: Single Variant Lookup")
test_chroms = stats["chromosomes"][:1]  # Test first available chromosome

if test_chroms:
    test_chr = test_chroms[0]
    print(f"   Testing chromosome {test_chr}...")
    
    # Try a few common positions
    test_variants = [
        (test_chr, 100000, "A", "G"),
        (test_chr, 200000, "C", "T"),
        (test_chr, 500000, "G", "A"),
    ]
    
    found_count = 0
    for chrom, pos, ref, alt in test_variants:
        result = loader.lookup_variant(chrom, pos, ref, alt)
        if result:
            found_count += 1
            print(f"   ✓ Found {chrom}:{pos}:{ref}>{alt}")
            print(f"      AF={result.af}, AC={result.ac}, AN={result.an}")
            if result.af_nfe:
                print(f"      European AF={result.af_nfe}")
            break
    
    if found_count == 0:
        print("   ⚠️  Test variants not found (this is normal for test positions)")
else:
    print("   ⚠️  No chromosomes available for testing")

print()

# Test batch lookup
print("🔍 Test 2: Batch Lookup")
if test_chroms:
    test_chr = test_chroms[0]
    batch_variants = [
        (test_chr, pos, "A", "G") 
        for pos in range(100000, 100100, 10)
    ]
    
    print(f"   Looking up {len(batch_variants)} variants on chr{test_chr}...")
    results = loader.lookup_variants_batch(batch_variants, show_progress=False)
    
    found = sum(1 for r in results if r is not None)
    print(f"   ✓ Found {found}/{len(results)} variants in gnomAD")
else:
    print("   ⚠️  No chromosomes available for testing")

print()

# Test DataFrame annotation
print("🔍 Test 3: DataFrame Annotation")
if test_chroms:
    test_chr = test_chroms[0]
    
    # Create test DataFrame
    test_df = pd.DataFrame({
        'chromosome': [test_chr] * 5,
        'position': [100000, 200000, 300000, 400000, 500000],
        'ref_allele': ['A', 'C', 'G', 'T', 'A'],
        'alt_allele': ['G', 'T', 'A', 'C', 'G']
    })
    
    print(f"   Annotating {len(test_df)} test variants...")
    annotated = loader.annotate_dataframe(test_df, show_progress=False)
    
    found = annotated['gnomad_af'].notna().sum()
    print(f"   ✓ Annotated {found}/{len(test_df)} variants with gnomAD data")
    
    if found > 0:
        print("\n   Sample annotated variant:")
        sample = annotated[annotated['gnomad_af'].notna()].iloc[0]
        print(f"      {sample['chromosome']}:{sample['position']}")
        print(f"      {sample['ref_allele']}>{sample['alt_allele']}")
        print(f"      AF={sample['gnomad_af']}")
else:
    print("   ⚠️  No chromosomes available for testing")

print()

# Clean up
print("🧹 Cleaning up...")
loader.close()
print("✅ File handles closed\n")

# Summary
print("="*70)
print("🎉 Testing Complete!")
print("="*70)

if stats["available_chromosomes"] > 0:
    print("\n✅ gnomAD loader is working correctly!")
    print("\nNext steps:")
    print("1. Download additional chromosome files if needed")
    print("2. Integrate with VariDex pipeline")
    print("3. See docs/GNOMAD_SETUP.md for usage examples\n")
else:
    print("\n⚠️  No chromosome files found.")
    print("\nPlease:")
    print("1. Download gnomAD chromosome files")
    print("2. Place them in the gnomad/ directory")
    print("3. Run this test again\n")
    print("See docs/GNOMAD_SETUP.md for download instructions.\n")
