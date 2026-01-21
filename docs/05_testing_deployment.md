# VariDex v6.0.0 Testing & Deployment

**Document Version:** 1.0  
**Last Updated:** 2026-01-19  

Testing strategy and deployment plan for migration.

---

## Testing Strategy

### Phase 1: Unit Tests (Coverage Target: 90%)

```python
# Test file splits
pytest tests/test_loaders_clinvar.py
pytest tests/test_loaders_user.py
pytest tests/test_loaders_matching.py
pytest tests/test_reports_generator.py
pytest tests/test_reports_formatters.py
pytest tests/test_pipeline_orchestrator.py
pytest tests/test_pipeline_stages.py

# Test unchanged files
pytest tests/test_core_models.py
pytest tests/test_core_classifier.py
pytest tests/test_utils_helpers.py
```

### Phase 2: Integration Tests

```python
def test_loader_to_classifier_pipeline():
    """Test ClinVar loader → classifier integration."""
    clinvar_df = load_clinvar_file("test_data.vcf")
    results = classify_variants(clinvar_df)
    assert len(results) > 0

def test_classifier_to_report_pipeline():
    """Test classifier → report generator integration."""
    variants = classify_test_variants()
    df = create_results_dataframe(variants)
    reports = generate_all_reports(df, output_dir)
    assert reports['html'].exists()
```

### Phase 3: Security Tests

```python
# Run security test suite
pytest tests/test_security_xss.py -v
pytest tests/test_security_csv_injection.py -v
pytest tests/test_security_path_traversal.py -v
```

### Phase 4: Performance Tests

```python
def test_classification_speed():
    """Verify <5% performance impact from splits."""
    start = time.time()
    classify_1000_variants()
    duration = time.time() - start

    # Baseline: 2.5 seconds
    assert duration < 2.625  # <5% regression
```

---

## Pre-Deployment Checklist

### Code Quality

- [ ] All files ≤500 lines
- [ ] Single version (6.0.0) across all modules
- [ ] No circular imports
- [ ] Type hints on all public functions
- [ ] Docstrings on all modules/functions
- [ ] PEP 8 compliant (flake8 passing)

### Testing

- [ ] Unit tests pass (pytest -v)
- [ ] Integration tests pass
- [ ] Security tests pass
- [ ] Performance tests pass (no regression)
- [ ] Coverage ≥90% (pytest --cov)

### Security

- [ ] XSS protection verified
- [ ] CSV injection protection verified
- [ ] Path traversal protection verified
- [ ] No pickle usage (replaced with Parquet)
- [ ] Input validation comprehensive

### Documentation

- [ ] All 5 migration docs created
- [ ] README.md updated
- [ ] API documentation generated
- [ ] Changelog updated

---

## Deployment Plan

### Step 1: Staging Deployment

```bash
# Deploy to staging environment
git checkout -b migration-v6.0.0
git push origin migration-v6.0.0

# Run full test suite on staging
pytest tests/ --cov=varidex --cov-report=html

# Manual testing
python -m varidex.cli classify --clinvar test.vcf --user test.tsv
```

### Step 2: Code Review

- Security team reviews security fixes
- Architecture team reviews file splits
- QA team reviews test coverage

### Step 3: Production Deployment

```bash
# Merge to main
git checkout main
git merge migration-v6.0.0

# Tag release
git tag -a v6.0.0 -m "500-line limit + security fixes"
git push origin v6.0.0

# Deploy to PyPI
python setup.py sdist bdist_wheel
twine upload dist/*
```

### Step 4: Rollback Plan

```bash
# If issues found:
git revert v6.0.0
git tag -a v6.0.0-rollback -m "Rollback to v5.2"
git push origin v6.0.0-rollback
```

---

## Post-Deployment Verification

### Week 1: Monitor

- [ ] No error spikes in production logs
- [ ] Classification accuracy unchanged
- [ ] Performance metrics stable
- [ ] No security incidents

### Week 2: Measure

- [ ] AI generation speed improved by 16%
- [ ] Developer satisfaction survey
- [ ] Code review cycle time reduced

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| All files ≤500 lines | 100% | `wc -l` |
| Test coverage | ≥90% | pytest --cov |
| Security tests pass | 100% | pytest tests/test_security* |
| Performance regression | <5% | pytest-benchmark |
| Zero critical bugs | 0 | Production logs (Week 1) |

---

See also:
- `01_overview.md`: Success criteria
- `02_file_splits.md`: What to test
- `04_security_fixes.md`: Security test requirements
