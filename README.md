<div align="center">

[![CI](https://github.com/Plantucha/VariDex/workflows/VariDex%20CI/badge.svg)](https://github.com/Plantucha/VariDex/actions) [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) [![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)


# VariDex

### ACMG 2015-Compliant Genomic Variant Classification

*An open-source Python toolkit for automated variant interpretation following clinical genetics standards*

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-AGPL--3.0-blue.svg)](LICENSE)
[![Development Status](https://img.shields.io/badge/status-alpha-yellow.svg)](https://github.com/Plantucha/VariDex)

[Features](#-features) • [Quick Start](#-quick-start) • [Documentation](#-documentation) • [Contributing](#-contributing)

</div>

---

## ⚠️ Important Notice

> **VariDex is research software under active development. It is NOT validated for clinical use.**
>
> - ❌ Do not use for patient diagnosis or treatment decisions
> - ❌ Not approved for clinical or regulatory use  
> - ✅ Suitable for research, education, and method development

---

## 🔬 What is VariDex?

VariDex automatically classifies genetic variants using the **ACMG/AMP 2015 guidelines**—the clinical genetics community's standard for interpreting genomic variants. It processes data from ClinVar, VCF files, and direct-to-consumer genetic tests (like 23andMe) to help researchers and geneticists understand variant pathogenicity.

### Why VariDex?

**Problem:** Interpreting genetic variants is complex, time-consuming, and requires expert knowledge of ACMG criteria.

**Solution:** VariDex automates variant classification while maintaining transparency about evidence used, helping researchers:
- 🔬 Classify thousands of variants systematically
- 📊 Integrate ClinVar annotations with personal genomes
- 🧠 Understand the evidence behind each classification
- 📝 Generate standardized reports for further analysis

---

## 🎯 Key Features

### Core Capabilities

- **🧩 ACMG Classification Engine**
  - Implements 12 of 28 ACMG evidence codes 12/28 codes (PVS1,PM2+Benign)
  - Follows official ACMG/AMP 2015 combination rules
  - Evidence-based pathogenicity scoring
  - Currently includes: PVS1, PM4, PP2, BA1, BS1, BP1, BP3

- **📊 ClinVar Integration**
  - Parse and normalize ClinVar VCF files
  - Extract clinical significance and review status
  - Match user variants against ClinVar database

- **🧱 Multi-Format Input**
  - VCF files (standard genomic format)
  - 23andMe raw data files
  - Custom TSV/CSV variant lists
  - Automatic coordinate normalization

- **🧬 Genome Build Conversion** ⭐ NEW
  - Liftover utility for coordinate conversion (GRCh37 ↔ GRCh38)
  - Convert 23andMe raw data between genome assemblies
  - 99%+ success rate on 600K+ variant datasets
  - Automatic UCSC chain file management
  - See [Liftover Guide](docs/LIFTOVER_GUIDE.md)

- **📝 Comprehensive Reporting**
  - CSV and JSON output formats
  - Evidence summary for each variant
  - Confidence levels and warnings

### Technical Excellence

- ✅ **90% test coverage** with 745+ automated tests
- ✅ **Type-safe** with comprehensive type hints
- ✅ **Well-documented** with inline docstrings
- ✅ **Modular design** for extensibility
- ✅ **Performance optimized** for batch processing

---

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/Plantucha/VariDex.git
cd VariDex

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install
pip install -e .
```

### Classify Your First Variant

```python
from varidex.core.classifier.engine import ACMGClassifier
from varidex.core.models import VariantData

# Initialize classifier
classifier = ACMGClassifier()

# Create variant (BRCA1 pathogenic example)
variant = VariantData(
    chromosome="17",
    position="43094692",
    ref_allele="G",
    alt_allele="A",
    gene="BRCA1",
    rsid="rs80357906"
)

# Classify
classification, confidence, evidence, time = classifier.classify_variant(variant)

print(f"{classification} ({confidence})")
print(f"Evidence: {evidence.summary()}")
print(f"Time: {time:.3f}s")
```

**Output:**
```
Pathogenic (High)
Evidence: PVS1:1 | PP2:1
Time: 0.003s
```

### Process a VCF File

```python
from varidex.io.loaders.user import load_user_file
from varidex.pipeline.orchestrator import VariantPipeline

# Load variants
variants = load_user_file("sample.vcf")

# Run classification pipeline
pipeline = VariantPipeline()
results = pipeline.process(variants)

# Generate report
pipeline.generate_report(results, output="classification_report.csv")
```

---

## 📊 Project Status

### Current Version: **6.4.0** (Alpha Development)
**Last Updated:** January 28, 2026

| Component | Implementation | Test Coverage | Status |
|-----------|---------------|---------------|--------|
| **Classification Engine** | 25% (7/28 codes) | 90% | 🟡 Active Development |
| **ClinVar Integration** | Complete | 92% | ✅ Production Ready |
| **File Loaders** | Complete | 90% | ✅ Production Ready |
| **Pipeline System** | Complete | 90% | ✅ Production Ready |
| **Report Generation** | Complete | 88% | ✅ Production Ready |
| **Documentation** | Good | 93% | 🟡 Expanding to 100% |

### Recent Achievements (January 2026)

✅ **Test coverage increased from 86% → 90%** (150 new tests)  
✅ **Critical bug fixes** in configuration and utility modules  
✅ **Documentation initiative** launched with comprehensive tooling  
✅ **745+ automated tests** ensuring code quality  
✅ **Zero broken tests** - full test suite passing  
✅ **Black code formatting** - All code auto-formatted to PEP 8 standards  
✅ **GitHub migration complete** - Repository successfully moved to GitHub
✅ **Genome build liftover utility** - GRCh37↔GRCh38 conversion (99%+ success rate)  

### What's Working

- ✅ Basic variant classification (7 evidence codes)
- ✅ ClinVar data loading and integration
- ✅ VCF and 23andMe file parsing
- ✅ Batch variant processing
- ✅ CSV/JSON report generation
- ✅ Comprehensive error handling

### Known Limitations

- ⚠️ Only 7 of 28 ACMG codes implemented (25%)
- ⚠️ No population database integration (gnomAD)
- ⚠️ No splice prediction (SpliceAI)
- ⚠️ No computational predictors (SIFT, PolyPhen)
- ⚠️ Not clinically validated

---

## 📚 Documentation

### User Guides

- **[Installation Guide](docs/INSTALLATION.md)** - Detailed setup instructions
- **[Tutorial](docs/TUTORIAL.md)** - Step-by-step walkthrough
- **[Examples](docs/EXAMPLES.md)** - Common use cases
- **[Configuration](docs/CONFIGURATION.md)** - Customization options
- **[API Reference](docs/API_REFERENCE.md)** - Complete API documentation

### Technical Documentation

- **[ACMG Implementation Guide](ACMG_28_IMPLEMENTATION_GUIDE.md)** - Evidence code details
- **[Testing Guide](TESTING.md)** - Running and writing tests
- **[Architecture Overview](docs/ARCHITECTURE.md)** - System design
- **[Code Standards](VARIDEX_CODE_STANDARDS.md)** - Development guidelines
- **[Contributing Guide](CONTRIBUTING.md)** - How to contribute

### Recent Documentation

- ✨ **[Coverage Achievement Report](COVERAGE_90_PERCENT_ACHIEVEMENT.md)** - How we reached 90%
- ✨ **[Documentation Plan](DOCUMENTATION_100_PERCENT_PLAN.md)** - Path to 100% docs
- 📊 **[Project Status](PROJECT_STATUS_SUMMARY.md)** - Current state and roadmap

---

## 🧪 Testing

### Test Suite Statistics

```
Total Tests:        745+
Test Coverage:      90%
Pass Rate:          98.5%
Execution Time:     ~45 seconds
```

### Run Tests

```bash
# Run all tests
pytest tests/ -v

# With coverage report
pytest tests/ --cov=varidex --cov-report=html

# Open coverage report
open htmlcov/index.html
```

### Test Categories

- **Unit Tests** (450 tests) - Individual component testing
- **Integration Tests** (150 tests) - Multi-component workflows  
- **End-to-End Tests** (70 tests) - Complete pipeline validation
- **Coverage Tests** (75 tests) - Edge cases and error handling

---

## 🛣️ Roadmap

### Next Release: v6.5 (February 2026)

- [ ] Complete CI/CD pipeline setup
- [ ] Publish to Test PyPI
- [ ] Documentation portal (ReadTheDocs)
- [ ] PM2 evidence code (gnomAD integration)
- [ ] BP7 evidence code (SpliceAI integration)

### v7.0: Full ACMG Implementation (Q2 2026)

- [ ] All 28 ACMG evidence codes
- [ ] External database integrations (gnomAD, dbNSFP)
- [ ] REST API
- [ ] Web interface
- [ ] Docker deployment

### v8.0+: Clinical Validation (Q3-Q4 2026)

- [ ] Validation against known datasets
- [ ] Benchmark against clinical tools
- [ ] Performance optimization
- [ ] Cloud deployment
- [ ] v1.0.0 production release

---

## 🤝 Contributing

**We welcome contributions!** VariDex is community-driven and needs your expertise.

### High-Priority Needs

1. **🧩 ACMG Evidence Codes** - Implement remaining 21 codes
2. **📊 Database Integration** - Connect gnomAD, dbNSFP, ClinGen
3. **📖 Documentation** - API docs, tutorials, examples
4. **🧪 Clinical Validation** - Test against benchmark datasets

### Getting Started

```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/VariDex.git
cd VariDex

# Create feature branch
git checkout -b feature/amazing-feature

# Install dev dependencies
pip install -e .
pip install -r requirements-test.txt

# Make changes and test
pytest tests/ -v

# Ensure code quality
black varidex/ tests/
mypy varidex/

# Submit pull request
git push origin feature/amazing-feature
```

### Development Standards

- ✅ Maintain 90%+ test coverage
- ✅ Include docstrings (Google style)
- ✅ Type hints required
- ✅ Black code formatting (88 chars)
- ✅ Files under 500 lines

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for detailed guidelines.

---

## 📜 Licensing

### Open Source: AGPL v3

**Free for:**
- ✅ Academic and research use
- ✅ Personal genome analysis
- ✅ Open-source projects
- ✅ Non-profit organizations

**Requires:** Source code sharing if distributed or run as a service

### Commercial License

**Required for:**
- ❌ Clinical diagnostic services
- ❌ SaaS platforms
- ❌ Proprietary products
- ❌ Closed-source derivatives

**Contact:** plantucha@gmail.com for commercial licensing

---

## 📝 Citation

If VariDex supports your research, please cite:

```bibtex
@software{varidex2026,
  author = {VariDex Development Team},
  title = {VariDex: ACMG 2015-Compliant Variant Classification System},
  version = {6.4.0},
  year = {2026},
  url = {https://github.com/Plantucha/VariDex},
}
```

And the ACMG 2015 guidelines:

```bibtex
@article{richards2015standards,
  author = {Richards, Sue and Aziz, Nazneen and Bale, Sherri and others},
  title = {Standards and guidelines for the interpretation of sequence variants},
  journal = {Genetics in Medicine},
  volume = {17},
  number = {5},
  pages = {405--424},
  year = {2015},
  doi = {10.1038/gim.2015.30},
  pmid = {25741868}
}
```

---

## ❓ FAQ

**Q: Is VariDex validated for clinical use?**  
A: No. VariDex is research software and has not undergone clinical validation. Do not use for patient care.

**Q: Which ACMG codes are implemented?**  
A: Currently 7 of 28 codes (PVS1, PM4, PP2, BA1, BS1, BP1, BP3). See [implementation guide](ACMG_28_IMPLEMENTATION_GUIDE.md).

**Q: Can I use VariDex commercially?**  
A: Yes, but you need a commercial license. Contact plantucha@gmail.com.

**Q: How accurate is the classification?**  
A: Accuracy depends on data quality and available evidence codes. With only 25% ACMG coverage, results are preliminary.

**Q: Where can I get help?**  
A: Open an [issue](https://github.com/Plantucha/VariDex/issues) or start a [discussion](https://github.com/Plantucha/VariDex/discussions).

---

## 📞 Support & Contact

- **🐛 Bug Reports:** [GitHub Issues](https://github.com/Plantucha/VariDex/issues)
- **💬 Discussions:** [GitHub Discussions](https://github.com/Plantucha/VariDex/discussions)
- **📧 Email:** plantucha@gmail.com
- **💼 Commercial:** plantucha@gmail.com

---

## 🙏 Acknowledgments

- **ACMG/AMP** - 2015 variant interpretation guidelines
- **NCBI ClinVar** - Variant clinical significance database
- **gnomAD** - Population allele frequency data (integration pending)
- **Open-source community** - Tools and libraries that make this possible
- **Contributors** - Everyone who has contributed code, ideas, and feedback

---

<div align="center">

### Built with ❤️ for the Genomics Research Community

**Version 6.4.0** • **January 2026** • **Alpha Development**

[⭐ Star on GitHub](https://github.com/Plantucha/VariDex) • [📖 Read the Docs](https://github.com/Plantucha/VariDex/tree/main/docs) • [🤝 Contribute](CONTRIBUTING.md)

---

*VariDex is research software provided "as is" without warranty.*  
*Not for clinical or diagnostic use.*

</div>
