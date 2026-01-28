# gnomAD Multi-Chromosome Setup Guide

## Overview

VariDex now supports efficient loading of gnomAD population frequency data from **per-chromosome VCF files**. This approach is:

- ✅ **Faster** - Only loads chromosomes you need
- ✅ **More reliable** - One corrupted file doesn't affect others
- ✅ **Easier to manage** - Download and verify individual files
- ✅ **Memory efficient** - Uses tabix indexing for instant lookups

---

## Installation

### 1. Install Required Dependencies

```bash
# Install pysam (includes tabix)
pip install pysam tqdm pandas

# Or add to your requirements.txt:
echo "pysam>=0.21.0" >> requirements.txt
echo "tqdm>=4.66.0" >> requirements.txt
pip install -r requirements.txt
```

### 2. Verify Tabix Installation

```bash
# Check if tabix is available
which tabix
# Should output: /usr/bin/tabix

# If not installed:
sudo apt install tabix  # Ubuntu/Debian
sudo dnf install tabix  # Fedora
conda install -c bioconda tabix  # Conda
```

---

## File Organization

### Recommended Directory Structure

```
VariDex/
├── gnomad/
│   ├── exomes/
│   │   ├── gnomad.exomes.r2.1.1.sites.1.vcf.bgz
│   │   ├── gnomad.exomes.r2.1.1.sites.1.vcf.bgz.tbi
│   │   ├── gnomad.exomes.r2.1.1.sites.2.vcf.bgz
│   │   ├── gnomad.exomes.r2.1.1.sites.2.vcf.bgz.tbi
│   │   ├── ... (chromosomes 3-22, X, Y)
│   │   └── checksums.md5
│   └── genomes/
│       ├── gnomad.genomes.v3.1.2.sites.chr1.vcf.bgz
│       ├── gnomad.genomes.v3.1.2.sites.chr1.vcf.bgz.tbi
│       └── ... (other chromosomes)
├── clinvar/
└── user_data/
```

### Your Current Setup

Based on your directory listing:

```bash
VariDex/gnomad/
├── gnomad.exomes.r2.1.1.sites.2.vcf.bgz      ✅ chr2 (4.2GB)
├── gnomad.exomes.r2.1.1.sites.2.vcf.bgz.tbi  ✅ chr2 index
└── gnomad.exomes.r2.1.1.sites.vcf.bgz        ❌ CORRUPTED (21GB)
```

**Action needed:** Remove or archive the corrupted 21GB file.

---

## Downloading gnomAD Files

### Option 1: Download Per-Chromosome Files (Recommended)

```bash
cd /media/michal/647A504F7A50205A/GENOME/Michal/VariDex10/VariDex/gnomad

# Create subdirectory for organization
mkdir -p exomes

# Download gnomAD v2.1.1 exomes (per chromosome)
# Base URL for gnomAD r2.1.1
BASE_URL="https://storage.googleapis.com/gcp-public-data--gnomad/release/2.1.1/vcf/exomes"

# Download chromosomes 1-22, X, Y (skip MT if not needed)
for chr in {1..22} X Y; do
    echo "📥 Downloading chromosome $chr..."
    wget -c "${BASE_URL}/gnomad.exomes.r2.1.1.sites.${chr}.vcf.bgz" \
        -O "exomes/gnomad.exomes.r2.1.1.sites.${chr}.vcf.bgz"
    
    # Index immediately after download
    echo "🔨 Indexing chromosome $chr..."
    tabix -p vcf "exomes/gnomad.exomes.r2.1.1.sites.${chr}.vcf.bgz"
done
```

### Option 2: Parallel Download (Faster)

```bash
# Download 4 chromosomes simultaneously
parallel -j 4 '
    wget -c "https://storage.googleapis.com/gcp-public-data--gnomad/release/2.1.1/vcf/exomes/gnomad.exomes.r2.1.1.sites.{}.vcf.bgz" -O "exomes/gnomad.exomes.r2.1.1.sites.{}.vcf.bgz" && 
    tabix -p vcf "exomes/gnomad.exomes.r2.1.1.sites.{}.vcf.bgz"
' ::: {1..22} X Y
```

### File Sizes (gnomAD v2.1.1 Exomes)

| Chromosome | Compressed Size | Variants |
|------------|----------------|----------|
| 1          | ~1.5 GB        | ~550K    |
| 2          | ~1.3 GB        | ~480K    |
| 3-22       | ~400MB-1.2GB   | varies   |
| X          | ~600 MB        | ~200K    |
| Y          | ~50 MB         | ~15K     |
| **Total**  | **~18-20 GB**  | ~7-8M    |

---

## Usage Examples

### 1. Basic Initialization

```python
from pathlib import Path
from varidex.io.loaders.gnomad import GnomADLoader

# Initialize loader
gnomad_dir = Path("./gnomad/exomes")
loader = GnomADLoader(
    gnomad_dir=gnomad_dir,
    dataset="exomes",
    version="r2.1.1",
    auto_index=True  # Auto-create indexes if missing
)

# Check what's available
stats = loader.get_statistics()
print(f"Available chromosomes: {stats['chromosomes']}")
```

### 2. Single Variant Lookup

```python
# Look up a specific variant
freq = loader.lookup_variant(
    chromosome="2",
    position=100000,
    ref="A",
    alt="G"
)

if freq:
    print(f"Allele Frequency: {freq.af}")
    print(f"Allele Count: {freq.ac}")
    print(f"African AF: {freq.af_afr}")
    print(f"European AF: {freq.af_nfe}")
else:
    print("Variant not found in gnomAD")
```

### 3. Batch Annotation of DataFrame

```python
import pandas as pd

# Your variants DataFrame
variants_df = pd.DataFrame({
    'chromosome': ['1', '2', '2', 'X'],
    'position': [12345, 100000, 200000, 50000],
    'ref_allele': ['A', 'C', 'G', 'T'],
    'alt_allele': ['G', 'T', 'A', 'C']
})

# Annotate with gnomAD frequencies
annotated_df = loader.annotate_dataframe(variants_df)

# View results
print(annotated_df[[
    'chromosome', 'position', 'ref_allele', 'alt_allele',
    'gnomad_af', 'gnomad_ac', 'gnomad_an'
]])
```

### 4. Context Manager (Auto-Close)

```python
with GnomADLoader(gnomad_dir, "exomes", "r2.1.1") as loader:
    # Use loader
    freq = loader.lookup_variant("2", 100000, "A", "G")
    # Automatically closes file handles when done
```

### 5. Integration with VariDex Pipeline

```python
from varidex.io.loaders.clinvar import load_clinvar_file
from varidex.io.loaders.gnomad import load_gnomad_frequencies
from pathlib import Path

# Load ClinVar data
clinvar_df = load_clinvar_file(Path("clinvar/clinvar_GRCh37.vcf.gz"))

# Annotate with gnomAD frequencies
annotated = load_gnomad_frequencies(
    variants_df=clinvar_df,
    gnomad_dir=Path("gnomad/exomes"),
    dataset="exomes",
    version="r2.1.1"
)

print(f"Annotated {len(annotated):,} variants with gnomAD data")
```

---

## Configuration

### Create Config File: `config/gnomad_config.yaml`

```yaml
gnomad:
  exomes:
    directory: "gnomad/exomes"
    version: "r2.1.1"
    enabled: true
  
  genomes:
    directory: "gnomad/genomes"
    version: "v3.1.2"
    enabled: false  # Set to true when available

  # Filtering thresholds
  filtering:
    max_af: 0.01  # Filter variants with AF > 1%
    min_ac: 5     # Require at least 5 observations
    populations:
      - nfe  # Non-Finnish European
      - afr  # African/African American
      - eas  # East Asian
```

### Load Config in Python

```python
import yaml
from pathlib import Path

with open("config/gnomad_config.yaml") as f:
    config = yaml.safe_load(f)

gnomad_config = config['gnomad']['exomes']
loader = GnomADLoader(
    gnomad_dir=Path(gnomad_config['directory']),
    dataset="exomes",
    version=gnomad_config['version']
)
```

---

## Troubleshooting

### Issue 1: "Failed to read BGZF block data"

**Cause:** Corrupted or incomplete download

**Solution:**
```bash
# Verify file integrity with md5sum
md5sum gnomad.exomes.r2.1.1.sites.2.vcf.bgz
# Compare with official checksum

# Re-download if corrupted
rm gnomad.exomes.r2.1.1.sites.2.vcf.bgz
wget -c "[URL]"
```

### Issue 2: "No such file or directory: *.tbi"

**Cause:** Missing tabix index

**Solution:**
```bash
# Create index manually
tabix -p vcf gnomad.exomes.r2.1.1.sites.2.vcf.bgz

# Or set auto_index=True in Python
loader = GnomADLoader(gnomad_dir, auto_index=True)
```

### Issue 3: Chromosome Not Found

**Cause:** File naming mismatch

**Solution:**
```python
# Check available chromosomes
loader = GnomADLoader(gnomad_dir)
print(loader.available_chroms)

# Scan directory
print(list(gnomad_dir.glob("*.vcf.bgz")))
```

### Issue 4: Slow Lookups

**Cause:** No tabix index or large region queries

**Solution:**
```bash
# Ensure all files are indexed
for f in gnomad/*.vcf.bgz; do
    tabix -p vcf "$f"
done

# Use batch operations instead of loops
results = loader.lookup_variants_batch(variant_list)
```

---

## Performance Tips

### 1. Pre-load Frequently Used Chromosomes

```python
# Open handles for chromosomes you'll use
for chrom in ['1', '2', '17', 'X']:
    loader._get_vcf_handle(chrom)

# Now lookups are instant (handles cached)
```

### 2. Batch Operations

```python
# ✅ GOOD: Batch lookup (100x faster)
variants = [(chr, pos, ref, alt) for ...]
results = loader.lookup_variants_batch(variants)

# ❌ BAD: Loop lookups (slow)
for variant in variants:
    result = loader.lookup_variant(*variant)
```

### 3. Use Context Manager

```python
# Automatically manages file handles
with GnomADLoader(gnomad_dir) as loader:
    results = loader.annotate_dataframe(df)
# Handles closed automatically
```

---

## Next Steps

1. **Sync to local:**
   ```bash
   git pull origin main
   ```

2. **Install dependencies:**
   ```bash
   pip install pysam tqdm
   ```

3. **Test with your chr2 file:**
   ```python
   from varidex.io.loaders.gnomad import GnomADLoader
   from pathlib import Path
   
   loader = GnomADLoader(
       gnomad_dir=Path("gnomad"),
       dataset="exomes",
       version="r2.1.1"
   )
   
   # Test lookup
   result = loader.lookup_variant("2", 100000, "A", "G")
   print(f"Test result: {result}")
   ```

4. **Download remaining chromosomes** (optional, based on your needs)

---

## Support

For issues or questions:
- Check [GitHub Issues](https://github.com/Plantucha/VariDex/issues)
- Review VariDex documentation
- gnomAD official docs: https://gnomad.broadinstitute.org/
