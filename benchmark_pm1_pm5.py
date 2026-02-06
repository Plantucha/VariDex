#!/usr/bin/env python3
"""
Benchmark: Original vs Optimized PM1/PM5
Compares performance and validates correctness
"""
import time
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Import both versions
from varidex.acmg.criteria_pm1 import PM1Classifier as PM1Original
from varidex.acmg.criteria_pm5 import PM5Classifier as PM5Original
from criteria_pm1_optimized import PM1ClassifierOptimized
from criteria_pm5_optimized import PM5ClassifierOptimized, PM5ClassifierUltraFast
from varidex.io.loaders.clinvar import load_clinvar_file


def benchmark_pm1(df, uniprot_path="uniprot/uniprot_sprot.xml.gz"):
    """Benchmark PM1 original vs optimized"""
    print("="*70)
    print("PM1 BENCHMARK")
    print("="*70)

    # Original
    print("\n🔵 ORIGINAL PM1:")
    start = time.time()
    pm1_orig = PM1Original(uniprot_path)
    init_orig = time.time() - start

    start = time.time()
    df_orig = pm1_orig.apply_pm1(df.copy())
    apply_orig = time.time() - start

    total_orig = init_orig + apply_orig
    count_orig = int(df_orig["PM1"].sum())

    print(f"   Time Init: {init_orig:.3f}s")
    print(f"   Time Apply: {apply_orig:.3f}s")
    print(f"   Time Total: {total_orig:.3f}s")
    print(f"   Hits: {count_orig}")

    # Optimized
    print("\n🟢 OPTIMIZED PM1:")
    start = time.time()
    pm1_opt = PM1ClassifierOptimized(uniprot_path)
    init_opt = time.time() - start

    start = time.time()
    df_opt = pm1_opt.apply_pm1(df.copy())
    apply_opt = time.time() - start

    total_opt = init_opt + apply_opt
    count_opt = int(df_opt["PM1"].sum())

    print(f"   Time Init: {init_opt:.3f}s")
    print(f"   Time Apply: {apply_opt:.3f}s")
    print(f"   Time Total: {total_opt:.3f}s")
    print(f"   Hits: {count_opt}")

    # Compare
    speedup = total_orig / total_opt if total_opt > 0 else 0
    print(f"\nSPEEDUP: {speedup:.2f}x faster")
    print(f"   Apply speedup: {apply_orig/apply_opt:.2f}x")

    # Validate correctness
    if count_orig == count_opt:
        print("   Results match!")
    else:
        print(f"   WARNING: Results differ: {count_orig} vs {count_opt}")

    return {
        'original': total_orig,
        'optimized': total_opt,
        'speedup': speedup,
        'count_orig': count_orig,
        'count_opt': count_opt
    }


def benchmark_pm5(df, clinvar_df):
    """Benchmark PM5 original vs optimized vs ultra-fast"""
    print("\n" + "="*70)
    print("PM5 BENCHMARK")
    print("="*70)

    # Original
    print("\n🔵 ORIGINAL PM5:")
    start = time.time()
    pm5_orig = PM5Original(clinvar_df)
    init_orig = time.time() - start

    start = time.time()
    df_orig = pm5_orig.apply_pm5(df.copy())
    apply_orig = time.time() - start

    total_orig = init_orig + apply_orig
    count_orig = int(df_orig["PM5"].sum())

    print(f"   Time Init: {init_orig:.3f}s")
    print(f"   Time Apply: {apply_orig:.3f}s")
    print(f"   Time Total: {total_orig:.3f}s")
    print(f"   Hits: {count_orig}")

    # Optimized
    print("\n🟢 OPTIMIZED PM5:")
    start = time.time()
    pm5_opt = PM5ClassifierOptimized(clinvar_df)
    init_opt = time.time() - start

    start = time.time()
    df_opt = pm5_opt.apply_pm5(df.copy())
    apply_opt = time.time() - start

    total_opt = init_opt + apply_opt
    count_opt = int(df_opt["PM5"].sum())

    print(f"   Time Init: {init_opt:.3f}s")
    print(f"   Time Apply: {apply_opt:.3f}s")
    print(f"   Time Total: {total_opt:.3f}s")
    print(f"   Hits: {count_opt}")

    # Ultra-fast
    print("\n🚀 ULTRA-FAST PM5:")
    start = time.time()
    pm5_ultra = PM5ClassifierUltraFast(clinvar_df)
    init_ultra = time.time() - start

    start = time.time()
    df_ultra = pm5_ultra.apply_pm5(df.copy())
    apply_ultra = time.time() - start

    total_ultra = init_ultra + apply_ultra
    count_ultra = int(df_ultra["PM5"].sum())

    print(f"   Time Init: {init_ultra:.3f}s")
    print(f"   Time Apply: {apply_ultra:.3f}s")
    print(f"   Time Total: {total_ultra:.3f}s")
    print(f"   Hits: {count_ultra}")

    # Compare
    speedup_opt = total_orig / total_opt if total_opt > 0 else 0
    speedup_ultra = total_orig / total_ultra if total_ultra > 0 else 0

    print(f"\nSPEEDUP:")
    print(f"   Optimized: {speedup_opt:.2f}x faster")
    print(f"   Ultra-fast: {speedup_ultra:.2f}x faster")

    # Validate
    if count_orig == count_opt == count_ultra:
        print("   All results match!")
    else:
        print(f"   WARNING: Results differ: {count_orig} / {count_opt} / {count_ultra}")

    return {
        'original': total_orig,
        'optimized': total_opt,
        'ultra': total_ultra,
        'speedup_opt': speedup_opt,
        'speedup_ultra': speedup_ultra
    }


def main():
    """Run benchmarks"""
    print("Loading data...")

    # Load ClinVar
    clinvar_df = load_clinvar_file("clinvar/clinvar_GRCh37.vcf.gz")
    print(f"Loaded {len(clinvar_df):,} ClinVar variants")

    # Load test data
    df = pd.read_csv("results_michal/results_13codes_FULL.csv")
    print(f"Loaded {len(df):,} test variants\n")

    # Benchmark PM1
    pm1_results = benchmark_pm1(df)

    # Benchmark PM5
    pm5_results = benchmark_pm5(df, clinvar_df)

    # Final summary
    print("\n" + "="*70)
    print("FINAL SUMMARY")
    print("="*70)
    print(f"\nPM1: {pm1_results['speedup']:.2f}x speedup")
    print(f"   Original: {pm1_results['original']:.3f}s")
    print(f"   Optimized: {pm1_results['optimized']:.3f}s")

    print(f"\nPM5: {pm5_results['speedup_ultra']:.2f}x speedup (ultra-fast)")
    print(f"   Original: {pm5_results['original']:.3f}s")
    print(f"   Ultra-fast: {pm5_results['ultra']:.3f}s")

    total_orig = pm1_results['original'] + pm5_results['original']
    total_opt = pm1_results['optimized'] + pm5_results['ultra']
    total_speedup = total_orig / total_opt if total_opt > 0 else 0

    print(f"\nCOMBINED SPEEDUP: {total_speedup:.2f}x")
    print(f"   Original total: {total_orig:.3f}s")
    print(f"   Optimized total: {total_opt:.3f}s")
    print(f"   Time saved: {total_orig - total_opt:.3f}s")


if __name__ == "__main__":
    main()
