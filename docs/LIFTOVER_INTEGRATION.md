# Liftover Integration Guide

**For:** Integrating liftover into `orchestrator.py`  
**Status:** Implementation Guide  
**Version:** 1.0.0

---

## Quick Start

### 1. Install Dependency

```bash
pip install pyliftover
```

### 2. Test the Module

```bash
python -m varidex.utils.liftover
```

Expected output:
```
======================================================================
TESTING varidex.utils.liftover v1.0.0-dev
======================================================================

🔍 Detected build: GRCh37 (votes: 37=3, 38=0)
✓ Build detection test: GRCh37
✓ Same build test: positions unchanged

======================================================================
✅ ALL TESTS PASSED
======================================================================
```

---

## Integration Option 1: Minimal (Recommended)

**Where:** Add to `orchestrator.py` after loading user data

### Code Addition

```python
# In orchestrator.py, after user data loading (around line 150)

from varidex.utils.liftover import ensure_build_match

def detect_clinvar_build(clinvar_path: Path) -> str:
    """Detect build from ClinVar filename or metadata."""
    filename = clinvar_path.name.lower()
    
    if 'grch38' in filename or 'hg38' in filename:
        return 'GRCh38'
    elif 'grch37' in filename or 'hg19' in filename:
        return 'GRCh37'
    else:
        # Default to GRCh38 (ClinVar current standard)
        logger.warning(
            "Could not detect ClinVar build from filename, assuming GRCh38"
        )
        return 'GRCh38'

def run_pipeline(...):
    # ... existing code to load user data ...
    
    logger.info("")
    logger.info("="*70)
    logger.info("[2B/7] 🔄 BUILD COMPATIBILITY CHECK")
    logger.info("="*70)
    
    # Detect ClinVar build
    clinvar_build = detect_clinvar_build(Path(clinvar_path))
    
    # Ensure builds match (with auto-conversion)
    user_df, final_build = ensure_build_match(
        user_df=user_df,
        clinvar_build=clinvar_build,
        auto_convert=True  # Enable automatic liftover
    )
    
    logger.info(f"  Final user data build: {final_build}")
    logger.info("="*70)
    logger.info("")
    
    # Continue with rest of pipeline...
```

### Expected Output

```
======================================================================
[2B/7] 🔄 BUILD COMPATIBILITY CHECK
======================================================================

======================================================================
BUILD COMPATIBILITY CHECK
======================================================================
  User data: GRCh37
  ClinVar:   GRCh38
  ⚠️  Build mismatch detected!
  🔄 Auto-converting: GRCh37 → GRCh38
======================================================================

📥 Downloading chain file: hg19ToHg38.over.chain...
📦 Decompressing hg19ToHg38.over.chain.gz...
✓ Chain file ready: .cache/hg19ToHg38.over.chain
🔄 Converting 601,845 variants: GRCh37 → GRCh38
✓ Liftover complete: 589,234/601,845 succeeded (97.9%)
⚠️  12,611 variants could not be converted

======================================================================
LIFTOVER VALIDATION
======================================================================
  Total variants: 601,845
  Converted: 589,234
  Failed: 12,611
  Detected build: GRCh38
======================================================================

  Final user data build: GRCh38
======================================================================
```

---

## Integration Option 2: With CLI Flag

### Add CLI Argument

```python
# In orchestrator.py CLI section

@click.command()
@click.argument('clinvar_path', type=click.Path(exists=True))
@click.argument('user_path', type=click.Path(exists=True))
@click.option('--format', type=click.Choice(['23andme', 'vcf']), required=True)
@click.option(
    '--auto-liftover/--no-auto-liftover',
    default=True,
    help='Automatically convert between genome builds if needed'
)
def main(clinvar_path, user_path, format, auto_liftover):
    """Run VariDex pipeline with optional build conversion."""
    run_pipeline(
        clinvar_path=clinvar_path,
        user_path=user_path,
        format_type=format,
        auto_liftover=auto_liftover  # Pass to pipeline
    )
```

### Usage

```bash
# With auto-liftover (default)
python -m varidex.pipeline.orchestrator \
    clinvar/clinvar_GRCh38.vcf \
    data/genome.txt \
    --format 23andme

# Disable auto-liftover
python -m varidex.pipeline.orchestrator \
    clinvar/clinvar_GRCh38.vcf \
    data/genome.txt \
    --format 23andme \
    --no-auto-liftover
```

---

## Integration Option 3: Pre-conversion Script

**Use Case:** Convert data once, use multiple times

### Create Standalone Script

```python
#!/usr/bin/env python3
"""convert_genome_build.py - Standalone build converter"""

import click
import pandas as pd
from pathlib import Path
from varidex.loaders.user_genome import load_23andme
from varidex.utils.liftover import liftover_coordinates, detect_build

@click.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.argument('output_file', type=click.Path())
@click.option('--from-build', type=click.Choice(['GRCh37', 'GRCh38']), help='Source build (auto-detect if not specified)')
@click.option('--to-build', type=click.Choice(['GRCh37', 'GRCh38']), required=True, help='Target build')
@click.option('--format', type=click.Choice(['23andme', 'vcf']), default='23andme')
def convert(input_file, output_file, from_build, to_build, format):
    """Convert genomic data between builds."""
    # Load data
    if format == '23andme':
        df = load_23andme(input_file)
    else:
        # Add VCF loading
        pass
    
    # Detect source build if not specified
    if from_build is None:
        from_build = detect_build(df)
        print(f"Detected source build: {from_build}")
    
    # Convert
    df_converted = liftover_coordinates(df, from_build, to_build)
    
    # Save (keep only successful)
    df_success = df_converted[df_converted['liftover_success'] == True]
    
    # Export in 23andMe format
    with open(output_file, 'w') as f:
        f.write("# rsid\tchromosome\tposition\tgenotype\n")
        for _, row in df_success.iterrows():
            f.write(f"{row['rsid']}\tchr{row['chromosome']}\t{row['position']}\t{row['genotype']}\n")
    
    print(f"\n✓ Converted {len(df_success):,} variants to {output_file}")
    print(f"⚠️  {len(df_converted) - len(df_success):,} variants failed conversion")

if __name__ == '__main__':
    convert()
```

### Usage

```bash
# Convert 23andMe data from GRCh37 to GRCh38
python convert_genome_build.py \
    data/genome_raw_grch37.txt \
    data/genome_converted_grch38.txt \
    --to-build GRCh38 \
    --format 23andme

# Then use converted file
python -m varidex.pipeline.orchestrator \
    clinvar/clinvar_GRCh38.vcf \
    data/genome_converted_grch38.txt \
    --format 23andme
```

---

## Testing the Integration

### Test 1: Same Build (No Conversion)

```bash
# Both GRCh37
python -m varidex.pipeline.orchestrator \
    clinvar/clinvar_GRCh37.vcf.gz \
    data/genome_grch37.txt \
    --format 23andme
```

**Expected:** No conversion, direct matching

### Test 2: Build Mismatch (With Conversion)

```bash
# GRCh37 user data vs GRCh38 ClinVar
python -m varidex.pipeline.orchestrator \
    clinvar/clinvar_GRCh38.vcf \
    data/genome_grch37.txt \
    --format 23andme
```

**Expected:** Auto-conversion from GRCh37 to GRCh38

### Test 3: Disabled Auto-conversion

```bash
python -m varidex.pipeline.orchestrator \
    clinvar/clinvar_GRCh38.vcf \
    data/genome_grch37.txt \
    --format 23andme \
    --no-auto-liftover
```

**Expected:** Warning message, no conversion, lower match rate

---

## Validation

### Check Conversion Success

After integration, validate with these checks:

```python
# In your results DataFrame
if 'liftover_success' in results_df.columns:
    total = len(results_df)
    success = results_df['liftover_success'].sum()
    print(f"Liftover success rate: {100*success/total:.1f}%")
```

### Compare Match Rates

**Before Liftover:**
```
Matched: 17,449 variants (2.9%)
rsID: 19,614 | Coordinate: 278
```

**After Liftover:**
```
Matched: 23,500+ variants (3.9%+)
rsID: 19,614 | Coordinate: 4,500+
```

Coordinate matches should **significantly increase** when builds are properly matched.

---

## Troubleshooting Integration

### Issue: Import Error

```python
ModuleNotFoundError: No module named 'pyliftover'
```

**Fix:**
```bash
pip install pyliftover
```

### Issue: Chain File Download Fails

**Symptoms:** Can't download from UCSC

**Fix:** Manual download
```bash
mkdir -p .cache
cd .cache
wget http://hgdownload.soe.ucsc.edu/goldenPath/hg19/liftOver/hg19ToHg38.over.chain.gz
gunzip hg19ToHg38.over.chain.gz
```

### Issue: Low Conversion Rate (<90%)

**Possible Causes:**
1. Wrong source build specified
2. Poor quality input data
3. Data already in target build

**Debug:**
```python
from varidex.utils.liftover import detect_build
actual_build = detect_build(user_df)
print(f"Actual build: {actual_build}")
```

---

## Performance Impact

### Timing
- **No conversion needed:** +0.1s (detection only)
- **With conversion:** +2-5 minutes for 600k variants

### Memory
- Chain file: ~20 MB
- Conversion overhead: Minimal

### Recommendation

**First Run:** Accept 2-5 minute overhead for accurate results

**Repeated Runs:** Consider pre-converting data once, then reuse

---

## Next Steps

1. ✅ Install pyliftover
2. ✅ Test liftover module
3. ⬜ Choose integration option (1, 2, or 3)
4. ⬜ Modify orchestrator.py
5. ⬜ Test with both GRCh37 and GRCh38 ClinVar
6. ⬜ Validate match rate improvements
7. ⬜ Document build in reports

---

**Questions?** Check [LIFTOVER.md](LIFTOVER.md) for full API reference.
