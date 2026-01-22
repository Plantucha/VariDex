# VariDex

**Variant Data Extraction and Classification System**

A Python package for ACMG 2015-compliant variant classification, ClinVar integration, and genomic data analysis.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE)
[![Code Status](https://img.shields.io/badge/status-in%20development-yellow.svg)](https://github.com/Plantucha/VariDex)

> **⚠️ Development Status:** VariDex is currently in active development. Testing and validation are ongoing. Not yet recommended for production clinical use.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Current Status](#current-status)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage Examples](#usage-examples)
- [Testing](#testing)
- [Licensing](#licensing)
- [Project Structure](#project-structure)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [Citation](#citation)

---

## 🔬 Overview

VariDex is a Python package designed for genomic variant analysis following the **ACMG 2015 guidelines** (Richards et al., 2015). It provides a workflow for:

- Loading and normalizing variant data from ClinVar and user genome files
- Classifying variants using ACMG/AMP 2015 evidence criteria
- Generating variant analysis reports
- Orchestrating variant analysis pipelines

**Key Reference:**  
*Richards S, et al. Standards and guidelines for the interpretation of sequence variants: a joint consensus recommendation of the American College of Medical Genetics and Genomics and the Association for Molecular Pathology. Genet Med. 2015 May;17(5):405-24. PMID: 25741868*

---

## ✨ Features

### 🎯 Core Capabilities

- **ACMG 2015 Classification Engine**
  - **Implementation status:** 7 out of 28 evidence codes (25% coverage)
  - **Implemented codes:** PVS1, PM4, PP2, BA1, BS1, BP1, BP3
  - **Pending implementation:** PS1-4, PM1-3, PM5-6, PP1, PP3-5, BS2-4, BP2, BP4-7 (21 codes)
  - Automated variant classification (Pathogenic/Likely Pathogenic/VUS/Likely Benign/Benign)
  - Follows ACMG 2015 combination rules

- **ClinVar Integration**
  - ClinVar data loading and parsing
  - Variant normalization and matching
  - Clinical significance mapping
  - Star rating extraction

- **User Genome Processing**
  - VCF file support
  - 23andMe format support
  - Custom variant data formats
  - Coordinate normalization

- **Pipeline Orchestration**
  - Workflow management
  - Batch variant processing
  - Progress tracking and logging

- **Report Generation**
  - Classification reports
  - Evidence summary tables
  - Multiple output formats (CSV, JSON, HTML planned)

### 🔧 Quality Features

- ✅ **Type Hints** - Type safety throughout codebase
- ✅ **Error Handling** - Comprehensive exception hierarchy
- ✅ **Logging** - Built-in logging system
- ✅ **Configuration** - Flexible configuration management
- ✅ **Code Standards** - Files under 500 lines, semantic naming
- ⚠️ **Testing** - In progress (see [Testing](#testing) section)
- ⚠️ **CI/CD** - Planned
- ⚠️ **Production Validation** - Pending

---

## 📊 Current Status

### Implementation Progress

| Component | Status | Notes |
|-----------|--------|-------|
| **Core Engine** | ✅ Complete | ACMG classifier engine functional |
| **Evidence Codes** | 🟡 Partial | 7/28 codes (25%) implemented |
| **ClinVar Integration** | ✅ Complete | Data loading and parsing working |
| **User File Processing** | ✅ Complete | VCF and 23andMe support |
| **Pipeline Orchestration** | ✅ Complete | End-to-end workflow functional |
| **Report Generation** | ✅ Complete | CSV and basic reporting working |
| **Test Suite** | ⚠️ Limited | Basic tests only, needs expansion |
| **Documentation** | 🟡 Partial | Core docs exist, needs completion |
| **Production Validation** | ❌ Pending | Not yet validated for clinical use |

### ACMG Evidence Code Coverage

**Implemented (7/28 = 25%):**
- PVS1: Loss-of-function in LOF-intolerant genes
- PM4: Protein length changes
- PP2: Missense in missense-rare genes
- BA1: Common polymorphism
- BS1: High population frequency
- BP1: Missense in LOF genes
- BP3: In-frame indel in repetitive region

**Pending Implementation (21/28 = 75%):**
- PS1-4: Strong pathogenic evidence (4 codes)
- PM1-3, PM5-6: Moderate pathogenic evidence (5 codes)
- PP1, PP3-5: Supporting pathogenic evidence (4 codes)
- BS2-4: Strong benign evidence (3 codes)
- BP2, BP4-7: Supporting benign evidence (5 codes)

### Known Limitations

- ⚠️ **Limited evidence code coverage**: Only 7/28 ACMG codes implemented
- ⚠️ **No external database integration**: gnomAD, SpliceAI, etc. not yet integrated
- ⚠️ **Testing incomplete**: Test suite needs significant expansion
- ⚠️ **Not clinically validated**: Not yet suitable for diagnostic use
- ⚠️ **Documentation gaps**: Some modules lack complete documentation

---

## 📦 Installation

### Prerequisites

- Python 3.9 or higher
- pip package manager

### Install from Source

```bash
# Clone the repository
git clone https://github.com/Plantucha/VariDex.git
cd VariDex

# Install in development mode
pip install -e .

# Or install required dependencies
pip install -r requirements-test.txt
```

### Verify Installation

```bash
# Set Python path
export PYTHONPATH=$(pwd):$PYTHONPATH

# Run basic tests
pytest tests/ -v
```

---

## 🚀 Quick Start

### Basic Variant Classification

```python
from varidex.version import __version__
from varidex.core.classifier.engine import ACMGClassifier
from varidex.core.models import VariantData

# Check version
print(f"VariDex v{__version__}")

# Initialize classifier
classifier = ACMGClassifier()

# Create a variant
variant = VariantData(
    rsid='rs80357906',
    chromosome='17',
    position='43094692',
    genotype='AG',
    gene='BRCA1',
    clinical_sig='Pathogenic',
    review_status='reviewed by expert panel',
    variant_type='single nucleotide variant',
    molecular_consequence='frameshift variant',
    ref_allele='G',
    alt_allele='A'
)

# Classify the variant
classification, confidence, evidence, duration = classifier.classify_variant(variant)

print(f"Classification: {classification}")
print(f"Confidence: {confidence}")
print(f"Evidence: {evidence.summary()}")
print(f"Time: {duration:.3f}s")
```

### Load ClinVar Data

```python
from varidex.io.loaders.clinvar import load_clinvar_file

# Load ClinVar VCF file
clinvar_data = load_clinvar_file('clinvar.vcf.gz')

print(f"Loaded {len(clinvar_data)} ClinVar variants")
```

### Process User Genome File

```python
from varidex.io.loaders.user import load_user_file
from varidex.io.normalization import normalize_dataframe_coordinates

# Load user VCF file
user_variants = load_user_file('sample.vcf')

# Normalize coordinates
normalized_variants = normalize_dataframe_coordinates(user_variants)

print(f"Processed {len(normalized_variants)} variants")
```

---

## 🧪 Testing

### Current Test Status

VariDex has **basic tests** covering:
- Exception hierarchy
- Core data models
- Basic functionality

**Test coverage is limited and needs expansion.**

### Run Tests

```bash
# Set Python path
export PYTHONPATH=$(pwd):$PYTHONPATH

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=varidex --cov-report=html

# Run specific test file
pytest tests/test_exceptions.py -v
```

### Testing Roadmap

- [ ] Expand test coverage to 90%+
- [ ] Add integration tests
- [ ] Add performance tests
- [ ] Set up CI/CD pipeline
- [ ] Add automated testing on multiple platforms
- [ ] Validate against known variant datasets

---

## 📄 Licensing

VariDex is available under a **dual-licensing model**:

### Open Source: AGPL v3

- ✅ **Free for research, academic, and open-source use**
- ✅ Personal genome analysis
- ✅ Non-profit research projects
- ✅ Open-source bioinformatics pipelines

**Requirements:** If you distribute or run VariDex as a network service, you must share your source code under AGPL v3.

See: [LICENSE](LICENSE) for full AGPL v3 terms

### Commercial License

**Required for:**
- ❌ Clinical diagnostic platforms (CLIA/CAP labs)
- ❌ SaaS/cloud-based variant analysis services
- ❌ Proprietary EMR/LIMS integration
- ❌ Commercial genomics products
- ❌ Keeping modifications private

**Pricing:**
- Contact for custom pricing based on use case and deployment scale
- Educational discounts available
- Volume licensing available

**Contact:** licensing@varidex.com  
**Docs:** See [LICENSING.md](LICENSING.md) and [COMMERCIAL_LICENSE.md](COMMERCIAL_LICENSE.md)

---

## 📁 Project Structure

```
VariDex/
├── varidex/                    # Main package
│   ├── __init__.py             # Package initialization
│   ├── version.py              # Version management
│   ├── exceptions.py           # Custom exceptions (14 types)
│   ├── core/                   # Core classification engine
│   │   ├── classifier/         # ACMG classifier
│   │   │   ├── engine.py       # Main classifier (v6.3.0)
│   │   │   ├── acmg_evidence_full.py  # Full 28-code implementation
│   │   │   └── config.py       # Configuration
│   │   └── models.py           # Data models
│   ├── io/                     # Input/Output operations
│   │   ├── loaders/            # Data loaders
│   │   └── normalization.py    # Coordinate normalization
│   ├── reports/                # Report generation
│   ├── pipeline/               # Pipeline orchestration
│   └── utils/                  # Utility functions
│
├── tests/                      # Test suite
│   ├── conftest.py             # Shared fixtures
│   └── test_exceptions.py      # Exception tests
│
├── docs/                       # Documentation
│   ├── ACMG_28_IMPLEMENTATION.md
│   ├── ACMG_DATA_REQUIREMENTS.md
│   └── TESTING.md
│
├── pytest.ini                  # Test configuration
├── requirements-test.txt       # Test dependencies
└── README.md                   # This file
```

---

## 📖 Documentation

### Core Modules

- **`varidex.core.classifier.engine`** - ACMG classification engine (7 evidence codes)
- **`varidex.core.classifier.acmg_evidence_full`** - Full 28-code implementation (in progress)
- **`varidex.io.loaders`** - Data loading utilities
- **`varidex.reports`** - Report generation
- **`varidex.pipeline`** - Pipeline orchestration
- **`varidex.exceptions`** - Exception handling

### Documentation Files

- **[ACMG_28_IMPLEMENTATION.md](docs/ACMG_28_IMPLEMENTATION.md)** - Full ACMG implementation guide
- **[ACMG_DATA_REQUIREMENTS.md](docs/ACMG_DATA_REQUIREMENTS.md)** - Data requirements reference
- **[TESTING.md](docs/TESTING.md)** - Testing guide
- **[LICENSING.md](LICENSING.md)** - Licensing information
- **[VARIDEX_CODE_STANDARDS.md](VARIDEX_CODE_STANDARDS.md)** - Coding standards

### Key Classes

- **`ACMGClassifier`** - Main variant classifier (engine.py)
- **`VariantData`** - Variant data model
- **`ACMGEvidenceSet`** - Evidence code container
- **`ACMGConfig`** - Classifier configuration

---

## 🤝 Contributing

We welcome contributions! VariDex is in active development and needs help with:

### Priority Areas

1. **Test Coverage** - Expand test suite to 90%+
2. **Evidence Codes** - Implement remaining 21/28 ACMG codes
3. **External Integrations** - gnomAD, SpliceAI, ClinGen, etc.
4. **Documentation** - Complete module documentation
5. **Validation** - Test against known variant datasets

### Development Setup

```bash
# Clone repository
git clone https://github.com/Plantucha/VariDex.git
cd VariDex

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .
pip install -r requirements-test.txt

# Run tests
export PYTHONPATH=$(pwd):$PYTHONPATH
pytest tests/ -v
```

### Code Standards

- ✅ Follow PEP 8 style guidelines
- ✅ All files must be under 500 lines
- ✅ Use semantic naming (no file_1, file_2 patterns)
- ✅ Include type hints
- ✅ Add docstrings to all functions
- ✅ Write tests for new features
- ✅ All tests must pass before submitting PR

See **[VARIDEX_CODE_STANDARDS.md](VARIDEX_CODE_STANDARDS.md)** for complete standards.

---

## 📝 Citation

If you use VariDex in your research, please cite:

```bibtex
@software{varidex2026,
  title = {VariDex: Variant Data Extraction and Classification System},
  author = {VariDex Development Team},
  year = {2026},
  url = {https://github.com/Plantucha/VariDex},
  note = {In development}
}
```

And the ACMG 2015 guidelines:

```bibtex
@article{richards2015standards,
  title={Standards and guidelines for the interpretation of sequence variants: a joint consensus recommendation of the American College of Medical Genetics and Genomics and the Association for Molecular Pathology},
  author={Richards, Sue and Aziz, Nazneen and Bale, Sherri and others},
  journal={Genetics in Medicine},
  volume={17},
  number={5},
  pages={405--424},
  year={2015},
  publisher={Nature Publishing Group},
  pmid={25741868}
}
```

---

## 📞 Contact & Support

- **Issues:** [GitHub Issues](https://github.com/Plantucha/VariDex/issues)
- **Discussions:** [GitHub Discussions](https://github.com/Plantucha/VariDex/discussions)
- **Commercial Licensing:** licensing@varidex.com

---

## 🔄 Version History

### v6.3.0 (2026-01-22)
- ✅ Engine.py optimizations (removed redundant operations)
- ✅ Added early exit for empty consequence
- ✅ Fixed critical bugs (orphaned decorator, data type issues)
- ✅ Code quality improvements

### v6.0.0 (2026-01-21)
- ✅ Initial release
- ✅ ACMG classification engine (7 evidence codes)
- ✅ ClinVar integration
- ✅ Pipeline orchestration
- ✅ Dual licensing (AGPL v3 + Commercial)

---

## 🎯 Roadmap

### Short Term (v6.x)
- [ ] Expand test suite to 90%+ coverage
- [ ] Complete evidence code implementation (21 remaining codes)
- [ ] Set up CI/CD pipeline
- [ ] Improve documentation

### Medium Term (v7.x)
- [ ] External database integration (gnomAD, SpliceAI)
- [ ] Clinical validation
- [ ] Performance optimization
- [ ] REST API

### Long Term (v8.x+)
- [ ] GUI interface
- [ ] Additional file format support (BAM, CRAM)
- [ ] Machine learning integration
- [ ] Cloud deployment options
- [ ] Database backend support

---

## 🙏 Acknowledgments

- ACMG/AMP for the 2015 variant interpretation guidelines
- ClinVar database for variant data
- All contributors to this project

---

## ⚠️ Disclaimer

**VariDex is currently in development and not yet validated for clinical diagnostic use.** 

This software is provided "as is" for research and educational purposes. While it follows ACMG 2015 guidelines, it:
- Has limited evidence code coverage (7/28 codes)
- Lacks comprehensive testing and validation
- Has not been clinically validated
- Should not be used for clinical decision-making without proper validation

For clinical use, consult with qualified genetic counselors and medical professionals.

---

**Built for the genomics community**

*Last updated: January 22, 2026*
