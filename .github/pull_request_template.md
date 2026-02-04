## Description

<!-- Provide a brief description of the changes in this PR -->

## Type of Change

<!-- Mark the relevant option with an 'x' -->

- [ ] 🐛 Bug fix (non-breaking change which fixes an issue)
- [ ] ✨ New feature (non-breaking change which adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📝 Documentation update
- [ ] 🧪 Test coverage improvement
- [ ] ♻️ Refactoring (no functional changes)
- [ ] ⚡ Performance improvement

## Related Issues

<!-- Link related issues using #issue_number -->

Closes #
Related to #

## Changes Made

<!-- List the main changes in bullet points -->

- 
- 
- 

## Testing

### Test Coverage

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] All tests passing locally
- [ ] Coverage ≥90% maintained

### Manual Testing

<!-- Describe how you tested these changes -->

```bash
# Commands used for testing

```

**Test Results:**
- [ ] Tested with Python 3.10
- [ ] Tested with Python 3.11
- [ ] Tested with Python 3.12

## Code Quality

- [ ] Code follows Black formatting (88 chars)
- [ ] Type hints added for new functions
- [ ] Docstrings added (Google style)
- [ ] No files exceed 500 lines
- [ ] All public APIs documented

### Pre-commit Checks

```bash
# Run before submitting
black --check varidex/ tests/
mypy varidex/
flake8 varidex/
pytest tests/ --cov=varidex
```

- [ ] Black formatting passed
- [ ] mypy type checking passed
- [ ] Flake8 linting passed
- [ ] All tests passed

## Security

- [ ] No sensitive data (API keys, credentials) added
- [ ] No ClinVar data files modified
- [ ] Bandit security scan passed
- [ ] Dependencies checked for vulnerabilities

## Documentation

- [ ] README updated (if needed)
- [ ] CHANGELOG updated
- [ ] Docstrings added/updated
- [ ] Code comments added for complex logic
- [ ] Examples updated (if API changed)

## Genomics-Specific

<!-- If applicable -->

- [ ] ACMG classification logic validated
- [ ] No original raw data files changed
- [ ] ClinVar data integrity maintained
- [ ] Test fixtures use small sample data
- [ ] Performance acceptable for large datasets

## Checklist

<!-- Ensure all items are completed before requesting review -->

- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published
- [ ] I have checked my code and corrected any misspellings

## CI/CD Status

<!-- Will be automatically updated by GitHub Actions -->

- [ ] Enhanced CI Pipeline passed
- [ ] Code quality checks passed
- [ ] Security scans passed
- [ ] All Python versions tested
- [ ] Build successful

## Deployment Notes

<!-- Any special instructions for deployment or release -->

**Version Impact:**
- [ ] Patch version bump (bug fixes)
- [ ] Minor version bump (new features)
- [ ] Major version bump (breaking changes)

**Deployment Checklist:**
- [ ] Migration required: No / Yes (explain below)
- [ ] Configuration changes needed: No / Yes (explain below)
- [ ] Database changes: No / Yes (explain below)

## Screenshots/Examples

<!-- If applicable, add screenshots or example output -->

```python
# Example usage

```

## Reviewer Notes

<!-- Any specific areas you'd like reviewers to focus on -->

**Focus areas:**
- 
- 

**Questions:**
- 

## Post-Merge Tasks

- [ ] Update project board
- [ ] Update release notes
- [ ] Notify team of changes
- [ ] Update documentation site

---

**Development Status:** ⚠️ Development (Not for production use)  
**Reviewer:** @Plantucha  
**Labels:** <!-- Add relevant labels: bug, enhancement, documentation, etc. -->
