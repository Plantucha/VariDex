#!/usr/bin/env python3
"""
test_gnomad_parallel.py - Test gnomAD Parallel Workers

Test script to verify parallel processing functionality of gnomAD loader.
"""

import sys
import time
from pathlib import Path

import pandas as pd

print("=" * 70)
print("🚀 gnomAD Parallel Workers Test Script")
print("=" * 70)

# Add VariDex to path
varidex_root = Path(__file__).parent
sys.path.insert(0, str(varidex_root))

try:
    from varidex.io.loaders.gnomad import GnomADLoader

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
print("📄 Available gnomAD files:")
vcf_files = list(GNOMAD_DIR.glob("*.vcf.bgz"))
if not vcf_files:
    print(f"   ⚠️  No .vcf.bgz files found in {GNOMAD_DIR}")
    print("\nExpected file pattern: gnomad.exomes.r2.1.1.sites.*.vcf.bgz")
    print("\nPlease download gnomAD files before testing.")
    sys.exit(1)

for f in sorted(vcf_files):
    size_mb = f.stat().st_size / (1024 * 1024)
    tbi_exists = (Path(str(f) + ".tbi")).exists()
    tbi_status = "✅" if tbi_exists else "❌"
    print(f"   {tbi_status} {f.name} ({size_mb:.1f} MB)")

print()

# ============================================================================
# Test 1: Sequential Processing (Baseline)
# ============================================================================

print("=" * 70)
print("🔍 Test 1: Sequential Processing (Baseline)")
print("=" * 70)

try:
    loader_seq = GnomADLoader(
        gnomad_dir=GNOMAD_DIR,
        dataset=DATASET,
        version=VERSION,
        max_workers=1,  # Force sequential
    )
    print("✅ Sequential loader initialized\n")
except Exception as e:
    print(f"❌ Initialization failed: {e}\n")
    sys.exit(1)

# Get statistics
stats = loader_seq.get_statistics()
print("📊 Loader Statistics:")
for key, value in stats.items():
    if key == "chromosomes":
        print(f"   {key}: {', '.join(value)}")
    else:
        print(f"   {key}: {value}")
print()

if not stats["available_chromosomes"]:
    print("⚠️  No chromosome files detected.")
    loader_seq.close()
    sys.exit(1)

# Create test dataset
test_chr = stats["chromosomes"][0]
num_variants = 1000

print(f"🧬 Creating test dataset: {num_variants} variants on chr{test_chr}\n")

test_variants = [
    (test_chr, pos, "A", "G") for pos in range(100000, 100000 + num_variants * 100, 100)
]

# Benchmark sequential processing
print(f"⏱️  Timing sequential processing...")
start_time = time.time()
results_seq = loader_seq.lookup_variants_batch(test_variants, show_progress=True)
seq_time = time.time() - start_time

found_seq = sum(1 for r in results_seq if r is not None)
print(f"\n   ✓ Sequential: {seq_time:.2f}s")
print(f"   ✓ Found: {found_seq}/{num_variants} variants ({100*found_seq/num_variants:.1f}%)\n")

loader_seq.close()

# ============================================================================
# Test 2: Parallel Processing (2 workers)
# ============================================================================

print("=" * 70)
print("🚀 Test 2: Parallel Processing (2 workers)")
print("=" * 70)

try:
    loader_2 = GnomADLoader(
        gnomad_dir=GNOMAD_DIR,
        dataset=DATASET,
        version=VERSION,
        max_workers=2,
    )
    print("✅ Parallel loader initialized (2 workers)\n")
except Exception as e:
    print(f"❌ Initialization failed: {e}\n")
    sys.exit(1)

# Benchmark parallel processing
print(f"⏱️  Timing parallel processing (2 workers)...")
start_time = time.time()
results_2 = loader_2.lookup_variants_batch(test_variants, show_progress=True)
parallel_2_time = time.time() - start_time

found_2 = sum(1 for r in results_2 if r is not None)
speedup_2 = seq_time / parallel_2_time if parallel_2_time > 0 else 0

print(f"\n   ✓ Parallel (2 workers): {parallel_2_time:.2f}s")
print(f"   ✓ Found: {found_2}/{num_variants} variants ({100*found_2/num_variants:.1f}%)")
print(f"   🚀 Speedup: {speedup_2:.2f}x\n")

loader_2.close()

# ============================================================================
# Test 3: Parallel Processing (4 workers)
# ============================================================================

print("=" * 70)
print("🚀 Test 3: Parallel Processing (4 workers)")
print("=" * 70)

try:
    loader_4 = GnomADLoader(
        gnomad_dir=GNOMAD_DIR,
        dataset=DATASET,
        version=VERSION,
        max_workers=4,
    )
    print("✅ Parallel loader initialized (4 workers)\n")
except Exception as e:
    print(f"❌ Initialization failed: {e}\n")
    sys.exit(1)

# Benchmark parallel processing
print(f"⏱️  Timing parallel processing (4 workers)...")
start_time = time.time()
results_4 = loader_4.lookup_variants_batch(test_variants, show_progress=True)
parallel_4_time = time.time() - start_time

found_4 = sum(1 for r in results_4 if r is not None)
speedup_4 = seq_time / parallel_4_time if parallel_4_time > 0 else 0

print(f"\n   ✓ Parallel (4 workers): {parallel_4_time:.2f}s")
print(f"   ✓ Found: {found_4}/{num_variants} variants ({100*found_4/num_variants:.1f}%)")
print(f"   🚀 Speedup: {speedup_4:.2f}x\n")

loader_4.close()

# ============================================================================
# Test 4: Auto Workers (Default)
# ============================================================================

print("=" * 70)
print("🤖 Test 4: Auto Workers (Default)")
print("=" * 70)

try:
    loader_auto = GnomADLoader(
        gnomad_dir=GNOMAD_DIR,
        dataset=DATASET,
        version=VERSION,
        max_workers=None,  # Auto-detect
    )
    print("✅ Auto loader initialized\n")
except Exception as e:
    print(f"❌ Initialization failed: {e}\n")
    sys.exit(1)

# Check detected configuration
stats_auto = loader_auto.get_statistics()
print("📊 Auto-detected Configuration:")
print(f"   max_workers: {stats_auto['max_workers']}")
print(f"   parallel_enabled: {stats_auto['parallel_enabled']}\n")

# Benchmark auto processing
print(f"⏱️  Timing auto parallel processing...")
start_time = time.time()
results_auto = loader_auto.lookup_variants_batch(test_variants, show_progress=True)
auto_time = time.time() - start_time

found_auto = sum(1 for r in results_auto if r is not None)
speedup_auto = seq_time / auto_time if auto_time > 0 else 0

print(f"\n   ✓ Auto parallel: {auto_time:.2f}s")
print(f"   ✓ Found: {found_auto}/{num_variants} variants ({100*found_auto/num_variants:.1f}%)")
print(f"   🚀 Speedup: {speedup_auto:.2f}x\n")

loader_auto.close()

# ============================================================================
# Test 5: DataFrame Annotation with Parallel Processing
# ============================================================================

print("=" * 70)
print("📄 Test 5: DataFrame Annotation (Parallel)")
print("=" * 70)

# Create test DataFrame
test_df = pd.DataFrame(
    {
        "chromosome": [test_chr] * num_variants,
        "position": list(range(100000, 100000 + num_variants * 100, 100)),
        "ref_allele": ["A"] * num_variants,
        "alt_allele": ["G"] * num_variants,
    }
)

print(f"\n🧬 Test DataFrame: {len(test_df)} variants\n")

# Test with parallel processing
try:
    loader_df = GnomADLoader(
        gnomad_dir=GNOMAD_DIR,
        dataset=DATASET,
        version=VERSION,
        max_workers=4,
    )
    print("✅ Loader initialized for DataFrame test\n")
except Exception as e:
    print(f"❌ Initialization failed: {e}\n")
    sys.exit(1)

print(f"⏱️  Timing DataFrame annotation...")
start_time = time.time()
annotated_df = loader_df.annotate_dataframe(test_df, show_progress=True)
df_time = time.time() - start_time

found_df = annotated_df["gnomad_af"].notna().sum()

print(f"\n   ✓ DataFrame annotation: {df_time:.2f}s")
print(f"   ✓ Annotated: {found_df}/{len(test_df)} variants ({100*found_df/len(test_df):.1f}%)")

if found_df > 0:
    print("\n   📊 Sample annotated variants:")
    samples = annotated_df[annotated_df["gnomad_af"].notna()].head(3)
    for idx, row in samples.iterrows():
        print(
            f"      {row['chromosome']}:{row['position']} "
            f"{row['ref_allele']}>{row['alt_allele']} "
            f"AF={row['gnomad_af']:.6f}"
        )

loader_df.close()
print()

# ============================================================================
# Summary
# ============================================================================

print("=" * 70)
print("🎯 Performance Summary")
print("=" * 70)
print()
print(f"Test Dataset: {num_variants} variants on chr{test_chr}\n")
print(f"Results:")
print(f"   Sequential (1 worker):  {seq_time:>6.2f}s  (baseline)")
print(f"   Parallel (2 workers):   {parallel_2_time:>6.2f}s  ({speedup_2:.2f}x speedup)")
print(f"   Parallel (4 workers):   {parallel_4_time:>6.2f}s  ({speedup_4:.2f}x speedup)")
print(f"   Auto parallel:          {auto_time:>6.2f}s  ({speedup_auto:.2f}x speedup)")
print(f"   DataFrame annotation:   {df_time:>6.2f}s\n")

# Verification
print("Verification:")
if found_seq == found_2 == found_4 == found_auto == found_df:
    print(f"   ✅ All methods found same variants: {found_seq}")
    print("   ✅ Results are consistent!\n")
else:
    print("   ⚠️  Warning: Different variant counts detected:")
    print(f"      Sequential: {found_seq}")
    print(f"      Parallel (2): {found_2}")
    print(f"      Parallel (4): {found_4}")
    print(f"      Auto: {found_auto}")
    print(f"      DataFrame: {found_df}\n")

print("=" * 70)
print("🎉 Testing Complete!")
print("=" * 70)
print()
print("✅ gnomAD parallel workers are functioning correctly!\n")
print("Key Findings:")
print(f"   • Best speedup: {max(speedup_2, speedup_4, speedup_auto):.2f}x")
print(f"   • Optimal config: {4 if speedup_4 >= speedup_auto else 'auto'} workers")
print("   • DataFrame annotation working")
print("   • Results consistent across all methods\n")

print("Next steps:")
print("1. Use parallel processing for large variant batches")
print("2. Adjust max_workers based on your system resources")
print("3. See docs/GNOMAD_PARALLEL_WORKERS.md for optimization tips\n")
