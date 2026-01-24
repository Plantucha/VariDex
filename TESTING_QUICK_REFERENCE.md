# ⚡ VariDex Testing Quick Reference

**For Developers • Updated: January 23, 2026**

---

## 🚀 Essential Commands

### Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=varidex --cov-report=html --cov-report=term

# Run specific test file
pytest tests/test_edge_cases.py -v

# Run specific test
pytest tests/test_edge_cases.py::TestEmptyInputHandling::test_empty_dataframe -v

# Run tests matching pattern
pytest tests/ -k "edge_case" -v

# Stop on first failure
pytest tests/ -x

# Run last failed tests only
pytest tests/ --lf

# Run in parallel (if pytest-xdist installed)
pytest tests/ -n auto
```

### Code Quality Checks

```bash
# Format code with Black (88-char line limit)
black varidex/ tests/

# Check formatting without modifying
black --check --diff varidex/ tests/

# Run Flake8 linter
flake8 varidex/ tests/ --max-line-length=100

# Run mypy type checker (strict mode)
mypy varidex/ --config-file mypy.ini

# Run all quality checks
black --check varidex/ tests/ && flake8 varidex/ tests/ && mypy varidex/
```

### Security & Dependencies

```bash
# Check for known vulnerabilities
pip freeze | safety check --stdin

# Security linting with Bandit
bandit -r varidex/ -ll

# Audit packages
pip-audit

# Check outdated packages
pip list --outdated
```

---

## 📝 Pre-Commit Checklist

**Before committing code:**

```bash
# 1. Format code
black varidex/ tests/

# 2. Run linter
flake8 varidex/ tests/

# 3. Type check
mypy varidex/

# 4. Run tests
pytest tests/ -v

# 5. Check coverage (optional)
pytest tests/ --cov=varidex --cov-report=term
```

**One-liner:**
```bash
black varidex/ tests/ && flake8 varidex/ tests/ && mypy varidex/ && pytest tests/ -v
```

---

## 📊 Test Organization

### Test Types

| Category | Files | Purpose |
|----------|-------|----------|
| **Unit Tests** | Most test files | Test individual components |
| **Integration** | `test_*_integration.py` | Test component interactions |
| **E2E** | `test_integration_e2e.py` | Test complete workflows |
| **Edge Cases** | `test_edge_cases.py` | Test boundary conditions |
| **Error Recovery** | `test_error_recovery.py` | Test error handling |
| **Property-Based** | `test_property_based.py` | Generative testing |
| **Performance** | `test_performance_benchmarks.py` | Performance testing |

### Key Test Files

```
tests/
├── conftest.py                     # Shared fixtures
├── test_acmg_classification.py     # ACMG logic
├── test_cli_interface.py           # CLI testing
├── test_core_models.py             # Data models
├── test_edge_cases.py              # 🆕 Edge cases (70+ tests)
├── test_error_recovery.py          # 🆕 Error handling (50+ tests)
├── test_property_based.py          # 🆕 Property-based (40+ tests)
├── test_integration_e2e.py          # End-to-end
└── ...and 14 more test modules
```

---

## 🧪 Common Testing Scenarios

### Scenario 1: Testing a New Feature

```bash
# 1. Write test first (TDD)
vim tests/test_my_feature.py

# 2. Run test (should fail)
pytest tests/test_my_feature.py -v

# 3. Implement feature
vim varidex/my_feature.py

# 4. Run test again (should pass)
pytest tests/test_my_feature.py -v

# 5. Check coverage
pytest tests/test_my_feature.py --cov=varidex.my_feature --cov-report=term
```

### Scenario 2: Debugging a Failed Test

```bash
# Run with verbose output
pytest tests/test_failing.py -vv

# Show local variables on failure
pytest tests/test_failing.py -l

# Drop into debugger on failure
pytest tests/test_failing.py --pdb

# Show print statements
pytest tests/test_failing.py -s
```

### Scenario 3: Testing Edge Cases

```python
# Add test to test_edge_cases.py
class TestMyFeatureEdgeCases:
    def test_empty_input(self):
        """Test with empty input."""
        result = my_feature([])
        assert result is not None
    
    def test_very_large_input(self):
        """Test with large dataset."""
        large_data = ["x"] * 100000
        result = my_feature(large_data)
        assert len(result) == 100000
```

### Scenario 4: Adding Property-Based Tests

```python
# Add to test_property_based.py
from hypothesis import given
import hypothesis.strategies as st

class TestMyFeatureProperties:
    @given(st.integers(min_value=1, max_value=1000))
    def test_always_positive(self, value):
        """Result should always be positive."""
        result = my_feature(value)
        assert result > 0
```

---

## 🔧 Troubleshooting

### Common Issues

#### Issue: Tests fail on CI but pass locally

**Possible causes:**
- Different Python version
- Missing dependencies
- Platform-specific code
- Timezone differences

**Solution:**
```bash
# Test with specific Python version
pyenv local 3.11
pytest tests/ -v

# Check dependencies
pip list | grep varidex

# Test on Docker (simulate CI)
docker run -it --rm -v $(pwd):/app python:3.11 bash
cd /app && pip install -e . && pytest tests/
```

#### Issue: Flaky tests

**Symptoms:** Tests pass/fail randomly

**Common causes:**
- Race conditions
- Time-dependent code
- Improper mocking
- Shared state

**Solution:**
```python
# Use pytest-repeat to detect flakiness
pytest tests/test_flaky.py --count=10

# Add deterministic behavior
import random
random.seed(42)  # In test setup
```

#### Issue: Slow tests

**Identify slow tests:**
```bash
# Show test durations
pytest tests/ --durations=10

# Profile tests
pytest tests/ --profile
```

**Solutions:**
- Mock external APIs
- Use smaller test datasets
- Optimize fixtures
- Run in parallel

---

## 🔄 CI/CD Integration

### Workflow Overview

```
Push/PR → GitHub Actions
    │
    ├───> Code Quality (Black, Flake8, mypy)
    ├───> Tests (Python 3.9-3.12, Ubuntu/Windows/macOS)
    ├───> Security (CodeQL, Safety, Bandit)
    ├───> Coverage (Upload to Codecov)
    └───> Build (Package validation)
```

### Workflow Files

- `.github/workflows/ci.yml` - Main CI/CD
- `.github/workflows/security.yml` - Security scanning
- `.github/workflows/release.yml` - Release automation
- `.github/workflows/dependency-updates.yml` - Weekly updates

### Status Checks

**Required for merge:**
- ✅ `code-quality` - Must pass
- ✅ `test (ubuntu-latest, 3.11)` - Must pass
- ✅ `security / codeql` - Must pass

### Viewing Results

1. Go to [Actions tab](https://github.com/Plantucha/VariDex/actions)
2. Click on workflow run
3. View job details and logs
4. Download artifacts (coverage reports, etc.)

---

## 📊 Coverage Goals

### Current Status

```
Overall Coverage: 86%
Target: 90%+
```

### Check Coverage

```bash
# Generate HTML report
pytest tests/ --cov=varidex --cov-report=html
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows

# Terminal report
pytest tests/ --cov=varidex --cov-report=term-missing

# Focus on specific module
pytest tests/ --cov=varidex.core --cov-report=term
```

### Coverage Targets by Module

| Module | Current | Target |
|--------|---------|--------|
| Core Models | 90% | 95% |
| Pipeline | 88% | 95% |
| ACMG | 86% | 90% |
| Integrations | 84% | 90% |
| CLI | 83% | 85% |
| Reports | 82% | 85% |

---

## 📚 Documentation Links

| Document | Description |
|----------|-------------|
| [TESTING.md](TESTING.md) | Comprehensive testing guide |
| [TEST_SUITE_FINALIZATION_REPORT.md](TEST_SUITE_FINALIZATION_REPORT.md) | Complete test suite overview |
| [CI_CD_PIPELINE.md](docs/CI_CD_PIPELINE.md) | CI/CD workflow documentation |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution guidelines |
| [VARIDEX_CODE_STANDARDS.md](VARIDEX_CODE_STANDARDS.md) | Code quality standards |

---

## ✨ Tips & Tricks

### Faster Feedback

```bash
# Run only tests that changed
pytest tests/ --testmon

# Watch for changes and auto-run tests
pytest-watch tests/

# Run tests in parallel
pytest tests/ -n auto
```

### Better Output

```bash
# Colorful output
pytest tests/ --color=yes

# Shorter traceback
pytest tests/ --tb=short

# Show all test names
pytest tests/ -v

# Show test docstrings
pytest tests/ -v --doctest-modules
```

### Test Markers

```bash
# Run only fast tests
pytest tests/ -m "not slow"

# Run integration tests only
pytest tests/ -m integration

# Skip certain tests
pytest tests/ -m "not external_api"
```

### Fixtures

```python
# Available fixtures (from conftest.py)
pytest --fixtures tests/

# Common fixtures:
# - sample_vcf_data
# - temp_dir
# - mock_config
# - sample_variant
```

---

## 👥 Getting Help

**Documentation Issues:**
- Check [TESTING.md](TESTING.md) for detailed guides
- Review test examples in `tests/` directory

**Test Failures:**
- Check CI logs in GitHub Actions
- Run locally with `-vv` for verbose output
- Use `--pdb` to debug interactively

**Questions:**
- [GitHub Discussions](https://github.com/Plantucha/VariDex/discussions)
- [GitHub Issues](https://github.com/Plantucha/VariDex/issues)

---

## ✅ Quick Checklist

**Before submitting PR:**

- [ ] All tests pass locally: `pytest tests/ -v`
- [ ] Code formatted: `black varidex/ tests/`
- [ ] Linting passes: `flake8 varidex/ tests/`
- [ ] Type checking passes: `mypy varidex/`
- [ ] Coverage maintained/improved
- [ ] New tests added for new features
- [ ] Documentation updated if needed
- [ ] CI checks will pass (expected)

---

**Keep this card handy!** 📌

*Last updated: January 23, 2026*
