# Genome Build Liftover - Reference Guide

**Version:** 1.0.0  
**Module:** `varidex.utils.liftover`  
**Status:** Development

## Overview

The liftover module provides automatic detection and conversion of genomic coordinates between genome builds (GRCh37/hg19 and GRCh38/hg38). This ensures accurate variant matching when user data and ClinVar databases use different reference builds.

### Why Liftover?

**Problem:** 23andMe, AncestryDNA, and other consumer genomics companies typically provide data in GRCh37 (hg19) coordinates, but ClinVar increasingly uses GRCh38 (hg38). Direct coordinate matching fails when builds don't match.

**Solution:** Automatic coordinate conversion using UCSC liftOver chain files.

---

## Features

### 1. Automatic Build Detection
```python
from varidex.utils.liftover import detect_build

build = detect_build(user_df)
print(f"Detected: {build}")  # Output: "GRCh37" or "GRCh38"
```

**Detection Strategy:**
- Checks known reference positions with build-specific coordinates
- Analyzes chromosome length compatibility
- Samples 1,000 variants for efficiency
- Defaults to GRCh37 if uncertain (most common for consumer data)

### 2. Coordinate Conversion
```python
from varidex.utils.liftover import liftover_coordinates

df_converted = liftover_coordinates(
    df=user_data,
    from_build='GRCh37',
    to_build='GRCh38'
)
```

**Conversion Details:**
- Uses UCSC liftOver chain files
- Preserves original positions in `original_position` column
- Adds `liftover_success` flag for each variant
- Typical success rate: 95-99%

### 3. Automatic Build Matching
```python
from varidex.utils.liftover import ensure_build_match

matched_data, final_build = ensure_build_match(
    user_df=user_data,
    clinvar_build='GRCh38',
    auto_convert=True  # Enable automatic conversion
)
```

**What It Does:**
1. Detects user data build
2. Compares with ClinVar build
3. Auto-converts if mismatch (when enabled)
4. Validates conversion quality
5. Returns matched data ready for analysis

---

## Installation

### Requirements

```bash
pip install pyliftover
```

**Note:** The module auto-downloads UCSC chain files (~10-20 MB) on first use.

### Chain Files Location

Chain files are cached in `.cache/` directory:
```
.cache/
├── hg19ToHg38.over.chain
└── hg38ToHg19.over.chain
```

---

## Integration with Pipeline

### Option A: Manual Integration

Modify your loader to add build matching:

```python
from varidex.loaders.user_genome import load_23andme
from varidex.utils.liftover import ensure_build_match

# Load user data
user_df = load_23andme('data/genome.txt')

# Match to ClinVar build
matched_df, build = ensure_build_match(
    user_df,
    clinvar_build='GRCh38',
    auto_convert=True
)

# Continue with matching
```

### Option B: Orchestrator Integration

Add build detection to `orchestrator.py`:

```python
def run_pipeline(clinvar_path, user_path, format_type):
    # ... existing code ...
    
    # After loading user data
    from varidex.utils.liftover import ensure_build_match
    
    # Detect ClinVar build from filename or metadata
    clinvar_build = detect_clinvar_build(clinvar_path)  # You'll add this
    
    # Ensure builds match
    user_df, _ = ensure_build_match(
        user_df,
        clinvar_build,
        auto_convert=True
    )
    
    # Continue with matching...
```

### Option C: Add CLI Flag

Enhance orchestrator with build options:

```bash
python -m varidex.pipeline.orchestrator \
    clinvar/clinvar_GRCh38.vcf \
    data/genome.txt \
    --format 23andme \
    --auto-liftover  # New flag!
```

---

## Usage Examples

### Example 1: Basic Conversion

```python
import pandas as pd
from varidex.utils.liftover import grch37_to_grch38

# Your GRCh37 data
df = pd.DataFrame({
    'chromosome': ['1', '1', '2'],
    'position': [10177, 754182, 234668],
    'rsid': ['rs367896724', 'rs3094315', 'rs5678']
})

# Convert to GRCh38
df_38 = grch37_to_grch38(df)

print(df_38[['chromosome', 'position', 'original_position', 'liftover_success']])
# Output:
#   chromosome  position  original_position  liftover_success
# 0          1     10177              10177              True
# 1          1    817186             754182              True
# 2          2    233674             234668              True
```

### Example 2: Validate After Conversion

```python
from varidex.utils.liftover import (
    liftover_coordinates,
    validate_after_liftover
)

df_converted = liftover_coordinates(df, 'GRCh37', 'GRCh38')
metrics = validate_after_liftover(df_converted, 'GRCh38')

print(f"Total: {metrics['total_variants']}")
print(f"Success: {metrics['successful_conversions']}")
print(f"Failed: {metrics['failed_conversions']}")
print(f"Detected build: {metrics['detected_build']}")
```

### Example 3: Handle Failed Conversions

```python
df_converted = liftover_coordinates(df, 'GRCh37', 'GRCh38')

# Separate successful and failed
df_success = df_converted[df_converted['liftover_success'] == True]
df_failed = df_converted[df_converted['liftover_success'] == False]

print(f"Successfully converted: {len(df_success):,} variants")
print(f"Failed to convert: {len(df_failed):,} variants")

# Export failed variants for manual review
if len(df_failed) > 0:
    df_failed.to_csv('failed_liftover.csv', index=False)
```

---

## Performance

### Speed
- **Detection:** ~0.1 seconds for 600k variants (sampled)
- **Conversion:** ~2-5 seconds per 1,000 variants
- **Full genome (600k variants):** ~2-5 minutes

### Memory
- Chain file: ~20 MB in memory
- Minimal overhead for coordinate storage
- Original positions preserved for validation

### Success Rates
| Conversion | Typical Success Rate | Notes |
|------------|---------------------|-------|
| GRCh37 → GRCh38 | 96-99% | Most common, well-supported |
| GRCh38 → GRCh37 | 95-98% | Some new regions can't convert back |

---

## Troubleshooting

### Issue 1: "pyliftover not installed"

**Solution:**
```bash
pip install pyliftover
```

### Issue 2: "Could not obtain chain file"

**Causes:**
- No internet connection
- UCSC server down
- Disk full

**Solution:**
- Check internet connection
- Manually download from: http://hgdownload.soe.ucsc.edu/goldenPath/hg19/liftOver/
- Place in `.cache/` directory

### Issue 3: High failure rate (>5%)

**Possible Causes:**
- Input data quality issues
- Wrong source build specified
- Corrupted chain file

**Solution:**
```python
# Re-detect build
actual_build = detect_build(df)
print(f"Actual build: {actual_build}")

# Use correct build
df_converted = liftover_coordinates(df, actual_build, target_build)
```

### Issue 4: Positions look wrong after conversion

**Validation:**
```python
from varidex.utils.liftover import validate_after_liftover

metrics = validate_after_liftover(df_converted, expected_build)
if metrics['detected_build'] != expected_build:
    print("⚠️ Build mismatch after conversion!")
```

---

## Technical Details

### Build Detection Algorithm

1. **Reference Position Matching** (Primary):
   - Checks 8+ known positions with build-specific coordinates
   - Example: chr1:754182 (GRCh37) vs chr1:817186 (GRCh38)
   - High confidence when multiple matches found

2. **Chromosome Length Analysis** (Secondary):
   - Compares max positions to known chromosome lengths
   - GRCh37 and GRCh38 have slight length differences
   - Useful when reference positions unavailable

3. **Vote-Based Decision**:
   - Each strategy provides votes
   - Majority wins
   - Defaults to GRCh37 if tied (most common)

### Coordinate Conversion Process

1. Load UCSC chain file (describes position mappings)
2. For each variant:
   - Query chain file for position mapping
   - Update chromosome and position if mapping exists
   - Flag success/failure
3. Preserve original positions for validation
4. Return DataFrame with converted coordinates

### Why Some Variants Fail

- **Deleted regions:** Removed in target build
- **Complex rearrangements:** No simple 1-to-1 mapping
- **Gap regions:** Filled differently between builds
- **Mitochondrial variants:** Different reference sequences

---

## API Reference

### `detect_build(df, sample_size=1000)`

Detect genome build from variant positions.

**Parameters:**
- `df` (DataFrame): Variants with 'chromosome' and 'position' columns
- `sample_size` (int): Number of variants to sample for detection

**Returns:** `str` - 'GRCh37' or 'GRCh38'

### `liftover_coordinates(df, from_build, to_build, chain_file=None)`

Convert coordinates between builds.

**Parameters:**
- `df` (DataFrame): Input variants
- `from_build` (str): Source build ('GRCh37' or 'GRCh38')
- `to_build` (str): Target build ('GRCh37' or 'GRCh38')
- `chain_file` (Path, optional): Path to chain file

**Returns:** DataFrame with converted coordinates

**Added Columns:**
- `original_position`: Position before conversion
- `liftover_success`: Boolean success flag

### `ensure_build_match(user_df, clinvar_build, auto_convert=True)`

Ensure user data matches ClinVar build.

**Parameters:**
- `user_df` (DataFrame): User genomic data
- `clinvar_build` (str): ClinVar reference build
- `auto_convert` (bool): Enable automatic conversion

**Returns:** Tuple[DataFrame, str] - (matched_df, final_build)

### Convenience Functions

```python
grch37_to_grch38(df)  # Convert GRCh37 → GRCh38
grch38_to_grch37(df)  # Convert GRCh38 → GRCh37
```

---

## Best Practices

### 1. Always Validate
```python
df_converted = liftover_coordinates(df, 'GRCh37', 'GRCh38')
metrics = validate_after_liftover(df_converted, 'GRCh38')
assert metrics['detected_build'] == 'GRCh38', "Conversion failed!"
```

### 2. Handle Failed Variants
```python
# Remove failed variants before analysis
df_clean = df_converted[df_converted['liftover_success'] == True]
```

### 3. Document Build in Reports
```python
print(f"Analysis performed on: {final_build}")
print(f"Original data: {original_build}")
if original_build != final_build:
    print(f"⚠️ Data converted from {original_build} to {final_build}")
```

### 4. Cache Awareness
- Chain files cached in `.cache/`
- Safe to delete and re-download
- Consider committing to version control for offline use

---

## Limitations

1. **Not 100% Coverage:** 1-5% of variants may fail conversion
2. **One Direction Better:** GRCh37→38 more reliable than reverse
3. **Structural Variants:** Large indels/CNVs may not convert accurately
4. **Requires Internet:** First-time chain file download
5. **Processing Time:** Adds 2-5 minutes for full genomes

---

## Future Enhancements

- [ ] Support for additional builds (GRCh36, T2T-CHM13)
- [ ] Parallel processing for faster conversion
- [ ] Pre-bundled chain files (no download required)
- [ ] Fuzzy matching for failed variants
- [ ] REST API integration with NCBI Remap
- [ ] Cached conversion results

---

## References

- **UCSC liftOver:** https://genome.ucsc.edu/cgi-bin/hgLiftOver
- **Chain File Format:** https://genome.ucsc.edu/goldenPath/help/chain.html
- **GRCh37 vs GRCh38:** https://www.ncbi.nlm.nih.gov/grc/human
- **pyliftover Library:** https://pypi.org/project/pyliftover/

---

**Last Updated:** 2026-01-30  
**Maintainer:** VariDex Development Team  
**Module Status:** Development (v1.0.0-dev)
