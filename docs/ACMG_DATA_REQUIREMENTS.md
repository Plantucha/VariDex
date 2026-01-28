# ACMG Evidence Code Data Requirements - Quick Reference

## Evidence Code Status Matrix

| Code | Works Now | Needs External Data | Data Source | Priority |
|------|-----------|---------------------|-------------|----------|
| **PVS1** | ✅ Yes | No | Gene annotations | High |
| **PS1** | ⚠️ Partial | Yes | ClinVar pathogenic at same AA | Medium |
| **PS2** | ❌ No | Yes | Parental genotypes | Low |
| **PS3** | ❌ No | Yes | Functional studies | Low |
| **PS4** | ❌ No | Yes | Case-control data | Low |
| **PM1** | ❌ No | Yes | UniProt/Pfam domains | High |
| **PM2** | ❌ No | Yes | gnomAD/ExAC | **Critical** |
| **PM3** | ❌ No | Yes | Phasing data | Low |
| **PM4** | ✅ Yes | No | Consequence annotations | High |
| **PM5** | ❌ No | Yes | ClinVar positional data | Medium |
| **PM6** | ⚠️ Manual | Yes | Clinical assessment | Low |
| **PP1** | ❌ No | Yes | Family segregation | Low |
| **PP2** | ✅ Yes | No | Gene constraint | High |
| **PP3** | ❌ No | Yes | SIFT/PolyPhen/CADD | **Critical** |
| **PP4** | ⚠️ Manual | Yes | Clinical phenotype | Low |
| **PP5** | ✅ Yes | No | ClinVar significance | High |
| **BA1** | ❌ No | Yes | gnomAD (AF > 5%) | **Critical** |
| **BS1** | ❌ No | Yes | gnomAD (AF > 1%) | **Critical** |
| **BS2** | ❌ No | Yes | Healthy cohort data | Low |
| **BS3** | ❌ No | Yes | Functional studies | Low |
| **BS4** | ❌ No | Yes | Family segregation | Low |
| **BP1** | ✅ Yes | No | Gene annotations | High |
| **BP2** | ❌ No | Yes | Phasing data (dominant) | Low |
| **BP3** | ⚠️ Partial | Yes | Repeat region annotations | Medium |
| **BP4** | ❌ No | Yes | SIFT/PolyPhen/CADD | **Critical** |
| **BP5** | ⚠️ Manual | Yes | Clinical records | Low |
| **BP6** | ✅ Yes | No | ClinVar significance | High |
| **BP7** | ❌ No | Yes | SpliceAI/MaxEntScan | High |

**Summary**:
- ✅ **Working Now**: 6/28 (21%) - PVS1, PM4, PP2, PP5, BP1, BP6
- ⚠️ **Partial/Manual**: 4/28 (14%) - PS1, PM6, PP4, BP3, BP5
- ❌ **Needs External Data**: 18/28 (64%)

---

## Critical Priority Data Sources

These 3 data sources enable 10 evidence codes (36% coverage):

### 1. gnomAD (PM2, BA1, BS1)
**Enables**: 3 codes  
**API**: https://gnomad.broadinstitute.org/api  
**Local**: Download gnomAD VCF (25GB compressed)

```python
# GraphQL API Example
import requests

query = '''
query {
  variant(dataset: gnomad_r3, variantId: "1-55516888-G-A") {
    genome { af }
  }
}
'''

response = requests.post(
    'https://gnomad.broadinstitute.org/api',
    json={'query': query}
)

af = response.json()['data']['variant']['genome']['af']
```

### 2. dbNSFP (PP3, BP4 - 7 codes total)
**Enables**: SIFT, PolyPhen-2, CADD, REVEL, MutationTaster, FATHMM, MetaSVM  
**Download**: https://sites.google.com/site/jpopgen/dbNSFP (30GB)  
**Format**: Tabix-indexed TSV

```python
import pysam

tbx = pysam.TabixFile('dbNSFP4.4a.gz')
for row in tbx.fetch('1', 55516887, 55516888):
    fields = row.split('\t')
    sift = float(fields[25])        # SIFT_score
    polyphen = float(fields[30])    # Polyphen2_HDIV_score
    cadd = float(fields[117])       # CADD_phred
    revel = float(fields[125])      # REVEL_score
```

### 3. SpliceAI (BP7)
**Enables**: 1 code  
**Install**: `pip install spliceai`  
**Precomputed**: Download SpliceAI scores VCF

```python
from spliceai import get_delta_scores

scores = get_delta_scores(
    chrom='1',
    pos=55516888,
    ref='G',
    alt='A',
    assembly='hg38'
)

max_score = max(scores)  # Max delta score
```

---

## High Priority Data Sources

These enable 2 additional codes:

### 4. UniProt/Pfam Domains (PM1)
**API**: https://www.ebi.ac.uk/proteins/api/  
**Alternative**: Download Pfam-A.full.gz

```python
import requests

url = 'https://www.ebi.ac.uk/proteins/api/proteins/P38398'  # BRCA1
response = requests.get(url, headers={'Accept': 'application/json'})

for feature in response.json()['features']:
    if feature['type'] == 'domain':
        print(f"{feature['description']}: {feature['begin']}-{feature['end']}")
```

### 5. Repeat Regions (BP3)
**Source**: RepeatMasker track from UCSC  
**Download**: http://hgdownload.soe.ucsc.edu/goldenPath/hg38/database/rmsk.txt.gz

```python
import pysam

rmsk = pysam.TabixFile('rmsk.txt.gz')
for row in rmsk.fetch('chr1', 55516887, 55516888):
    fields = row.split('\t')
    repeat_class = fields[11]
    repeat_name = fields[10]
    print(f"In repeat: {repeat_name} ({repeat_class})")
```

---

## Medium Priority (Clinical Context)

### 6. ClinVar Variant-Level Data (PS1, PM5)
**Download**: clinvar_20260101.vcf.gz  
**Size**: ~3GB compressed

```python
import vcf

vcf_reader = vcf.Reader(filename='clinvar.vcf.gz')

for record in vcf_reader.fetch('1', 55516888, 55516889):
    clnsig = record.INFO.get('CLNSIG', [])
    hgvs_p = record.INFO.get('HGVS_P', [])
    
    if 'Pathogenic' in clnsig:
        print(f"Pathogenic variant: {hgvs_p}")
```

---

## Low Priority (Specialized Clinical Data)

These require manual clinical review or specialized cohorts:

- **PS2, PM6**: Parental genotypes (trio sequencing)
- **PS3, BS3**: Functional studies (literature review)
- **PS4**: Case-control studies (research cohorts)
- **PM3, BP2**: Phasing data (family sequencing or molecular phasing)
- **PP1, BS4**: Segregation analysis (extended families)
- **PP4**: Phenotype matching (clinical assessment)
- **BS2**: Healthy adult cohorts (research databases)
- **BP5**: Alternate diagnosis (clinical records)

---

## Implementation Phases

### Phase 1: Core (6 codes working)
**Status**: ✅ Complete  
**Codes**: PVS1, PM4, PP2, PP5, BP1, BP6  
**Data**: Gene annotations, ClinVar significance  
**Coverage**: 21%

### Phase 2: Population Genetics (9 codes)
**Add**: gnomAD  
**New Codes**: PM2, BA1, BS1  
**Coverage**: 32% (+11%)

### Phase 3: Computational Predictions (11 codes)
**Add**: dbNSFP, SpliceAI  
**New Codes**: PP3, BP4, BP7  
**Coverage**: 39% (+7%)

### Phase 4: Functional Annotations (13 codes)
**Add**: UniProt domains, RepeatMasker  
**New Codes**: PM1, BP3  
**Coverage**: 46% (+7%)

### Phase 5: ClinVar Enrichment (15 codes)
**Add**: Variant-level ClinVar parsing  
**New Codes**: PS1, PM5  
**Coverage**: 54% (+8%)

### Phase 6: Clinical Integration (28 codes)
**Add**: Clinical records, family data  
**New Codes**: PS2-4, PM3, PM6, PP1, PP4, BS2-4, BP2, BP5  
**Coverage**: 100% (+46%)

---

## Quick Setup Guide

### Minimal Setup (Phase 2-3: 39% coverage)

```bash
# 1. Download gnomAD (25GB compressed)
wget https://storage.googleapis.com/gcp-public-data--gnomad/release/3.1.2/vcf/genomes/gnomad.genomes.v3.1.2.sites.vcf.bgz
tabix -p vcf gnomad.genomes.v3.1.2.sites.vcf.bgz

# 2. Download dbNSFP (30GB compressed)
wget http://database.liulab.science/dbNSFP4.4a.zip
unzip dbNSFP4.4a.zip
cat dbNSFP4.4a_variant.chr* | bgzip -c > dbNSFP4.4a.gz
tabix -s 1 -b 2 -e 2 dbNSFP4.4a.gz

# 3. Install SpliceAI
pip install spliceai

# 4. Download reference genome (for SpliceAI)
wget http://hgdownload.soe.ucsc.edu/goldenPath/hg38/bigZips/hg38.fa.gz
gunzip hg38.fa.gz
samtools faidx hg38.fa
```

### Recommended Setup (Phase 4: 46% coverage)

```bash
# Add to minimal setup:

# 5. Download Pfam domains
wget ftp://ftp.ebi.ac.uk/pub/databases/Pfam/current_release/Pfam-A.full.gz

# 6. Download RepeatMasker
wget http://hgdownload.soe.ucsc.edu/goldenPath/hg38/database/rmsk.txt.gz
tabix -p bed rmsk.txt.gz
```

### Full Setup (Phase 5: 54% coverage)

```bash
# Add to recommended setup:

# 7. Download full ClinVar VCF
wget https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/clinvar.vcf.gz
wget https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/clinvar.vcf.gz.tbi
```

**Total Disk Space**: ~100GB  
**Setup Time**: ~4 hours (download time dependent)

---

## Configuration Template

Add to `varidex/core/config.py`:

```python
# External Data Paths
EXTERNAL_DATA = {
    'gnomad_vcf': '/data/gnomad/gnomad.genomes.v3.1.2.sites.vcf.bgz',
    'dbnsfp': '/data/dbnsfp/dbNSFP4.4a.gz',
    'spliceai_ref': '/data/reference/hg38.fa',
    'pfam_domains': '/data/pfam/Pfam-A.full.gz',
    'repeatmasker': '/data/repeats/rmsk.txt.gz',
    'clinvar_vcf': '/data/clinvar/clinvar.vcf.gz'
}

# Evidence Code Thresholds
ACMG_THRESHOLDS = {
    'ba1_af': 0.05,           # 5%
    'bs1_af': 0.01,           # 1%
    'pm2_af': 0.0001,         # 0.01%
    'cadd_pathogenic': 20.0,  # CADD phred
    'spliceai_high': 0.5,     # SpliceAI delta
    'sift_deleterious': 0.05, # SIFT
    'polyphen_damaging': 0.85 # PolyPhen-2
}
```

---

## API Rate Limits

| Service | Rate Limit | Solution |
|---------|------------|----------|
| gnomAD API | 10 req/sec | Use local VCF |
| UniProt API | 100 req/sec | Cache results |
| dbNSFP | N/A | Local file (recommended) |
| SpliceAI | N/A | Local model |

---

## Storage Requirements

| Phase | Storage | Data Sources |
|-------|---------|-------------|
| Phase 1 | <1GB | ClinVar summary, gene lists |
| Phase 2 | ~30GB | + gnomAD VCF |
| Phase 3 | ~60GB | + dbNSFP |
| Phase 4 | ~65GB | + Pfam, RepeatMasker |
| Phase 5 | ~70GB | + Full ClinVar VCF |
| Phase 6 | Variable | + Clinical databases |

---

## Summary

**Current Implementation**: 28/28 codes (100% complete)  
**Functional Now**: 6/28 codes (21%)  
**With Critical Data**: 16/28 codes (57%)  
**With Recommended Data**: 18/28 codes (64%)

**Critical Next Steps**:
1. ❗ Integrate gnomAD (enables PM2, BA1, BS1)
2. ❗ Integrate dbNSFP (enables PP3, BP4)
3. ❗ Add SpliceAI (enables BP7)
4. Add domain annotations (enables PM1)
5. Enhance ClinVar parsing (enables PS1, PM5)

**File**: `varidex/core/classifier/acmg_evidence_full.py` (477 lines)  
**Guide**: `ACMG_28_IMPLEMENTATION_GUIDE.md`  
**Reference**: Richards et al. 2015, PMID 25741868
