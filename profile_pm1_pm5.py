#!/usr/bin/env python3
"""
Performance Profiler for PM1 and PM5 Classifiers
Measures execution time, memory usage, and identifies bottlenecks
"""
import time
import pandas as pd
import cProfile
import pstats
from io import StringIO
import sys
from pathlib import Path

# Add varidex to path
sys.path.insert(0, str(Path(__file__).parent))

from varidex.acmg.criteria_pm1 import PM1Classifier
from varidex.acmg.criteria_pm5 import PM5Classifier
from varidex.io.loaders.clinvar import load_clinvar_file


class PerformanceProfiler:
    """Profile ACMG criteria performance"""

    def __init__(self):
        self.results = {}

    def time_function(self, func, *args, **kwargs):
        """Time a function execution"""
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        return result, elapsed

    def profile_pm1(self, df, uniprot_path="uniprot/uniprot_sprot.xml.gz"):
        """Profile PM1 classifier"""
        print("="*70)
        print("PM1 PERFORMANCE PROFILE")
        print("="*70)

        # Profile initialization (domain loading)
        print("\n1. PM1 Initialization (Domain Loading)...")
        pm1, init_time = self.time_function(PM1Classifier, uniprot_path)
        print(f"   ⏱️  Initialization: {init_time:.3f}s")
        self.results['pm1_init'] = init_time

        # Profile application
        print("\n2. PM1 Application (Variant Classification)...")
        result_df, apply_time = self.time_function(pm1.apply_pm1, df.copy())
        print(f"   ⏱️  Application: {apply_time:.3f}s")
        print(f"   📊 Variants processed: {len(df):,}")
        print(f"   📊 Throughput: {len(df)/apply_time:.0f} variants/sec")

        self.results['pm1_apply'] = apply_time
        self.results['pm1_throughput'] = len(df)/apply_time

        return result_df

    def profile_pm5(self, df, clinvar_df):
        """Profile PM5 classifier"""
        print("\n" + "="*70)
        print("PM5 PERFORMANCE PROFILE")
        print("="*70)

        # Profile initialization (index building)
        print("\n1. PM5 Initialization (Index Building)...")
        pm5, init_time = self.time_function(PM5Classifier, clinvar_df)
        print(f"   ⏱️  Initialization: {init_time:.3f}s")
        print(f"   📊 Pathogenic positions indexed: {len(pm5.pathogenic_positions):,}")
        self.results['pm5_init'] = init_time

        # Profile application
        print("\n2. PM5 Application (Position Matching)...")
        result_df, apply_time = self.time_function(pm5.apply_pm5, df.copy())
        print(f"   ⏱️  Application: {apply_time:.3f}s")
        print(f"   📊 Variants processed: {len(df):,}")
        print(f"   📊 Throughput: {len(df)/apply_time:.0f} variants/sec")

        self.results['pm5_apply'] = apply_time
        self.results['pm5_throughput'] = len(df)/apply_time

        return result_df

    def detailed_profile(self, func, *args):
        """Detailed cProfile analysis"""
        profiler = cProfile.Profile()
        profiler.enable()
        result = func(*args)
        profiler.disable()

        # Print stats
        s = StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
        ps.print_stats(20)  # Top 20 functions
        return result, s.getvalue()

    def print_summary(self):
        """Print performance summary"""
        print("\n" + "="*70)
        print("PERFORMANCE SUMMARY")
        print("="*70)

        total_pm1 = self.results.get('pm1_init', 0) + self.results.get('pm1_apply', 0)
        total_pm5 = self.results.get('pm5_init', 0) + self.results.get('pm5_apply', 0)

        print(f"\n🔬 PM1 Total Time: {total_pm1:.3f}s")
        print(f"   - Init: {self.results.get('pm1_init', 0):.3f}s")
        print(f"   - Apply: {self.results.get('pm1_apply', 0):.3f}s")
        print(f"   - Throughput: {self.results.get('pm1_throughput', 0):.0f} var/s")

        print(f"\n🔬 PM5 Total Time: {total_pm5:.3f}s")
        print(f"   - Init: {self.results.get('pm5_init', 0):.3f}s")
        print(f"   - Apply: {self.results.get('pm5_apply', 0):.3f}s")
        print(f"   - Throughput: {self.results.get('pm5_throughput', 0):.0f} var/s")

        print(f"\n⚡ Total Time: {total_pm1 + total_pm5:.3f}s")


def main():
    """Run performance profiling"""
    print("Loading test data...")

    # Load ClinVar for PM5
    clinvar_df = load_clinvar_file("clinvar/clinvar_GRCh37.vcf.gz")
    print(f"✓ Loaded {len(clinvar_df):,} ClinVar variants")

    # Load results for testing
    df = pd.read_csv("results_michal/results_13codes_FULL.csv")
    print(f"✓ Loaded {len(df):,} test variants\n")

    # Run profiler
    profiler = PerformanceProfiler()

    # Profile PM1
    df = profiler.profile_pm1(df)

    # Profile PM5
    df = profiler.profile_pm5(df, clinvar_df)

    # Summary
    profiler.print_summary()

    # Detailed profiling
    print("\n" + "="*70)
    print("DETAILED PROFILING (Top 20 functions)")
    print("="*70)

    print("\nPM1 Detailed Profile:")
    pm1 = PM1Classifier("uniprot/uniprot_sprot.xml.gz")
    _, stats = profiler.detailed_profile(pm1.apply_pm1, df.copy())
    print(stats[:1000])  # First 1000 chars


if __name__ == "__main__":
    main()
