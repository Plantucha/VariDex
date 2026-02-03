#!/usr/bin/env python3
"""
Annotate with gnomAD - AUTO-OPTIMIZED for any system
Automatically detects CPU cores, RAM, and optimizes accordingly
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Patch tqdm
import tqdm.std as tqdm_std
original_tqdm_init = tqdm_std.tqdm.__init__
def patched_tqdm_init(self, *args, **kwargs):
    original_tqdm_init(self, *args, **kwargs)
tqdm_std.tqdm.__init__ = patched_tqdm_init

import pandas as pd
import multiprocessing as mp
import psutil
import time

pd.options.mode.copy_on_write = True

from varidex.io.loaders.clinvar import load_clinvar_file
from varidex.io.loaders.user import load_user_file
from varidex.io import matching
from varidex.pipeline.gnomad_annotator_parallel import (
    annotate_with_gnomad,
    apply_frequency_acmg_criteria,
)


def detect_optimal_config():
    """
    Auto-detect optimal configuration for current system.
    
    Returns:
        tuple: (n_workers, batch_size)
    """
    # Detect CPU cores
    cpu_count = mp.cpu_count()
    
    # Detect available RAM (in GB)
    try:
        ram_gb = psutil.virtual_memory().available / (1024**3)
    except:
        ram_gb = 8  # Conservative default
    
    # Calculate optimal workers
    # Leave at least 1-2 cores for system/I/O
    if cpu_count <= 2:
        n_workers = 1
    elif cpu_count <= 4:
        n_workers = cpu_count - 1
    elif cpu_count <= 8:
        n_workers = cpu_count - 2
    else:
        # High-end systems: leave 2 cores, but cap at 20 workers
        n_workers = min(cpu_count - 2, 20)
    
    # Calculate optimal batch size based on RAM
    # Rule of thumb: ~100 variants per GB of RAM, capped at 2000
    if ram_gb < 4:
        batch_size = 100
    elif ram_gb < 8:
        batch_size = 250
    elif ram_gb < 16:
        batch_size = 500
    elif ram_gb < 32:
        batch_size = 1000
    else:
        batch_size = 2000
    
    return n_workers, batch_size


def print_system_info(n_workers, batch_size):
    """Print detected system configuration."""
    cpu_count = mp.cpu_count()
    
    try:
        ram = psutil.virtual_memory()
        ram_total_gb = ram.total / (1024**3)
        ram_avail_gb = ram.available / (1024**3)
        ram_info = f"{ram_avail_gb:.1f} GB available / {ram_total_gb:.1f} GB total"
    except:
        ram_info = "Unknown"
    
    try:
        cpu_freq = psutil.cpu_freq()
        freq_info = f"{cpu_freq.current/1000:.2f} GHz"
    except:
        freq_info = "Unknown"
    
    print("=" * 80)
    print("📥 GNOMAD ANNOTATION - AUTO-OPTIMIZED FOR YOUR SYSTEM")
    print("=" * 80)
    print(f"\n💻 System Detected:")
    print(f"   CPU Cores:    {cpu_count} threads")
    print(f"   CPU Freq:     {freq_info}")
    print(f"   RAM:          {ram_info}")
    print(f"\n⚡ Optimization:")
    print(f"   Workers:      {n_workers} (parallel threads)")
    print(f"   Batch Size:   {batch_size} variants/batch")
    print(f"   Reserved:     {cpu_count - n_workers} threads for system/I/O")
    
    # Estimate speedup
    speedup = min(n_workers, cpu_count * 0.8)  # ~80% efficiency
    print(f"\n🚀 Expected Speedup: ~{speedup:.0f}x vs single-threaded")
    print("=" * 80)


# Main pipeline
if __name__ == "__main__":
    # Auto-detect optimal configuration
    n_workers, batch_size = detect_optimal_config()
    print_system_info(n_workers, batch_size)
    
    print("\nLoading ClinVar...")
    clinvar = load_clinvar_file("clinvar/clinvar_GRCh37.vcf")
    print(f"✓ {len(clinvar):,} variants")
    
    print("\nLoading user genome...")
    user = load_user_file("data/raw.txt")
    print(f"✓ {len(user):,} variants")
    
    print("\nMatching...")
    matched = matching.match_variants_hybrid(clinvar, user, "vcf", "23andme")[0]
    print(f"✓ {len(matched):,} matched")
    
    print(f"\n⚡ Annotating {len(matched):,} variants with gnomAD...")
    print(f"   Using {n_workers} parallel workers with batch size {batch_size}")
    start_time = time.time()
    
    matched_annotated = annotate_with_gnomad(
        matched, 
        Path("gnomad"),
        n_workers=n_workers,
        batch_size=batch_size
    )
    
    elapsed = time.time() - start_time
    rate = len(matched) / elapsed if elapsed > 0 else 0
    
    print(f"\n⏱️  Annotation completed in {elapsed:.1f}s")
    print(f"   Speed: {rate:.1f} variants/second")
    
    print("\nApplying frequency criteria...")
    result = apply_frequency_acmg_criteria(matched_annotated)
    
    result["clinvar_class"] = result["clinical_sig"].str.replace("_", " ", regex=False)
    
    output = Path("output/michal_gnomad_annotated.csv")
    output.parent.mkdir(exist_ok=True)
    result.to_csv(output, index=False)
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    total = len(result)
    with_af = result["gnomad_af"].notna().sum()
    ba1 = result["BA1"].sum()
    bs1 = result["BS1"].sum()
    pm2 = result["PM2"].sum()
    
    print(f"\nTotal variants:   {total:,}")
    print(f"With gnomAD data: {with_af:,} ({with_af/total*100:.1f}%)")
    print(f"\nEvidence Codes:")
    print(f"  🟢 BA1 (>5%):   {ba1:,}")
    print(f"  🟢 BS1 (>1%):   {bs1:,}")
    print(f"  🔴 PM2 (<0.01%): {pm2:,}")
    
    print(f"\n⏱️  Performance:")
    print(f"  Time:  {elapsed:.1f}s")
    print(f"  Speed: {rate:.1f} variants/sec")
    print(f"  Config: {n_workers} workers, batch {batch_size}")
    
    print(f"\n✅ Results saved to: {output}")
    print("=" * 80)
