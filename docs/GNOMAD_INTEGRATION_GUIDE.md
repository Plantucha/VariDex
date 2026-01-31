# gnomAD Integration Guide v1.0.0

**VariDex gnomAD Population Frequency Integration**

Last Updated: January 31, 2026

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Pipeline Integration](#pipeline-integration)
6. [ACMG Evidence Codes](#acmg-evidence-codes)
7. [Usage Examples](#usage-examples)
8. [Performance](#performance)
9. [Troubleshooting](#troubleshooting)
10. [Testing](#testing)

---

## Overview

This integration adds **population frequency annotation** from gnomAD (Genome Aggregation Database) to the VariDex classification pipeline. gnomAD data enables proper application of ACMG evidence codes PM2, BA1, and BS1, which rely on allele frequency thresholds.

### What's New

- **Stage 4: gnomAD Annotation** - New pipeline stage between matching and classification
- **PM2 Evidence** - Now uses actual gnomAD frequencies (previously disabled)
- **BA1/BS1 Evidence** - Enhanced with real population data
- **Dual Mode** - Supports both API (online) and local VCF (offline) modes
- **Graceful Fallback** - Works with or without gnomAD data

### Architecture

```
Stage 1: Load User Data
         ↓
Stage 2: Load ClinVar
         ↓
Stage 3: Variant Matching
         ↓
✨ Stage 4: gnomAD Annotation ✨ [NEW]
         ↓
Stage 5: ACMG Classification (now uses gnomAD data)
         ↓
Stage 6: Report Generation
```

---

## Features

### Data Sources

**1. gnomAD API (Recommended for small datasets)**
- **Endpoint:** `https://gnomad.broadinstitute.org/api`
- **Version:** gnomAD v4 (v3 also supported)
- **Data:** Genome + Exome frequencies, population-specific AFs
- **Rate Limit:** 100 requests/minute (automatic rate limiting)
- **Cache:** 24-hour in-memory cache (1000 variants)

**2. Local VCF Files (Recommended for large datasets)**
- **Files:** Downloaded gnomAD VCF files
- **Size:** ~200GB compressed per genome/exome dataset
- **Speed:** ~10,000 variants/second
- **Offline:** No internet required

### ACMG Evidence Integration

| Evidence | Description | Threshold | Impact |
|----------|-------------|-----------|--------|
| **PM2** | Absent/rare in population | AF < 0.01% | Pathogenic (Moderate) |
| **BS1** | High population frequency | AF 1-5% | Benign (Strong) |
| **BA1** | Common polymorphism | AF > 5% | Benign (Stand-alone) |

### Performance Features

- Batch processing with progress bars
- Automatic retry with exponential backoff
- Memory-efficient DataFrame operations
- Parallel annotation support (local mode)
- Error handling and graceful degradation

---

## Installation

### Prerequisites

```bash
# Base VariDex installation
pip install varidex

# gnomAD API support (required)
pip install requests>=2.26.0

# Local VCF support (optional)
pip install pysam>=0.19.0
```

### Verify Installation

```python
from varidex.integrations.gnomad_client import GnomadClient

client = GnomadClient()
freq = client.get_variant_frequency(
    chromosome="17",
    position=43094692,
    ref="G",
    alt="A",
    dataset="gnomad_r4"
)

if freq:
    print(f"✓ gnomAD API working: AF={freq.genome_af}")
else:
    print("✗ gnomAD API not accessible")
```

---

## Configuration

### Default Configuration

```python
from varidex.pipeline.gnomad_stage import GnomADStageConfig

config = GnomADStageConfig(
    # Mode
    enabled=True,
    mode="api",  # "api" or "local"
    
    # API settings
    api_url="https://gnomad.broadinstitute.org/api",
    api_dataset="gnomad_r4",
    api_timeout=30,
    api_retry=3,
    
    # ACMG thresholds
    pm2_threshold=0.0001,  # 0.01%
    ba1_threshold=0.05,    # 5%
    bs1_threshold=0.01,    # 1%
    
    # Performance
    batch_size=1000,
    show_progress=True,
    enable_cache=True
)
```

### Local VCF Configuration

```python
from pathlib import Path

config = GnomADStageConfig(
    enabled=True,
    mode="local",
    
    # Local VCF settings
    gnomad_dir=Path("/data/gnomad/vcfs"),
    gnomad_dataset="exomes",  # or "genomes"
    gnomad_version="r2.1.1",
    
    # Performance (local is faster)
    batch_size=10000,
    show_progress=True
)
```

### Environment Variables

```bash
# Optional: Override API endpoint
export GNOMAD_API_URL="https://gnomad.broadinstitute.org/api"

# Optional: Local VCF directory
export GNOMAD_VCF_DIR="/data/gnomad/vcfs"

# Optional: Disable gnomAD
export GNOMAD_ENABLED=false
```

---

## Pipeline Integration

### Method 1: Use GnomADPipelineStage

```python
from varidex.pipeline.gnomad_stage import GnomADPipelineStage, GnomADStageConfig
import pandas as pd

# Your variants from Stage 3 (matching)
variants_df = pd.DataFrame({
    'chromosome': ['17', '13'],
    'position': [43094692, 32315508],
    'ref_allele': ['G', 'C'],
    'alt_allele': ['A', 'T'],
    'rsid': ['rs80357906', 'rs80357914']
})

# Configure gnomAD stage
config = GnomADStageConfig(enabled=True, mode="api")

# Annotate
with GnomADPipelineStage(config) as stage:
    annotated_df, stats = stage.annotate_variants(variants_df)
    
    print(f"Annotated: {stats['found_count']}/{stats['total_variants']}")
    print(f"PM2 eligible: {stats['pm2_eligible']}")
    print(f"BA1 eligible: {stats['ba1_eligible']}")

# Continue to Stage 5 (classification)
```

### Method 2: Modify orchestrator.py

Add to `varidex/pipeline/orchestrator.py`:

```python
def _stage_4_gnomad(self, matches_df: pd.DataFrame) -> pd.DataFrame:
    """Stage 4: gnomAD Frequency Annotation."""
    from varidex.pipeline.gnomad_stage import GnomADPipelineStage, GnomADStageConfig
    
    logger.info("\nStage 4: gnomAD Annotation")
    
    # Configure
    config = GnomADStageConfig(
        enabled=True,
        mode="api",  # or "local" for large datasets
        show_progress=True
    )
    
    # Annotate
    try:
        with GnomADPipelineStage(config) as stage:
            annotated_df, stats = stage.annotate_variants(matches_df)
            
            logger.info(f"  ✓ gnomAD: {stats['found_count']:,} frequencies retrieved")
            logger.info(f"  ✓ PM2 eligible: {stats['pm2_eligible']:,}")
            logger.info(f"  ✓ BA1 eligible: {stats['ba1_eligible']:,}")
            
            return annotated_df
    except Exception as e:
        logger.warning(f"  ✗ gnomAD annotation failed: {e}")
        logger.warning("  Continuing without gnomAD data...")
        return matches_df

# In main():
def main(clinvar_path, user_data_path, **kwargs):
    # ... existing stages 1-3 ...
    
    # NEW: Stage 4
    matches = _stage_4_gnomad(matches)
    
    # ... existing stages 5-6 ...
```

### Method 3: Enable in Classifier

Update `varidex/core/classifier/engine.py`:

```python
from varidex.core.classifier.evidence_assignment_gnomad import assign_evidence_codes_gnomad

class ACMGClassifier:
    def __init__(self, config=None, use_gnomad=True):
        self.config = config or ACMGConfig()
        self.use_gnomad = use_gnomad
        
        # Enable PM2 when gnomAD available
        if use_gnomad:
            self.config.enable_pm2 = True
    
    def assign_evidence(self, variant):
        if self.use_gnomad:
            # Use gnomAD-aware assignment
            return assign_evidence_codes_gnomad(variant, self.config)
        else:
            # Use original assignment
            return assign_evidence_codes(variant, self.config)
```

---

## ACMG Evidence Codes

### PM2: Absent from controls

**ACMG Definition:**
> Absent from controls (or at extremely low frequency if recessive) in Exome Sequencing Project, 1000 Genomes Project, or Exome Aggregation Consortium.

**VariDex Implementation:**
```python
if gnomad_af is not None:
    if gnomad_af < 0.0001:  # < 0.01%
        evidence.pm.add("PM2")
else:
    # Fallback: text-based heuristic
    if "rare" in clinical_sig or "novel" in clinical_sig:
        evidence.pm.add("PM2")
```

**Impact:** Moderate pathogenic evidence. Contributes to "Likely Pathogenic" when combined with other evidence.

### BS1: Allele frequency greater than expected

**ACMG Definition:**
> Allele frequency is greater than expected for disorder.

**VariDex Implementation:**
```python
if gnomad_af is not None:
    if 0.01 <= gnomad_af < 0.05:  # 1-5%
        evidence.bs.add("BS1")
```

**Impact:** Strong benign evidence. Two BS codes lead to "Benign" classification.

### BA1: Allele frequency above 5%

**ACMG Definition:**
> Allele frequency is >5% in Exome Sequencing Project, 1000 Genomes Project, or Exome Aggregation Consortium.

**VariDex Implementation:**
```python
if gnomad_af is not None:
    if gnomad_af >= 0.05:  # ≥ 5%
        evidence.ba.add("BA1")
```

**Impact:** Stand-alone benign. BA1 overrides all pathogenic evidence, resulting in "Benign" classification.

---

## Usage Examples

### Example 1: Single Variant (API Mode)

```python
from varidex.integrations.gnomad_client import GnomadClient

client = GnomadClient()

# BRCA1 pathogenic variant
freq = client.get_variant_frequency(
    chromosome="17",
    position=43094692,
    ref="G",
    alt="A",
    dataset="gnomad_r4"
)

if freq:
    print(f"Genome AF: {freq.genome_af}")
    print(f"Exome AF: {freq.exome_af}")
    print(f"Max AF: {freq.max_af}")
    print(f"Is rare (PM2): {freq.is_rare}")  # AF < 0.01%
    print(f"Is common (BA1): {freq.is_common}")  # AF > 1%
```

### Example 2: Batch Annotation (API Mode)

```python
from varidex.integrations.gnomad_annotator import annotate_variants
import pandas as pd

variants_df = pd.DataFrame({
    'chromosome': ['1', '2', '17'],
    'position': [100000, 200000, 43094692],
    'ref_allele': ['A', 'C', 'G'],
    'alt_allele': ['G', 'T', 'A']
})

# Annotate
annotated = annotate_variants(
    variants_df,
    use_api=True,
    max_af=0.01  # Filter common variants
)

print(annotated[['chromosome', 'position', 'gnomad_af']].head())
```

### Example 3: Local VCF Mode

```python
from varidex.pipeline.gnomad_stage import GnomADPipelineStage, GnomADStageConfig
from pathlib import Path

config = GnomADStageConfig(
    enabled=True,
    mode="local",
    gnomad_dir=Path("/data/gnomad/vcfs"),
    gnomad_dataset="exomes",
    batch_size=10000
)

with GnomADPipelineStage(config) as stage:
    annotated_df, stats = stage.annotate_variants(variants_df)
    
    print(f"Processed: {stats['total_variants']:,} variants")
    print(f"Coverage: {stats['coverage']:.1f}%")
```

### Example 4: Complete Pipeline

```bash
# Run full pipeline with gnomAD
python -m varidex.pipeline.orchestrator \
    --clinvar data/clinvar.vcf.gz \
    --user-data data/23andme_raw.txt \
    --enable-gnomad \
    --gnomad-mode api \
    --output-dir results/
```

---

## Performance

### API Mode (Online)

**Pros:**
- No downloads required
- Always up-to-date data
- Minimal storage

**Cons:**
- Rate limited (100 req/min)
- Network latency (~500ms/variant)
- Requires internet

**Best for:** <1,000 variants

**Expected Time:**
- 100 variants: ~1 minute
- 1,000 variants: ~10 minutes
- 10,000 variants: ~2 hours

### Local Mode (Offline)

**Pros:**
- Fast (~10,000 variants/sec)
- No rate limits
- Offline operation

**Cons:**
- Large downloads (~200GB)
- Storage requirements
- Manual updates

**Best for:** >10,000 variants

**Expected Time:**
- 100 variants: <1 second
- 1,000 variants: <1 second
- 10,000 variants: ~1 second
- 600,000 variants: ~60 seconds

### Optimization Tips

1. **Use local mode for large datasets** (>10K variants)
2. **Enable caching** for repeated queries
3. **Batch process** in chunks of 1,000-10,000
4. **Filter variants** before annotation (e.g., ClinVar matches only)
5. **Use exomes dataset** for coding variants (smaller, faster)

---

## Troubleshooting

### Issue 1: "gnomAD dependencies not installed"

```bash
# Install required packages
pip install requests>=2.26.0

# For local VCF support
pip install pysam>=0.19.0
```

### Issue 2: "Rate limit exceeded"

**Cause:** >100 API requests per minute

**Solution:**
```python
config = GnomADStageConfig(
    mode="api",
    batch_size=100,  # Reduce batch size
    # Rate limiter is automatic
)
```

Or switch to local mode.

### Issue 3: "gnomAD API timeout"

**Cause:** Network issues or slow API

**Solution:**
```python
config = GnomADStageConfig(
    api_timeout=60,  # Increase from 30s
    api_retry=5      # More retries
)
```

### Issue 4: "No gnomAD data found"

**Possible causes:**
1. Variant not in gnomAD (too rare or QC filtered)
2. Incorrect coordinates (check genome build)
3. Non-standard chromosome names

**Check:**
```python
# Verify variant exists in gnomAD
client = GnomadClient()
freq = client.get_variant_frequency(chrom, pos, ref, alt)

if freq is None:
    print("Variant not found in gnomAD")
    # Expected for ~5-10% of variants
```

### Issue 5: "PM2/BA1/BS1 not assigned"

**Diagnostic:**
```python
# Check if gnomAD data is in variant
if hasattr(variant, 'annotations'):
    print(variant.annotations.get('gnomad_af'))
else:
    print("No annotations found")

# Check classifier config
config = ACMGConfig()
print(f"PM2 enabled: {config.enable_pm2}")
print(f"BA1 enabled: {config.enable_ba1}")
```

---

## Testing

### Unit Tests

```bash
# Test gnomAD client
pytest tests/integrations/test_gnomad_client.py -v

# Test pipeline stage
pytest tests/pipeline/test_gnomad_stage.py -v

# Test evidence assignment
pytest tests/classifier/test_evidence_gnomad.py -v
```

### Integration Test

```python
# tests/integration/test_gnomad_pipeline.py
import pandas as pd
from varidex.pipeline.gnomad_stage import GnomADPipelineStage, GnomADStageConfig

def test_gnomad_integration():
    """Test complete gnomAD pipeline integration."""
    
    # Test variants (BRCA1/2 pathogenic)
    variants = pd.DataFrame({
        'chromosome': ['17', '13'],
        'position': [43094692, 32315508],
        'ref_allele': ['G', 'C'],
        'alt_allele': ['A', 'T']
    })
    
    config = GnomADStageConfig(enabled=True, mode="api")
    
    with GnomADPipelineStage(config) as stage:
        result, stats = stage.annotate_variants(variants)
        
        # Assertions
        assert 'gnomad_af' in result.columns
        assert 'gnomad_pm2_eligible' in result.columns
        assert stats['found_count'] >= 1
        assert stats['pm2_eligible'] >= 0
        
    print("✓ Integration test passed")

if __name__ == "__main__":
    test_gnomad_integration()
```

### Manual Verification

```python
# Verify BRCA1 c.5266dupC (pathogenic, rare)
from varidex.integrations.gnomad_client import GnomadClient

client = GnomadClient()
freq = client.get_variant_frequency(
    chromosome="17",
    position=43094692,
    ref="G",
    alt="A"
)

assert freq is not None, "Variant should be in gnomAD"
assert freq.is_rare, "Should be rare (PM2 eligible)"
assert not freq.is_common, "Should not be common"

print("✓ Verification passed")
print(f"  AF: {freq.genome_af}")
print(f"  PM2: {freq.is_rare}")
print(f"  BA1: {freq.is_common}")
```

---

## References

1. **gnomAD Database:**
   - Website: https://gnomad.broadinstitute.org/
   - Paper: Karczewski et al. (2020) Nature 581:434-443
   - PMID: 32461654

2. **ACMG Guidelines:**
   - Richards et al. (2015) Genet Med 17:405-424
   - PMID: 25741868

3. **API Documentation:**
   - https://gnomad.broadinstitute.org/help/api

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/Plantucha/VariDex/issues
- Documentation: https://github.com/Plantucha/VariDex/docs

**Version:** 1.0.0  
**Last Updated:** January 31, 2026  
**Status:** Development (not clinically validated)
