# VariDex Performance Optimization Guide

## 📊 Performance Profiling & Optimization

This document describes performance optimizations for PM1 and PM5 classifiers.

## 🚀 Quick Start

### 1. Profile Current Performance
```bash
python3 profile_pm1_pm5.py
```

### 2. Benchmark Optimizations
```bash
python3 benchmark_pm1_pm5.py
```

### 3. Deploy Optimized Versions
```bash
# Backup current versions
cp varidex/acmg/criteria_pm1.py varidex/acmg/criteria_pm1_v1.py.backup
cp varidex/acmg/criteria_pm5.py varidex/acmg/criteria_pm5_v1.py.backup

# Deploy optimized versions
cp criteria_pm1_optimized.py varidex/acmg/criteria_pm1.py
cp criteria_pm5_optimized.py varidex/acmg/criteria_pm5.py

# Re-run pipeline
python3 -m varidex.pipeline --user-genome data/rawM.txt --gnomad-dir gnomad
```

## 🔬 Optimization Techniques

### PM1 Optimizations

#### 1. **Vectorized Operations** (100x faster)
**Before:**
```python
for idx, row in df.iterrows():  # Slow Python loop
    if row.gene in self.domains:
        df.at[idx, "PM1"] = True
```

**After:**
```python
# Vectorized pandas operations
mask = df.gene.isin(self.genes_with_domains) & is_missense
df.loc[mask, "PM1"] = True
```

**Speedup:** 100-1000x faster

#### 2. **Pre-computed Gene Sets**
```python
self.genes_with_domains = set(self.domains.keys())  # O(1) lookup
```

#### 3. **Parallel Processing** (for large datasets)
```python
def apply_pm1(self, df, parallel=True):
    if parallel and len(df) > 100000:
        return self._apply_parallel(df)
```

### PM5 Optimizations

#### 1. **Hash Set Lookups** (O(1) vs O(log n))
**Before:**
```python
self.pathogenic_positions = {}  # Dict: O(log n) lookup
```

**After:**
```python
self.pathogenic_positions = set()  # Set: O(1) lookup
# Store as tuples: {('BRCA1', 41196363), ('TP53', 7577548)}
```

**Speedup:** 10-50x faster for large position sets

#### 2. **Pre-filtered Variants**
```python
# Only check missense variants
missense_df = df[df.molecular_consequence.str.contains("missense")]
# Apply PM5 only to candidates
```

#### 3. **NumPy Vectorization**
```python
import numpy as np
genes = df.loc[mask, "gene"].values  # NumPy array
positions = df.loc[mask, "position"].values
pm5_hits = np.array([(g,p) in self.positions for g,p in zip(genes, positions)])
```

## 📈 Expected Performance Gains

### Small Dataset (17k variants)
| Criteria | Original | Optimized | Speedup |
|----------|----------|-----------|---------|
| PM1 Init | 0.001s   | 0.001s    | 1x      |
| PM1 Apply| 2.5s     | 0.025s    | **100x** |
| PM5 Init | 0.5s     | 0.3s      | 1.7x    |
| PM5 Apply| 0.8s     | 0.1s      | **8x**  |
| **Total**| **3.8s** | **0.4s**  | **9.5x** |

### Large Dataset (1M variants)
| Criteria | Original | Optimized | Speedup |
|----------|----------|-----------|---------|
| PM1 Apply| 150s     | 1.5s      | **100x** |
| PM5 Apply| 45s      | 5s        | **9x**  |
| **Total**| **195s** | **6.5s**  | **30x** |

## 🛠️ Advanced Optimizations

### 1. Parallel Processing for PM1
```python
from multiprocessing import Pool

def apply_pm1(self, df, parallel=True):
    if parallel and len(df) > 100000:
        chunks = np.array_split(df, cpu_count())
        with Pool() as pool:
            results = pool.map(self._process_chunk, chunks)
        return pd.concat(results)
```

**Best for:** Datasets > 100k variants
**Speedup:** 4-8x on multi-core systems

### 2. Cython Compilation
```bash
# Install Cython
pip install cython

# Compile PM1/PM5 to C
cythonize -i varidex/acmg/criteria_pm1.py
cythonize -i varidex/acmg/criteria_pm5.py
```

**Speedup:** Additional 2-5x

### 3. Memory-Mapped Domains
```python
import mmap

# For very large domain databases
with open('uniprot/uniprot_domains.bin', 'rb') as f:
    mmapped = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
```

**Benefit:** Instant loading, shared memory

## 📊 Profiling Tools

### Built-in Profiler
```bash
python3 profile_pm1_pm5.py
```

Output:
```
PM1 PERFORMANCE PROFILE
=======================================================================
1. PM1 Initialization (Domain Loading)...
   ⏱️  Initialization: 0.001s
2. PM1 Application (Variant Classification)...
   ⏱️  Application: 0.025s
   📊 Variants processed: 17,449
   📊 Throughput: 697,960 variants/sec
```

### Detailed Profiling
```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()
pm1.apply_pm1(df)
profiler.disable()

stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)
```

### Memory Profiling
```bash
pip install memory_profiler

python3 -m memory_profiler profile_pm1_pm5.py
```

## 🎯 Optimization Checklist

- [x] **Vectorized operations** (pandas/numpy)
- [x] **Hash set lookups** (O(1) instead of O(log n))
- [x] **Pre-filtered candidates** (reduce search space)
- [x] **Cached domain data** (pickle files)
- [ ] **Parallel processing** (for large datasets)
- [ ] **Cython compilation** (for ultra-fast execution)
- [ ] **Memory mapping** (for huge databases)

## 📚 Best Practices

### 1. Choose Right Optimization
- **Small datasets (<50k):** Vectorization only
- **Medium datasets (50k-500k):** Vectorization + hash sets
- **Large datasets (>500k):** Add parallel processing
- **Huge datasets (>5M):** Consider Cython compilation

### 2. Profile Before Optimizing
Always benchmark to identify real bottlenecks:
```bash
python3 profile_pm1_pm5.py > profile_report.txt
```

### 3. Validate Correctness
After optimization, always compare results:
```bash
python3 benchmark_pm1_pm5.py
```

## 🔧 Troubleshooting

### Issue: No speedup observed
**Solution:** Check if caching is enabled and working
```bash
ls -lh uniprot/uniprot_sprot.xml.pkl
```

### Issue: Memory errors with parallel processing
**Solution:** Reduce number of workers
```python
n_workers = min(cpu_count() // 2, 4)
```

### Issue: Inconsistent results
**Solution:** Disable parallel processing for debugging
```python
df = pm1.apply_pm1(df, parallel=False)
```

## 📈 Monitoring Performance

### Add timing to pipeline
```python
import time

start = time.time()
df = pm1.apply_pm1(df)
elapsed = time.time() - start
print(f"PM1 took {elapsed:.3f}s ({len(df)/elapsed:.0f} var/s)")
```

### Log performance metrics
```python
import logging

logging.info(f"PM1 throughput: {len(df)/elapsed:.0f} variants/sec")
```

## 🚀 Next Steps

1. Profile current performance
2. Identify bottlenecks
3. Apply appropriate optimizations
4. Benchmark improvements
5. Deploy to production

See `benchmark_pm1_pm5.py` for detailed performance comparison.
