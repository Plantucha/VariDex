# VariDex Pipeline Examples

Production-ready examples demonstrating VariDex capabilities.

---

## 📋 Available Examples

### 1. `annotate_clinvar_with_gnomad.py` - Complete Pipeline

Full integration pipeline that:
- ✅ Loads user genome variants
- ✅ Matches against ClinVar database
- ✅ Annotates with gnomAD population frequencies
- ✅ Identifies rare and novel pathogenic variants
- ✅ Generates comprehensive reports

---

## 🚀 Quick Start

### Prerequisites

```bash
# Activate virtual environment
source venv/bin/activate

# Ensure dependencies installed
pip install -r requirements.txt
```

### Basic Usage

```bash
python examples/annotate_clinvar_with_gnomad.py \
    --user-variants user_data/my_genome.csv \
    --clinvar clinvar/clinvar_GRCh37.vcf.gz \
    --gnomad-dir gnomad \
    --output-dir results
```

### Advanced Usage

```bash
# Filter to rare variants only (AF < 1%)
python examples/annotate_clinvar_with_gnomad.py \
    --user-variants user_data/my_genome.csv \
    --clinvar clinvar/clinvar_GRCh37.vcf.gz \
    --gnomad-dir gnomad \
    --max-af 0.01 \
    --output-dir results/rare_variants
```

---

## 📊 Input File Formats

### User Variants File

Supported formats: **CSV**, **TSV**, **VCF**

**Required columns:**
- `chromosome` - Chromosome number (1-22, X, Y, MT)
- `position` - Genomic position (integer)
- `ref_allele` - Reference allele
- `alt_allele` - Alternate allele

**Example CSV:**
```csv
chromosome,position,ref_allele,alt_allele,rsid
1,12345,A,G,rs123456
2,67890,C,T,rs789012
17,7577120,C,T,rs397507444
```

**Optional columns:**
- `rsid` - dbSNP ID (improves matching)
- `gene` - Gene name
- `quality` - Variant call quality

### ClinVar File

Use official ClinVar VCF files:
- **GRCh37/hg19**: `clinvar_GRCh37.vcf.gz`
- **GRCh38/hg38**: `clinvar_GRCh38.vcf.gz`

Download from: https://ftp.ncbi.nlm.nih.gov/pub/clinvar/

### gnomAD Files

Per-chromosome VCF files in `gnomad/` directory:
```
gnomad/
├── gnomad.exomes.r2.1.1.sites.1.vcf.bgz
├── gnomad.exomes.r2.1.1.sites.1.vcf.bgz.tbi
├── gnomad.exomes.r2.1.1.sites.2.vcf.bgz
└── ... (chromosomes 3-22, X, Y)
```

See `docs/GNOMAD_SETUP.md` for download instructions.

---

## 📤 Output Files

The pipeline generates:

### 1. `all_variants_annotated.csv`
Complete results with all annotations:
- Original variant information
- ClinVar clinical significance
- gnomAD population frequencies
- Quality scores

### 2. `novel_pathogenic.csv`
Pathogenic variants **not found in gnomAD** (highest priority)

### 3. `rare_pathogenic.csv`
Pathogenic variants with **AF < 0.1%**

### 4. `common_pathogenic.csv`
Pathogenic variants with **AF > 1%** (may be benign)

### 5. `all_pathogenic.csv`
All pathogenic/likely pathogenic variants

### 6. `summary_statistics.txt`
Analysis summary with counts and percentages

---

## 💡 Example Workflows

### Workflow 1: Find Your Pathogenic Variants

```bash
# Run full pipeline
python examples/annotate_clinvar_with_gnomad.py \
    --user-variants user_data/my_23andme.csv \
    --clinvar clinvar/clinvar_GRCh37.vcf.gz \
    --gnomad-dir gnomad \
    --output-dir results/my_analysis

# Review high-priority variants
cat results/my_analysis/novel_pathogenic.csv
cat results/my_analysis/rare_pathogenic.csv
```

### Workflow 2: Focus on Rare Variants

```bash
# Only analyze variants with AF < 0.1%
python examples/annotate_clinvar_with_gnomad.py \
    --user-variants user_data/variants.csv \
    --clinvar clinvar/clinvar_GRCh37.vcf.gz \
    --gnomad-dir gnomad \
    --max-af 0.001 \
    --output-dir results/rare_only
```

### Workflow 3: Batch Processing

```bash
#!/bin/bash
# Process multiple samples

for sample in user_data/*.csv; do
    name=$(basename "$sample" .csv)
    echo "Processing $name..."
    
    python examples/annotate_clinvar_with_gnomad.py \
        --user-variants "$sample" \
        --clinvar clinvar/clinvar_GRCh37.vcf.gz \
        --gnomad-dir gnomad \
        --output-dir "results/$name"
done
```

---

## 🔍 Understanding Results

### Clinical Significance Categories

| Category | Meaning | Action |
|----------|---------|--------|
| **Pathogenic** | Known disease-causing | Consult genetic counselor |
| **Likely Pathogenic** | Probably disease-causing | Clinical review recommended |
| **Uncertain Significance** | Unknown impact | Monitor research updates |
| **Likely Benign** | Probably harmless | Generally no action needed |
| **Benign** | Confirmed harmless | No action needed |

### gnomAD Frequency Interpretation

| Allele Frequency | Category | Interpretation |
|------------------|----------|----------------|
| Not in gnomAD | Novel | Rare, requires careful evaluation |
| < 0.01% | Ultra-rare | May be pathogenic |
| 0.01% - 0.1% | Rare | Context-dependent |
| 0.1% - 1% | Uncommon | Often benign |
| > 1% | Common | Usually benign |

### Priority Ranking

**Highest Priority:**
1. Novel pathogenic variants (not in gnomAD)
2. Rare pathogenic variants (AF < 0.1%)

**Medium Priority:**
3. Pathogenic variants with AF 0.1-1%
4. Likely pathogenic variants

**Lower Priority:**
5. Variants of uncertain significance
6. Common pathogenic variants (may be misclassified)

---

## 🛠️ Troubleshooting

### Error: "Missing required columns"

**Solution:** Ensure your input CSV has these exact column names:
```csv
chromosome,position,ref_allele,alt_allele
```

### Error: "ClinVar file not found"

**Solution:** Download ClinVar VCF:
```bash
mkdir -p clinvar
wget https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh37/clinvar.vcf.gz \
    -O clinvar/clinvar_GRCh37.vcf.gz
```

### Error: "gnomAD directory not found"

**Solution:** Download gnomAD files (see `docs/GNOMAD_SETUP.md`)

### Low ClinVar Match Rate

**Possible causes:**
- Wrong genome build (GRCh37 vs GRCh38)
- Chromosome naming mismatch (chr1 vs 1)
- Missing rsID column

**Solution:** Verify genome build and normalize chromosome names

---

## 📚 Additional Resources

- **VariDex Documentation**: `docs/`
- **gnomAD Setup Guide**: `docs/GNOMAD_SETUP.md`
- **ClinVar Database**: https://www.ncbi.nlm.nih.gov/clinvar/
- **gnomAD Browser**: https://gnomad.broadinstitute.org/

---

## 🤝 Contributing

Have a useful pipeline example? Contribute:

1. Fork the repository
2. Add your example to `examples/`
3. Update this README
4. Submit a pull request

---

## 📧 Support

For issues or questions:
- Check existing examples
- Review documentation in `docs/`
- Open an issue on GitHub

---

**Version:** 1.0.0 DEVELOPMENT  
**Last Updated:** 2026-01-28
