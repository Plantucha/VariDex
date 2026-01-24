# Contributing to VariDex

Thank you for your interest in contributing to VariDex! This document provides guidelines for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Standards](#code-standards)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Licensing](#licensing)

## Code of Conduct

Please be respectful and constructive in all interactions. We're building a professional tool for genomic analysis.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/VariDex.git
   cd VariDex
   ```
3. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Setup

### Prerequisites

- Python 3.9 or higher
- pip and setuptools
- Git

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e .
pip install -r requirements-test.txt

# Install pre-commit hooks (optional)
pip install pre-commit
pre-commit install
```

## Code Standards

### Code Formatting

- **Black** for code formatting (88-character line limit)
- **Flake8** for style checking
- **mypy** for type checking

```bash
# Format code
black varidex/ tests/

# Check formatting
black --check varidex/ tests/

# Run linter
flake8 varidex/ tests/

# Type check
mypy varidex/
```

### Code Style Guidelines

1. **Type Hints**: All new functions must have type hints
2. **Docstrings**: Use Google-style docstrings for all public functions
3. **Line Length**: Maximum 88 characters (Black standard)
4. **Imports**: Organize imports alphabetically, standard library first
5. **Naming**:
   - Classes: `PascalCase`
   - Functions/variables: `snake_case`
   - Constants: `UPPER_SNAKE_CASE`

### Example Function

```python
def classify_variant(
    variant: Variant,
    evidence: Dict[str, Any],
    config: ClassifierConfig,
) -> ClassificationResult:
    """Classify a variant using ACMG guidelines.
    
    Args:
        variant: Variant to classify
        evidence: Dictionary of evidence criteria
        config: Classifier configuration
        
    Returns:
        Classification result with pathogenicity and evidence
        
    Raises:
        ValidationError: If variant data is invalid
    """
    # Implementation here
    pass
```

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=varidex --cov-report=term --cov-report=html

# Run specific test file
pytest tests/test_classifier.py

# Run specific test
pytest tests/test_classifier.py::test_variant_classification
```

### Writing Tests

1. **Location**: Place tests in `tests/` directory
2. **Naming**: Test files must start with `test_`
3. **Coverage**: Aim for 90%+ coverage for new code
4. **Types of Tests**:
   - Unit tests (fast, isolated)
   - Integration tests (with markers)
   - Property-based tests (Hypothesis)

### Test Example

```python
import pytest
from varidex.core.classifier import ACMGClassifier

def test_pathogenic_classification():
    """Test classification of known pathogenic variant."""
    classifier = ACMGClassifier()
    variant = create_test_variant("pathogenic")
    result = classifier.classify(variant)
    assert result.classification == "Pathogenic"
    assert "PVS1" in result.evidence
```

## Submitting Changes

### Before Submitting

1. **Run all tests**: `pytest tests/`
2. **Check formatting**: `black --check varidex/ tests/`
3. **Check types**: `mypy varidex/`
4. **Update documentation** if needed
5. **Add tests** for new features

### Pull Request Process

1. **Push your branch** to your fork
2. **Create a Pull Request** on GitHub
3. **Fill out the PR template** completely
4. **Wait for CI/CD checks** to pass
5. **Respond to review feedback**

### PR Title Format

```
<type>: <description>

Types:
- feat: New feature
- fix: Bug fix
- docs: Documentation changes
- test: Test additions/changes
- refactor: Code restructuring
- perf: Performance improvements
- ci: CI/CD changes
```

### Examples

- `feat: Add PP3 computational prediction criteria`
- `fix: Correct gnomAD allele frequency threshold`
- `docs: Update ACMG implementation guide`
- `test: Add edge case tests for ClinVar loader`

## Licensing

By contributing to VariDex, you agree that your contributions will be licensed under:

- **AGPL-3.0-or-later** for open-source use
- Available under **Commercial License** for proprietary use

See [LICENSE](LICENSE) and [COMMERCIAL_LICENSE.md](COMMERCIAL_LICENSE.md) for details.

### Contributor License Agreement (CLA)

For significant contributions, you may be asked to sign a CLA to ensure:
- Your right to contribute the code
- Our right to distribute your contributions under our dual license

## Questions?

If you have questions about contributing:

1. Check existing [Issues](https://github.com/Plantucha/VariDex/issues)
2. Review project [Documentation](README.md)
3. Open a new issue with the `question` label

## Development Workflow Summary

```bash
# 1. Setup
git checkout -b feature/my-feature
pip install -e .
pip install -r requirements-test.txt

# 2. Develop
# ... write code ...

# 3. Format & Check
black varidex/ tests/
flake8 varidex/ tests/
mypy varidex/

# 4. Test
pytest tests/ --cov=varidex

# 5. Commit & Push
git add .
git commit -m "feat: Add new feature"
git push origin feature/my-feature

# 6. Create PR on GitHub
```

---

**Thank you for contributing to VariDex!** 🧬
