# Contributing to VariDex

Thank you for your interest in contributing to VariDex! This document provides guidelines for contributing to this genomic variant analysis project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Standards](#code-standards)
- [Testing Requirements](#testing-requirements)
- [Submitting Changes](#submitting-changes)
- [Licensing](#licensing)

---

## Code of Conduct

Be respectful, professional, and collaborative. We're building tools for the genomics community.

---

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Git
- Basic knowledge of genomic variant analysis
- Familiarity with ACMG 2015 guidelines (recommended)

### Find an Issue

1. Check [existing issues](https://github.com/Plantucha/VariDex/issues)
2. Look for issues labeled `good first issue` or `help wanted`
3. Comment on the issue to let others know you're working on it
4. For major changes, open an issue first to discuss

---

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/VariDex.git
cd VariDex
git remote add upstream https://github.com/Plantucha/VariDex.git
```

### 2. Create Virtual Environment

```bash
# Install venv if needed
sudo apt install python3-venv python3-full  # Ubuntu/Debian

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Development Dependencies

```bash
# Install VariDex in editable mode
pip install -e .

# Install test and development dependencies
pip install -r requirements-test.txt

# Install optional development tools
pip install black flake8 mypy pre-commit
```

### 4. Verify Installation

```bash
# Run test suite
export PYTHONPATH=$(pwd):$PYTHONPATH
pytest tests/ -v

# Should see: 200+ tests passing
```

---

## Code Standards

### File Organization

- **500-Line Limit**: All Python files must be under 500 lines
- **Semantic Naming**: Use descriptive names (no `file_1.py`, `temp_2.py`)
- **Modular Design**: Split large files into logical modules

See [VARIDEX_CODE_STANDARDS.md](VARIDEX_CODE_STANDARDS.md) for complete standards.

### Python Style

- Follow **PEP 8** conventions
- Line length: **100 characters max**
- Use **type hints** for function signatures
- Add **docstrings** to all public functions/classes
- Use **meaningful variable names**

```python
# Good
def classify_variant(variant: dict, config: ACMGConfig) -> dict:
    """Classify genetic variant using ACMG 2015 guidelines.
    
    Args:
        variant: Dictionary containing variant data
        config: ACMG classification configuration
        
    Returns:
        Classification result with evidence codes
    """
    pass

# Bad
def cv(v, c):
    pass
```

### Code Quality Checks

```bash
# Format code with Black
black varidex/ tests/ --line-length 100

# Lint with flake8
flake8 varidex/ tests/ --max-line-length=100

# Type check with mypy
mypy varidex/ --ignore-missing-imports
```

---

## Testing Requirements

### Test Coverage

- **Minimum 90% coverage** for new code
- All tests must pass before submitting PR
- Add tests for bug fixes and new features

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=varidex --cov-report=html

# Run specific test file
pytest tests/test_exceptions.py -v

# Run specific test class
pytest tests/test_exceptions.py::TestExceptionHierarchy -v
```

### Writing Tests

```python
import pytest
from varidex.core.classifier import ACMGClassifier

def test_classify_pathogenic_variant():
    """Test classification of known pathogenic variant."""
    classifier = ACMGClassifier()
    variant = {
        'chromosome': '17',
        'position': 43094692,
        'ref': 'G',
        'alt': 'A',
        'gene': 'BRCA1'
    }
    result = classifier.classify(variant)
    assert result['classification'] == 'Pathogenic'
```

See [TESTING.md](TESTING.md) for comprehensive testing guidelines.

---

## Submitting Changes

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates
- `test/description` - Test additions/fixes

### Commit Messages

Follow conventional commits format:

```
type(scope): brief description

Detailed explanation of changes (optional)

Fixes #123
```

**Types:** `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`

**Examples:**
```
feat(classifier): add PM5 evidence code for missense variants

fix(loader): handle malformed VCF header lines

docs(readme): update installation instructions for Python 3.13
```

### Pull Request Process

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes and Test**
   ```bash
   # Make your changes
   pytest tests/ -v
   black varidex/ tests/
   flake8 varidex/ tests/
   ```

3. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat(scope): description"
   ```

4. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   # Create PR on GitHub
   ```

5. **PR Requirements**
   - ✅ All tests passing (CI/CD green)
   - ✅ Code coverage maintained (≥90%)
   - ✅ Code formatted with Black
   - ✅ No flake8 errors
   - ✅ Documentation updated
   - ✅ CHANGELOG.md updated (for features/fixes)
   - ✅ Linked to related issue

6. **Code Review**
   - Address reviewer feedback
   - Keep PR focused (one feature/fix per PR)
   - Update PR description if scope changes

---

## Licensing

### Dual License Agreement

By contributing, you agree that your contributions will be licensed under:
- **AGPL v3** for open source use
- **Commercial License** for commercial/clinical use

See [LICENSE](LICENSE) and [COMMERCIAL_LICENSE.md](COMMERCIAL_LICENSE.md).

### Contributor License Agreement (CLA)

For substantial contributions, you may be asked to sign a CLA confirming:
- You own the copyright to your contributions
- You grant VariDex rights to use your contributions under dual licensing

---

## Development Workflow

### Typical Contribution Flow

```bash
# 1. Update your fork
git checkout main
git pull upstream main

# 2. Create feature branch
git checkout -b feature/new-evidence-code

# 3. Develop with tests
# - Write code
# - Write tests
# - Run tests frequently
pytest tests/ -v

# 4. Format and lint
black varidex/ tests/
flake8 varidex/ tests/

# 5. Commit and push
git add .
git commit -m "feat(classifier): add PM5 evidence code"
git push origin feature/new-evidence-code

# 6. Create PR on GitHub
# 7. Respond to review feedback
# 8. Merge after approval
```

---

## Areas for Contribution

### High Priority

- **ACMG Evidence Codes**: Implement remaining 21/28 codes (see [VARIDEX_COMPLETE_ACMG_IMPLEMENTATION.md](VARIDEX_COMPLETE_ACMG_IMPLEMENTATION.md))
- **Test Coverage**: Add tests for edge cases
- **Documentation**: API documentation, tutorials, examples

### Medium Priority

- **Performance**: Optimize ClinVar loading and matching
- **File Formats**: Add BAM, CRAM support
- **Reporting**: Enhanced HTML reports with visualizations

### Good First Issues

- Fix typos in documentation
- Add example notebooks
- Improve error messages
- Add unit tests for utilities

---

## Questions?

- **GitHub Issues**: [Report bugs or request features](https://github.com/Plantucha/VariDex/issues)
- **GitHub Discussions**: [Ask questions](https://github.com/Plantucha/VariDex/discussions)
- **Email**: licensing@varidex.com (for licensing questions)

---

**Thank you for contributing to VariDex!** 🧬
