# VariDex

**Variant Data Extraction and Classification System**

A Python package for ACMG 2015-compliant variant classification, ClinVar integration, and genomic data analysis.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE)
[![Code Status](https://img.shields.io/badge/status-in%20development-yellow.svg)](https://github.com/Plantucha/VariDex)
[![Test Coverage](https://img.shields.io/badge/coverage-86%25%20→%2090%25-yellow.svg)](https://github.com/Plantucha/VariDex)

> **⚠️ DEVELOPMENT STATUS:** VariDex is currently **IN DEVELOPMENT**. Testing and validation are ongoing. **NOT recommended for production clinical use.**

> **📈 COVERAGE IMPROVEMENT:** Test coverage increase from 86% → 90% **IN PROGRESS**. See [COVERAGE_IMPROVEMENT_SUMMARY.md](COVERAGE_IMPROVEMENT_SUMMARY.md) for details.

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
  - **Implementation status:** 7 out of 28 evidence codes **(25% coverage)**
  - **Implemented codes:** PVS1, PM4, PP2, BA1, BS1, BP1, BP3
  - **Pending implementation:** 21 codes (PS1-4, PM1-3, PM5-6, PP1, PP3-5, BS2-4, BP2, BP4-7)
  - Automated variant classification following ACMG 2015 combination rules
  - Evidence-based classification system

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
  - CSV and JSON output formats

### 🔧 Technical Features

- ✅ **Type Hints** - 100% type hint coverage
- ✅ **Error Handling** - Comprehensive exception hierarchy
- ✅ **Logging** - Built-in structured logging
- ✅ **Configuration** - Flexible configuration management
- ✅ **Code Standards** - Files under 500 lines, semantic naming
- 🟡 **Testing** - 86% coverage → **90% target** (45+ new tests added)
- 🟡 **CI/CD** - Configured, awaiting final setup
- ❌ **Clinical Validation** - Not yet validated for diagnostic use

---

## 📊 Current Status

**Project Stage:** **Alpha/Beta Transition (v0.6-0.8 equivalent)**

### Implementation Progress

| Component | Status | Coverage | Notes |
|-----------|--------|----------|-------|
| **Core Engine** | ✅ Functional | 86% | Classification logic works |
| **Evidence Codes** | 🟡 Partial | 25% | 7/28 codes implemented |
| **ClinVar Integration** | ✅ Complete | 90% | Data loading functional |
| **User File Processing** | ✅ Complete | 88% | VCF and 23andMe support |
| **Pipeline Orchestration** | ✅ Functional | 86% | End-to-end workflow works |
| **Report Generation** | ✅ Complete | 82% | CSV and JSON output |
| **Test Suite** | 🟡 Improving | **86% → 90%** | **595+ tests** (45 new) |
| **Documentation** | 🟡 Good | 93% | Core docs complete |
| **CI/CD** | 🟡 Configured | - | Awaiting GitHub secrets |
| **Clinical Validation** | ❌ None | - | Not suitable for clinical use |

**Legend:** ✅ Complete | 🟡 In Progress | ❌ Not Started

### ACMG Evidence Code Coverage

**Implemented (7/28 = 25%):**
- ✅ **PVS1** - Loss-of-function in LOF-intolerant genes
- ✅ **PM4** - Protein length changes
- ✅ **PP2** - Missense in missense-rare genes
- ✅ **BA1** - Common polymorphism (allele frequency)
- ✅ **BS1** - High population frequency
- ✅ **BP1** - Missense in LOF genes
- ✅ **BP3** - In-frame indel in repetitive region

**Pending Implementation (21/28 = 75%):**
- ❌ **PS1-4** - Strong pathogenic evidence (4 codes) - *Requires computational predictions*
- ❌ **PM1-3, PM5-6** - Moderate pathogenic evidence (5 codes) - *Requires functional domain data*
- ❌ **PP1, PP3-5** - Supporting pathogenic evidence (4 codes) - *Requires cosegregation, predictions*
- ❌ **BS2-4** - Strong benign evidence (3 codes) - *Requires observation data*
- ❌ **BP2, BP4-7** - Supporting benign evidence (5 codes) - *Requires splicing, computational data*

### Recent Improvements (January 24, 2026)

✅ **Critical Bug Fixes:**
- Fixed string formatting bugs in config.py (missing f-string prefixes)
- Fixed performance issue (__getattribute__ → __getattr__)
- Documented version fragmentation (engine.py, engine_v7.py, engine_v8.py)

🟡 **Coverage Improvement Initiative:**
- **Goal:** 86% → 90% test coverage
- **New Tests:** 45+ tests in `test_coverage_gaps.py`
- **Target Modules:** 7 modules below 90%
- **Status:** IN PROGRESS
- **See:** [COVERAGE_IMPROVEMENT_SUMMARY.md](COVERAGE_IMPROVEMENT_SUMMARY.md)

### Known Limitations

**Functional Limitations:**
- ⚠️ **Limited evidence code coverage**: Only 7/28 ACMG codes (25%)
- ⚠️ **No external database integration**: gnomAD, SpliceAI, dbNSFP not integrated
- ⚠️ **PM2 disabled**: Requires gnomAD population data
- ⚠️ **BP7 disabled**: Requires SpliceAI predictions
- ⚠️ **Test coverage**: 86% (target: 90%, industry standard)

**Not Suitable For:**
- ❌ Clinical diagnostic use
- ❌ Patient care decisions
- ❌ Regulatory submission
- ❌ Production deployment without validation

---

## 📦 Installation

### Prerequisites

- Python 3.9+ (tested on 3.9, 3.10, 3.11, 3.12)
- pip package manager
- 8GB+ RAM recommended for large VCF files

### Install from Source (Development)

```bash
# Clone the repository
git clone https://github.com/Plantucha/VariDex.git
cd VariDex

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Install test dependencies
pip install -r requirements-test.txt
```

### Verify Installation

```bash
# Set Python path
export PYTHONPATH=$(pwd):$PYTHONPATH

# Run basic tests
pytest tests/ -v

# Check coverage
pytest tests/ --cov=varidex --cov-report=term
```

**Note:** Package not yet published to PyPI. Source installation only.

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

# Create a variant (BRCA1 pathogenic example)
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
print(f"Duration: {duration:.3f}s")
```

**Expected Output:**
```
VariDex v6.4.0
Classification: Pathogenic
Confidence: High
Evidence: PVS1:1 | PP2:1
Duration: 0.003s
```

### Load ClinVar Data

```python
from varidex.io.loaders.clinvar import load_clinvar_file

# Load ClinVar VCF file (download from NCBI)
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

**Test Suite Summary:**
- **Total Tests:** **595+** across **23 modules** (45 new tests added)
- **Coverage:** **86%** → **Target: 90%** 🎯
- **Pass Rate:** 98.5%
- **Test Types:**
  - Unit tests: 385 (65%)
  - Integration tests: 110 (19%)
  - End-to-end tests: 55 (9%)
  - Coverage gap tests: 45 (7%) ✨ **NEW**

**Coverage by Module:**

| Module | Current | Target | Status |
|--------|---------|--------|--------|
| Core Models | 90% | 90% | ✅ Target met |
| ClinVar Integration | 90% | 90% | ✅ Target met |
| Core Config | 88% | 90% | 🟡 Close |
| Pipeline Orchestrator | 88% | 90% | 🟡 Close |
| User File Processing | 88% | 90% | 🟡 Close |
| **Pipeline Stages** | **86%** | **90%** | 🎯 **Targeted** |
| **ACMG Classifier** | **86%** | **90%** | 🎯 **Targeted** |
| **Integrations** | **84-86%** | **90%** | 🎯 **Targeted** |
| **Utils/Helpers** | **83%** | **90%** | 🎯 **Targeted** |
| **CLI Interface** | **83%** | **90%** | 🎯 **Targeted** |
| **Reports** | **82%** | **90%** | 🎯 **Targeted** |

### Coverage Improvement Initiative

**📈 New Test Module:** `tests/test_coverage_gaps.py` (45+ tests)

**Targets 7 modules below 90%:**
1. Pipeline stages - Error handling, edge cases
2. ACMG classifier - Missing fields, timeouts, conflicts
3. Reports generator - Format variations, special chars
4. Utils/helpers - Boundary conditions, normalization
5. CLI interface - Command validation, verbose mode
6. Integrations - Timeouts, rate limits, errors

**Why 90%?**
- ✅ Industry standard for genomics software
- ✅ ClinVar, gnomAD target 90-95%
- ✅ Production-grade quality assurance
- ✅ Achievable in 1-2 days

**See:** [COVERAGE_IMPROVEMENT_SUMMARY.md](COVERAGE_IMPROVEMENT_SUMMARY.md) for complete details.

### Run Tests

```bash
# Set Python path
export PYTHONPATH=$(pwd):$PYTHONPATH

# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=varidex --cov-report=html --cov-report=term

# Run new coverage gap tests
pytest tests/test_coverage_gaps.py -v

# Open coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux

# Run specific test module
pytest tests/test_classifier_engine.py -v

# Run with detailed output
pytest tests/ -vv --tb=short
```

### Testing Roadmap

**Short-term (1-2 days):**
- [x] Create coverage gap tests (45+ tests)
- [ ] Validate coverage increase to 90%
- [ ] Update CI/CD coverage threshold
- [ ] Merge coverage improvements

**Medium-term (1-2 weeks):**
- [ ] Add property-based testing
- [ ] Performance benchmarking
- [ ] Expand integration tests
- [ ] Test against known datasets

**Long-term (1-2 months):**
- [ ] Mutation testing
- [ ] Fuzz testing
- [ ] Clinical validation tests
- [ ] Stress testing

---

## 📄 Licensing

VariDex uses a **dual-licensing model**:

### Open Source: AGPL v3

**Free for:**
- ✅ Research and academic use
- ✅ Personal genome analysis
- ✅ Non-profit projects
- ✅ Open-source bioinformatics pipelines

**Requirements:** If you distribute or run as a network service, you must share your source code under AGPL v3.

See: [LICENSE](LICENSE)

### Commercial License

**Required for:**
- ❌ Clinical diagnostic platforms
- ❌ SaaS/cloud-based services
- ❌ Proprietary products
- ❌ Keeping modifications private

**Contact:** plantucha@gmail.com

---

## 📁 Project Structure

```
VariDex/
├── varidex/                    # Main package
│   ├── __init__.py
│   ├── version.py              # Version: v6.4.0
│   ├── exceptions.py           # 14 custom exception types
│   ├── core/                   # Core classification engine
│   │   ├── classifier/         # ACMG classifier (7/28 codes)
│   │   │   ├── engine.py       # Main classifier ✅ PRODUCTION
│   │   │   ├── engine_v7.py    # V7 🧪 EXPERIMENTAL
│   │   │   ├── engine_v8.py    # V8 🧪 EXPERIMENTAL
│   │   │   ├── VERSION_HISTORY.md  # Version documentation
│   │   │   ├── acmg_evidence_full.py  # Full implementation (WIP)
│   │   │   ├── config.py       # Configuration
│   │   │   └── rules.py        # ACMG combination rules
│   │   ├── models.py           # Data models
│   │   ├── config.py           # Global config
│   │   └── schema.py           # Data schemas
│   ├── io/                     # Input/Output
│   │   ├── loaders/            # ClinVar, VCF, 23andMe loaders
│   │   └── normalization.py    # Coordinate normalization
│   ├── reports/                # Report generation
│   ├── pipeline/               # Pipeline orchestration
│   │   ├── orchestrator.py     # Main pipeline
│   │   └── stages.py           # Pipeline stages
│   └── utils/                  # Utilities
│
├── tests/                      # Test suite (595+ tests)
│   ├── conftest.py             # Shared fixtures
│   ├── test_coverage_gaps.py   # ✨ NEW: Coverage improvement
│   ├── test_classifier_engine.py
│   ├── test_core_models.py
│   └── ...                     # 23 test modules
│
├── docs/                       # Documentation
│   ├── ACMG_28_IMPLEMENTATION_GUIDE.md
│   ├── ACMG_DATA_REQUIREMENTS.md
│   ├── TESTING.md
│   └── CI_CD_PIPELINE.md
│
├── .github/workflows/          # CI/CD (configured, pending setup)
│   ├── ci.yml                  # Main CI pipeline
│   ├── security.yml            # Security scanning
│   └── release.yml             # Release automation
│
├── COVERAGE_IMPROVEMENT_SUMMARY.md  # ✨ NEW: Coverage initiative
├── requirements.txt            # Runtime dependencies
├── requirements-test.txt       # Test dependencies
├── pytest.ini                  # Test configuration
├── mypy.ini                    # Type checking config
└── README.md                   # This file
```

---

## 📖 Documentation

### Key Documentation Files

- **[ACMG_28_IMPLEMENTATION_GUIDE.md](ACMG_28_IMPLEMENTATION_GUIDE.md)** - Full ACMG implementation guide
- **[ACMG_DATA_REQUIREMENTS.md](ACMG_DATA_REQUIREMENTS.md)** - Data requirements for evidence codes
- **[TESTING.md](TESTING.md)** - Comprehensive testing guide
- **[COVERAGE_IMPROVEMENT_SUMMARY.md](COVERAGE_IMPROVEMENT_SUMMARY.md)** - ✨ **NEW:** Coverage 86%→90%
- **[PROJECT_STATUS_SUMMARY.md](PROJECT_STATUS_SUMMARY.md)** - Detailed project status
- **[NEXT_STEPS_ACTION_PLAN.md](NEXT_STEPS_ACTION_PLAN.md)** - Development roadmap
- **[VARIDEX_CODE_STANDARDS.md](VARIDEX_CODE_STANDARDS.md)** - Coding standards
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guidelines

### Core Modules

- **`varidex.core.classifier.engine`** - Main ACMG classifier
- **`varidex.core.models`** - Data models (VariantData, ACMGEvidenceSet)
- **`varidex.io.loaders`** - Data loading utilities
- **`varidex.pipeline.orchestrator`** - Pipeline orchestration
- **`varidex.reports`** - Report generation

---

## 🤝 Contributing

We welcome contributions! VariDex is in **active development** and needs help.

### Priority Areas

1. **Validate Coverage Improvements** - Help verify 90% target
   - Run new coverage gap tests
   - Report any failures
   - Suggest additional test cases

2. **Implement Evidence Codes** - 21 remaining ACMG codes
   - PM2 (gnomAD integration)
   - BP7 (SpliceAI integration)
   - See [ACMG_28_IMPLEMENTATION_GUIDE.md](ACMG_28_IMPLEMENTATION_GUIDE.md)

3. **Improve Documentation**
   - API documentation
   - Usage examples
   - Tutorial videos

4. **Clinical Validation**
   - Test against known datasets
   - Benchmark against other tools
   - Validate ACMG compliance

### Development Setup

```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/VariDex.git
cd VariDex

# Create branch
git checkout -b feature/your-feature-name

# Install dependencies
pip install -e .
pip install -r requirements-test.txt

# Make changes and test
export PYTHONPATH=$(pwd):$PYTHONPATH
pytest tests/ -v

# Code quality checks
black varidex/ tests/
flake8 varidex/ tests/
mypy varidex/

# Submit PR
git push origin feature/your-feature-name
```

### Code Standards

- ✅ Files under 500 lines
- ✅ Type hints required
- ✅ Docstrings for all public functions
- ✅ Black formatting (88-char line length)
- ✅ Flake8 compliance
- ✅ Mypy strict mode
- ✅ Tests for new features (90%+ coverage)

See: [VARIDEX_CODE_STANDARDS.md](VARIDEX_CODE_STANDARDS.md)

---

## 📝 Citation

If you use VariDex in your research, please cite:

```bibtex
@software{varidex2026,
  title = {VariDex: Variant Data Extraction and Classification System},
  author = {VariDex Development Team},
  year = {2026},
  version = {6.4.0},
  url = {https://github.com/Plantucha/VariDex},
  note = {In development - not for clinical use}
}
```

And cite the ACMG 2015 guidelines:

```bibtex
@article{richards2015standards,
  title={Standards and guidelines for the interpretation of sequence variants},
  author={Richards, Sue and Aziz, Nazneen and Bale, Sherri and others},
  journal={Genetics in Medicine},
  volume={17},
  number={5},
  pages={405--424},
  year={2015},
  pmid={25741868}
}
```

---

## 🎯 Roadmap

### Current Focus (v6.5 - Next 1-2 weeks)

**Priority: Complete Coverage Improvement & CI/CD Setup**

- [x] Fix string formatting bugs in config.py ✅
- [x] Replace `__getattribute__` with `__getattr__` ✅
- [x] Document version fragmentation ✅
- [x] Create coverage gap tests (45+ tests) ✅
- [ ] Validate 90% coverage target 🎯
- [ ] Complete CI/CD setup (GitHub secrets)
- [ ] First beta release to Test PyPI

### Short Term (v6.6-6.9 - Q1 2026)

**Priority: Core Functionality & Testing**

- [ ] Implement PM2 evidence code (gnomAD integration)
- [ ] Implement BP7 evidence code (SpliceAI integration)
- [ ] Add 5 more evidence codes (PS1, PS2, PM1, PM5, BS2)
- [ ] Expand integration tests
- [ ] Add performance benchmarking
- [ ] Validate against ClinGen test dataset

### Medium Term (v7.0 - Q2 2026)

**Priority: Full ACMG Implementation**

- [ ] Complete all 28 evidence codes
- [ ] External database integrations (gnomAD, dbNSFP, ClinGen)
- [ ] REST API
- [ ] Web interface (basic)
- [ ] Docker deployment
- [ ] Comprehensive documentation

### Long Term (v8.0+ - Q3-Q4 2026)

**Priority: Clinical Validation & Production**

- [ ] Clinical validation with known datasets
- [ ] CLIA/CAP compliance evaluation
- [ ] Performance optimization for large-scale analysis
- [ ] Machine learning integration
- [ ] Cloud deployment options
- [ ] Database backend support
- [ ] Production release (v1.0.0)

---

## 📞 Contact & Support

- **Issues:** [GitHub Issues](https://github.com/Plantucha/VariDex/issues)
- **Discussions:** [GitHub Discussions](https://github.com/Plantucha/VariDex/discussions)
- **Email:** support@varidex.com
- **Commercial Licensing:** licensing@varidex.com

---

## ⚠️ Disclaimer

**VariDex is IN DEVELOPMENT and NOT VALIDATED for clinical diagnostic use.**

This software is provided "as is" for research and educational purposes. Current limitations:

- ❌ **Only 25% ACMG evidence code coverage** (7/28 codes)
- ❌ **Not clinically validated**
- ❌ **Missing external database integrations**
- 🟡 **Test coverage improving** (86% → 90% target)
- ✅ **Critical bugs fixed** (January 2026)

**DO NOT USE for:**
- Clinical diagnosis
- Patient care decisions
- Regulatory submissions
- Production deployment

**For clinical use:** Consult qualified genetic counselors and medical professionals. Use clinically validated tools.

---

## 🙏 Acknowledgments

- **ACMG/AMP** for the 2015 variant interpretation guidelines
- **ClinVar** database for variant data
- **gnomAD** project for population frequency data (integration pending)
- **Open-source community** for tools and libraries
- **Contributors** to this project

---

**Built for the genomics research community**

*Last updated: January 24, 2026*  
*Version: 6.4.0*  
*Status: IN DEVELOPMENT*  
*Test Coverage: 86% → 90% (in progress)*
