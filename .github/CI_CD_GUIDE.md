# CI/CD Implementation Guide

## Overview

VariDex now has a comprehensive CI/CD pipeline using GitHub Actions. This guide explains the implementation, configuration, and usage.

## 🚀 Quick Start

All workflows are automatically triggered on push/pull requests to `main` and `develop` branches. No manual setup required to get started!

## 📊 Workflows

### 1. Enhanced CI/CD Pipeline (`ci-enhanced.yml`)

**Primary workflow for continuous integration and deployment preparation.**

#### Jobs

##### Code Quality
- **Black formatting** - Ensures all code follows PEP 8 (88 char line length)
- **isort** - Validates import sorting
- **Flake8** - Linting with genomics-friendly rules
- **mypy** - Type checking (non-blocking)

##### Security Scanning
- **Bandit** - Python security vulnerability scanner
- **Safety** - Dependency vulnerability checking
- **detect-secrets** - Prevents credential leaks

##### Matrix Testing
- Tests across **Python 3.10, 3.11, 3.12**
- Runs full test suite (745+ tests)
- **90%+ coverage requirement** enforced
- Generates coverage reports (XML, HTML, terminal)
- Uploads to Codecov for tracking

##### Integration Tests
- End-to-end pipeline validation
- Pipeline validator tests
- ClinVar integration tests

##### Build & Package
- Creates wheel and source distributions
- Validates package metadata with `twine`
- Checks wheel contents
- Uploads artifacts for release

##### Documentation
- Validates README completeness
- Checks for broken links (when docs/ exists)
- Future: Sphinx/MkDocs build validation

##### Performance Benchmarks
- Runs on pull requests
- Placeholder for pytest-benchmark tests
- Future: Variant classification speed tests

#### Status Checks

✅ **Required for merge:**
- Code Quality: Must pass
- Security: Warning only (continue-on-error)
- Tests: Must pass all Python versions
- Integration: Must pass
- Build: Must pass

### 2. Badge Generation (`badges.yml`)

**Automatically generates status badges after successful CI runs.**

#### Features
- Coverage percentage badge
- Test count badge
- Python version support badge
- Updates on every main branch push

#### Setup Required

1. **Create GitHub Gist for badges:**
   ```bash
   # Go to https://gist.github.com and create a new gist
   # Name it: varidex-badges
   # Add file: varidex-coverage.json with content: {}
   ```

2. **Create Personal Access Token:**
   ```bash
   # Go to Settings > Developer settings > Personal access tokens
   # Generate new token with 'gist' scope
   ```

3. **Add secret to repository:**
   ```bash
   # Go to repository Settings > Secrets > Actions
   # New repository secret: GIST_SECRET = <your token>
   ```

4. **Update badges.yml:**
   - Replace `YOUR_GIST_ID_HERE` with your gist ID

5. **Add badges to README:**
   ```markdown
   ![Coverage](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/USERNAME/GIST_ID/raw/varidex-coverage.json)
   ![Tests](https://github.com/Plantucha/VariDex/workflows/Enhanced%20CI%2FCD%20Pipeline/badge.svg)
   ![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)
   ```

### 3. Existing Workflows (Keep Running)

- **`ci.yml`** - Original CI (can run in parallel)
- **`test.yml`** - Focused test runner
- **`security.yml`** - Security-specific checks
- **`release.yml`** - Release automation
- **`cd.yml`** - Continuous deployment
- **`dependency-updates.yml`** - Automated dependency updates

## 🔧 Configuration

### Environment Variables

```yaml
PYTHON_VERSION_DEFAULT: "3.12"  # Primary Python version
MIN_COVERAGE: 90                 # Minimum test coverage required
```

### Caching

All workflows use pip caching to speed up builds:
```yaml
- uses: actions/setup-python@v5
  with:
    cache: 'pip'
```

### Artifacts

Workflows upload these artifacts (30-day retention):
- **mypy-report**: Type checking results
- **security-reports**: Bandit and Safety scan results
- **test-results-{version}**: JUnit XML and HTML coverage
- **dist-packages**: Built wheel and sdist files

## 🧬 Testing Locally

### Run CI Checks Before Push

```bash
# Code quality
black --check varidex/ tests/
isort --check-only varidex/ tests/
flake8 varidex/ tests/ --max-line-length=88
mypy varidex/

# Security
bandit -r varidex/
safety check
detect-secrets scan

# Tests
pytest tests/ --cov=varidex --cov-report=term

# Build
python -m build
twine check dist/*
```

### Use Pre-commit Hooks

```bash
pip install pre-commit
pre-commit install
```

Now checks run automatically on `git commit`.

## 📊 Monitoring & Reporting

### GitHub Actions Dashboard

1. Go to repository > Actions tab
2. View workflow runs
3. Click on runs to see detailed logs
4. Download artifacts for analysis

### Codecov Integration

**Setup:**
1. Go to [codecov.io](https://codecov.io)
2. Link your GitHub account
3. Enable for VariDex repository
4. Add `CODECOV_TOKEN` secret (optional but recommended)

**Features:**
- Line-by-line coverage visualization
- Pull request comments with coverage diff
- Historical coverage trends
- Coverage badges

### Coverage Reports

HTML coverage reports are uploaded as artifacts:
```bash
# Download from Actions > Workflow run > Artifacts
unzip test-results-3.12.zip
open htmlcov/index.html
```

## 🔒 Security Best Practices

### Secrets Management

**Never commit:**
- API keys
- Tokens
- Passwords
- Database credentials

**Use GitHub Secrets:**
```yaml
- uses: actions/checkout@v4
  with:
    token: ${{ secrets.MY_SECRET }}
```

### Dependency Updates

Dependabot is configured to:
- Check for updates weekly
- Create PRs for security vulnerabilities
- Update GitHub Actions versions

## ⚠️ Troubleshooting

### Tests Failing on CI but Passing Locally

**Common causes:**
1. **Python version mismatch** - CI tests 3.10, 3.11, 3.12
   ```bash
   pyenv install 3.10.13
   pyenv local 3.10.13
   pytest tests/
   ```

2. **Missing test dependencies**
   ```bash
   pip install -r requirements-test.txt
   ```

3. **File path issues** - Use `pathlib` or `os.path.join()`

4. **Timezone/locale differences** - Mock time in tests

### Coverage Below Threshold

```bash
# Generate coverage report
pytest --cov=varidex --cov-report=term-missing

# Find uncovered lines
coverage report -m

# See HTML report
coverage html && open htmlcov/index.html
```

### Black Formatting Failures

```bash
# Auto-fix formatting
black varidex/ tests/

# Check what would change
black --check --diff varidex/
```

### Security Scan Warnings

**Bandit false positives:**
```python
# Add inline comment to suppress
import pickle  # nosec B403
```

**Update .bandit config:**
```ini
[bandit]
exclude_dirs = tests/
skips = B101,B601
```

## 📝 Best Practices

### For Genomics Projects

1. **Data File Handling**
   - Never commit large VCF/BAM files
   - Use fixtures with small sample data
   - Mock external database queries

2. **ClinVar Data**
   - Don't modify original data in tests
   - Use read-only test fixtures
   - Validate data integrity

3. **Performance Testing**
   - Benchmark variant classification speed
   - Set performance regression thresholds
   - Test with realistic data sizes

4. **Version Marking**
   - Never mark as 'production' in CI
   - Always use 'dev' or version-specific tags
   - Follow semantic versioning

### Code Quality

1. **Keep files under 500 lines** (per space instructions)
2. **Black format everything** (automated)
3. **Type hints required** for public APIs
4. **Docstrings required** (Google style)
5. **Test coverage ≥90%** (enforced)

### Testing Strategy

```python
# Unit tests - Fast, isolated
tests/test_core_models.py
tests/test_acmg_classification.py

# Integration tests - Multiple components
tests/test_integration_e2e.py
tests/test_pipeline_stages.py

# E2E tests - Full workflows
tests/test_cli_interface.py
```

## 🚀 Deployment Pipeline

### Manual Release Process

1. **Update version:**
   ```bash
   # Edit varidex/version.py
   __version__ = "7.3.0-dev"
   ```

2. **Create release notes:**
   ```bash
   cp RELEASE_NOTES_v7.2.0_dev.md RELEASE_NOTES_v7.3.0_dev.md
   # Edit with changes
   ```

3. **Tag release:**
   ```bash
   git tag -a v7.3.0-dev -m "Release 7.3.0 Development"
   git push origin v7.3.0-dev
   ```

4. **GitHub automatically:**
   - Runs full CI pipeline
   - Builds packages
   - Creates GitHub release
   - Uploads artifacts

### Test PyPI Deployment

**When ready (not yet):**
```bash
# Add PYPI_TEST_TOKEN secret
# Workflow will publish to test.pypi.org
pip install -i https://test.pypi.org/simple/ varidex
```

## 📚 Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Pytest Best Practices](https://docs.pytest.org/en/stable/goodpractices.html)
- [Black Code Style](https://black.readthedocs.io/)
- [Type Checking with mypy](https://mypy.readthedocs.io/)
- [Codecov Documentation](https://docs.codecov.com/)

## 👥 Contributing

When submitting PRs:
1. All CI checks must pass
2. Coverage must remain ≥90%
3. No security vulnerabilities
4. Code must be Black-formatted
5. Update tests for new features

## 💬 Support

Issues with CI/CD?
- Check [GitHub Actions tab](https://github.com/Plantucha/VariDex/actions)
- Open issue with `ci` label
- Include workflow run link
- Attach relevant logs

---

**Version:** 1.0.0  
**Last Updated:** February 2026  
**Status:** ✅ Active Development
