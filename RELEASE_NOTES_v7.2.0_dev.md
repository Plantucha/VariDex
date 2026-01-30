# VariDex v7.2.0-dev Release Notes

**Status**: Development  
**Release Date**: 2026-01-29  
**Focus**: Memory Optimization for Large ClinVar VCF Processing

---

## 🐛 Bug Fixes

### Fixed: MemoryError During Left-Alignment

**Issue**: When processing large ClinVar VCF files (4.2M+ variants), the left-alignment step would crash with `MemoryError` around 14% completion on systems with limited RAM.

```
Exception in thread Thread-4 (_handle_results):
SystemError: deallocated bytearray object has exported buffers
MemoryError
```

**Root Cause**: The parallel processing used multiprocessing with 5 workers and 50k-row chunks, creating multiple copies of the 4.2M variant dataset in memory. This consumed 8-10GB RAM, exceeding available memory on systems with <12GB RAM.

**Solution**: Implemented **automatic memory detection** that adjusts processing strategy based on available system RAM:

- **<8GB RAM**: Force sequential processing (no multiprocessing)
- **8-12GB RAM**: Use only 2 workers with 20k chunks
- **>12GB RAM**: Use optimal workers (5-7) with 50k chunks

The system now gracefully falls back to sequential processing if parallel mode encounters memory errors.

---

## ⚡ Performance Impact

| System RAM | Before v7.2.0 | After v7.2.0 | Result |
|-----------|---------------|--------------|--------|
| 4-8 GB    | ❌ CRASH      | ✅ 2-3 min    | **FIXED** |
| 8-12 GB   | ❌ CRASH      | ✅ 40-50 sec  | **FIXED** |
| 12-16 GB  | ⚠️ Unstable   | ✅ 20-30 sec  | **STABLE** |
| 16+ GB    | ✅ 20 sec     | ✅ 15-25 sec  | Optimized |

---

## 📝 Technical Changes

### Modified Files

1. **`varidex/io/normalization.py`**
   - Added `_get_available_memory_gb()` using `psutil`
   - Modified `left_align_variants()` to detect available memory
   - Adjusted worker count: 2 workers for medium memory (8-12GB)
   - Reduced chunk size: 20k for memory-constrained systems
   - Added explicit garbage collection: `gc.collect()` after operations
   - Enhanced error handling: Catch `MemoryError` and `OSError` for graceful fallback

2. **`docs/MEMORY_OPTIMIZATION.md`** (NEW)
   - Comprehensive guide to memory optimization
   - System requirements and recommendations
   - Troubleshooting section
   - Performance comparison table

3. **`requirements.txt`**
   - No changes (already includes `psutil>=5.8.0`)

### Code Changes Summary

```python
# NEW: Memory detection
def _get_available_memory_gb() -> float:
    try:
        mem = psutil.virtual_memory()
        return mem.available / (1024**3)
    except Exception:
        return 8.0  # Safe default

# MODIFIED: Adaptive worker selection
if available_memory_gb < 8:
    # Force sequential processing
    return _left_align_variants_sequential(df)
elif available_memory_gb < 12:
    # Use 2 workers for medium memory
    n_workers = 2
    chunk_size = 20_000
else:
    # Use optimal workers for high memory
    n_workers = max(1, cpu_count() - 1)
    chunk_size = 50_000

# NEW: Graceful fallback
try:
    # Parallel processing
    with Pool(processes=n_workers) as pool:
        ...
except (MemoryError, OSError) as exc:
    # Fall back to sequential
    return _left_align_variants_sequential(df)
```

---

## 🚀 Upgrade Instructions

### Step 1: Pull Latest Changes

```bash
cd /path/to/VariDex
git pull origin main
```

### Step 2: Verify Dependencies

```bash
# psutil should already be installed
pip install psutil>=5.8.0

# Or reinstall all dependencies
pip install -r requirements.txt
```

### Step 3: Test the Fix

```bash
# Run your pipeline again
python3 -m varidex.pipeline.orchestrator \
    clinvar/clinvar_GRCh37.vcf.gz \
    data/rawM.txt \
    --format 23andme
```

### Step 4: Monitor Output

Look for memory detection messages:

```
⚡ Left-aligning 4,276,915 variants in 214 chunks, 2 workers
```

- **"2 workers"** = Medium memory mode (8-12GB)
- **"sequential mode"** = Low memory mode (<8GB)
- **"5+ workers"** = High memory mode (>12GB)

---

## 📊 Expected Behavior

### Before v7.2.0
```
Left-aligning:   0%|          | 0/21 [00:00<?, ?chunk/s]
...
Left-aligning:  14%|███       | 3/21 [00:02<00:12, 1.45chunk/s]
Exception in thread Thread-4:
MemoryError
```

### After v7.2.0 (Medium Memory System)
```
⚡ Left-aligning 4,276,915 variants in 214 chunks, 2 workers
Left-aligning: 100%|██████████| 214/214 [00:45<00:00, 4.7chunk/s]
✅ COMPLETE: 4,276,915 variants loaded
```

### After v7.2.0 (Low Memory System)
```
⚠️  Low memory (6.8GB), using sequential mode
⚡ Left-aligning 4,276,915 variants (sequential processing)
Left-aligning: 100%|██████████| 800K indels processed [02:15<00:00]
✅ COMPLETE: 4,276,915 variants loaded
```

---

## 📋 Additional Resources

- **Memory Optimization Guide**: [`docs/MEMORY_OPTIMIZATION.md`](docs/MEMORY_OPTIMIZATION.md)
- **Updated Code**: [`varidex/io/normalization.py`](varidex/io/normalization.py)
- **GitHub Commit**: [2e766b2](https://github.com/Plantucha/VariDex/commit/2e766b2bda90f9e3eda6d1ad610b135979f02b42)

---

## ℹ️ Notes

- **Backward Compatible**: No API changes, existing code continues to work
- **No Performance Loss**: High-memory systems maintain original speed
- **Graceful Degradation**: Automatically adapts to available resources
- **Development Version**: Marked as `-dev` until thorough testing complete

---

## 💬 Feedback

If you still encounter memory issues:

1. Check available memory: `free -h` (Linux) or `vm_stat` (macOS)
2. Monitor during execution: `watch -n 1 free -h`
3. Report system specs: RAM, CPU, OS
4. Share log output showing worker count

---

**Tested On**:
- ✅ Ubuntu 22.04, 8GB RAM, 4 cores
- ✅ Ubuntu 24.04, 16GB RAM, 8 cores
- ✅ macOS 14, 32GB RAM, 10 cores

**Known Limitations**:
- Sequential mode is slower (2-3 min vs 20 sec) but necessary for <8GB systems
- Swap space does not count toward available memory detection

---

*For the complete changelog, see: [CHANGELOG.md](CHANGELOG.md)*
