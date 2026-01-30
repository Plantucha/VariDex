# Memory Optimization Guide - VariDex v7.2.0-dev

## Overview

VariDex v7.2.0 introduces **automatic memory-aware processing** for the left-alignment step when loading large ClinVar VCF files. The system now detects available RAM and automatically adjusts processing strategy to prevent `MemoryError` crashes.

## What Changed

The left-alignment normalization process now includes:

1. **Memory Detection**: Automatically checks available system memory before processing
2. **Adaptive Strategy**: Adjusts worker count and chunk sizes based on available RAM
3. **Graceful Fallback**: Falls back to sequential processing if memory errors occur
4. **Explicit Cleanup**: Forces garbage collection to free memory between operations

## Processing Modes

### High Memory Mode (>12GB available)
- **Workers**: CPU count - 1 (typically 5-7 workers)
- **Chunk Size**: 50,000 variants per chunk
- **Performance**: ~20-30 seconds for 4.3M variants
- **Recommended For**: Systems with 16GB+ RAM

### Medium Memory Mode (8-12GB available)
- **Workers**: 2 workers only
- **Chunk Size**: 20,000 variants per chunk
- **Performance**: ~40-50 seconds for 4.3M variants
- **Recommended For**: Systems with 8-12GB RAM

### Low Memory Mode (<8GB available)
- **Workers**: Sequential processing (no multiprocessing)
- **Chunk Size**: N/A (processes entire dataset)
- **Performance**: ~2-3 minutes for 4.3M variants
- **Recommended For**: Systems with <8GB RAM or memory-constrained environments

## System Requirements

### Minimum
- **RAM**: 4GB (sequential mode)
- **CPU**: Single core
- **Disk**: 2GB free space for caching

### Recommended
- **RAM**: 12GB+ (parallel mode)
- **CPU**: 4+ cores
- **Disk**: 5GB free space for caching

### Optimal
- **RAM**: 16GB+
- **CPU**: 8+ cores
- **Disk**: SSD with 10GB+ free space

## Performance Comparison

| System RAM | Processing Mode | Workers | Time (4.3M variants) |
|-----------|----------------|---------|---------------------|
| 4-8 GB    | Sequential     | 1       | 2-3 minutes         |
| 8-12 GB   | Limited Parallel| 2       | 40-50 seconds       |
| 12-16 GB  | Parallel       | 5       | 20-30 seconds       |
| 16+ GB    | Parallel       | 7+      | 15-25 seconds       |

## Troubleshooting

### Still Getting MemoryError?

If you still encounter memory errors after the v7.2.0 update:

1. **Close Other Applications**: Free up system RAM before running VariDex
   ```bash
   # Check current memory usage
   free -h  # Linux
   vm_stat  # macOS
   ```

2. **Force Sequential Mode**: Set environment variable to bypass parallel processing
   ```bash
   # Force sequential processing regardless of available memory
   export VARIDEX_FORCE_SEQUENTIAL=1
   python3 -m varidex.pipeline.orchestrator ...
   ```

3. **Increase Swap Space**: Add swap memory for systems with <8GB RAM
   ```bash
   # Linux: Check current swap
   swapon --show
   
   # Add 8GB swap file (if needed)
   sudo fallocate -l 8G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

4. **Use Cloud Instance**: For large datasets, consider cloud instances
   - AWS: t3.xlarge (16GB RAM, $0.17/hour)
   - Google Cloud: n1-standard-4 (15GB RAM, $0.19/hour)
   - Azure: Standard_D4s_v3 (16GB RAM, $0.19/hour)

### Monitoring Memory Usage

```bash
# Monitor memory during VariDex execution
watch -n 1 free -h

# Or use htop for detailed view
htop
```

### Log Output

VariDex now logs memory detection information:

```
⚡ Left-aligning 4,276,915 variants in 214 chunks, 2 workers
```
- If you see **"2 workers"**: Medium memory mode (8-12GB)
- If you see **"sequential mode"**: Low memory mode (<8GB)
- If you see **"5+ workers"**: High memory mode (>12GB)

## Technical Details

### Memory Detection

```python
import psutil

mem = psutil.virtual_memory()
available_gb = mem.available / (1024**3)
```

### Processing Strategy

1. **Check Available RAM**
   - Uses `psutil.virtual_memory()` to detect available (not total) RAM
   - Available RAM = Total RAM - Used RAM (by OS and other processes)

2. **Select Mode**
   - `< 8GB`: Force sequential
   - `8-12GB`: 2 workers, 20k chunks
   - `> 12GB`: Optimal workers, 50k chunks

3. **Graceful Degradation**
   - If parallel mode fails with `MemoryError` or `OSError`
   - Automatically falls back to sequential mode
   - Logs warning message

### Why Memory Optimization Matters

Multiprocessing creates data copies in each worker process:

```
Original Data (4.2M variants): ~1.5GB RAM
With 5 Workers: ~1.5GB × 5 = 7.5GB RAM
Plus OS overhead: ~8-9GB total RAM needed
```

By reducing to 2 workers and smaller chunks:

```
Original Data: ~1.5GB RAM
With 2 Workers: ~1.5GB × 2 = 3GB RAM
Smaller chunks: Less peak memory per worker
Total: ~4-5GB RAM needed
```

## Related Files

- [`varidex/io/normalization.py`](../varidex/io/normalization.py) - Memory-aware left-alignment implementation
- [`requirements.txt`](../requirements.txt) - Dependencies (includes `psutil>=5.8.0`)

## Version History

### v7.2.0-dev (Current)
- ✅ Auto-detect available memory
- ✅ Adaptive worker/chunk sizing
- ✅ Graceful fallback to sequential
- ✅ Explicit garbage collection

### v7.1.0 (Previous)
- ⚡ Skip SNV alignment (80% speedup)
- ⚡ Vectorized operations
- ⚡ Parallel processing (fixed workers)

### v7.0.0
- 🆕 Initial left-alignment implementation

## Feedback

If you encounter memory issues not resolved by v7.2.0:

1. Check available memory: `free -h` (Linux) or `vm_stat` (macOS)
2. Check log output for worker count
3. Report issue with system specs (RAM, CPU, OS)
4. Include error message and stack trace

---

**Last Updated**: 2026-01-29  
**Version**: 7.2.0-dev  
**Status**: Development
