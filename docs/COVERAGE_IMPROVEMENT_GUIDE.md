# 📈 Test Coverage Improvement Guide

**Goal:** Increase VariDex test coverage from 86% to 90%+  
**Timeline:** 1-2 weeks  
**Effort:** ~4-6 hours

---

## 🎯 Current Status

### Coverage Snapshot

```
Module                          Current  Target   Gap
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
varidex/core/models.py           90%     95%     5%
varidex/core/config.py           88%     95%     7%
varidex/pipeline/orchestrator.py 88%     95%     7%
varidex/pipeline/stages.py       86%     95%     9%
varidex/acmg/classifier.py       86%     90%     4%
varidex/integrations/dbnsfp.py   86%     90%     4%
varidex/integrations/gnomad.py   84%     90%     6%
varidex/cli/interface.py         83%     85%     2%
varidex/reports/generator.py     82%     85%     3%
varidex/utils/helpers.py         83%     85%     2%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OVERALL                          86%     90%     4%
```

### Priority Areas

**High Priority** (largest impact):
1. 🔴 `pipeline/stages.py` - 9% gap
2. 🔴 `core/config.py` - 7% gap
3. 🔴 `pipeline/orchestrator.py` - 7% gap

**Medium Priority**:
4. 🟡 `integrations/gnomad.py` - 6% gap
5. 🟡 `core/models.py` - 5% gap

**Low Priority** (already good):
6. 🟢 All others - 2-4% gap

---

## 📖 Step-by-Step Workflow

### Step 1: Generate Detailed Coverage Report

```bash
# Generate HTML coverage report with missing lines
pytest tests/ --cov=varidex --cov-report=html --cov-report=term-missing

# Open in browser
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

**What to look for:**
- 🔴 Red lines = Not covered
- 🟡 Yellow lines = Partially covered (branches)
- 🟢 Green lines = Fully covered

### Step 2: Identify Untested Code

**Navigate to a module in htmlcov:**
1. Click on module name (e.g., `varidex/pipeline/stages.py`)
2. Scroll through code
3. Look for red/yellow lines
4. Identify patterns:
   - Error handling blocks (`except` clauses)
   - Edge case conditions (`if x is None`)
   - Early returns
   - Validation logic

### Step 3: Analyze Why Code Is Untested

**Common reasons:**

❓ **Error handling paths**
```python
# Example: Not tested
try:
    result = process_data(data)
except ValueError as e:  # 🔴 Never triggered in tests
    logger.error(f"Invalid data: {e}")
    return None
```

❓ **Edge cases**
```python
# Example: Not tested
if len(variants) == 0:  # 🔴 Empty case not tested
    return {"status": "no_variants"}
```

❓ **Optional parameters**
```python
# Example: Not tested
def analyze(data, config=None):
    if config is None:  # 🔴 Default case not tested
        config = get_default_config()
```

❓ **Rare conditions**
```python
# Example: Not tested
if variant.chromosome == "MT":  # 🔴 Mitochondrial not tested
    return handle_mitochondrial(variant)
```

### Step 4: Write Tests for Gaps

**Follow this pattern:**

```python
# 1. Identify untested code
# In varidex/pipeline/stages.py:
def process_variants(variants: List[Variant]) -> Dict:
    if not variants:  # 🔴 Line 45 not covered
        return {"status": "empty", "count": 0}
    # ... rest of function

# 2. Write test in tests/test_pipeline_stages.py:
class TestProcessVariants:
    def test_empty_variants_list(self):
        """Test processing with empty variant list."""
        result = process_variants([])
        
        assert result["status"] == "empty"
        assert result["count"] == 0

# 3. Run test and verify coverage improved:
pytest tests/test_pipeline_stages.py::TestProcessVariants::test_empty_variants_list -v
pytest tests/ --cov=varidex.pipeline.stages --cov-report=term
```

---

## 🔧 Coverage Improvement Strategies

### Strategy 1: Test Error Handling

**Target:** Exception handling blocks

**Example:**
```python
# Original code (varidex/integrations/gnomad.py)
def fetch_gnomad_data(variant_id: str) -> Dict:
    try:
        response = requests.get(f"{API_URL}/{variant_id}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:  # 🔴 Not covered
        logger.error("Timeout fetching gnomAD data")
        return {"error": "timeout"}
    except requests.exceptions.HTTPError:  # 🔴 Not covered
        logger.error("HTTP error fetching gnomAD data")
        return {"error": "http_error"}

# Add tests (tests/test_gnomad_integration.py)
from unittest.mock import patch
import requests

class TestGnomadErrorHandling:
    @patch("requests.get")
    def test_fetch_timeout(self, mock_get):
        """Test handling of timeout errors."""
        mock_get.side_effect = requests.exceptions.Timeout()
        
        result = fetch_gnomad_data("1-12345-A-T")
        
        assert result["error"] == "timeout"
    
    @patch("requests.get")
    def test_fetch_http_error(self, mock_get):
        """Test handling of HTTP errors."""
        mock_get.side_effect = requests.exceptions.HTTPError()
        
        result = fetch_gnomad_data("1-12345-A-T")
        
        assert result["error"] == "http_error"
```

**Impact:** +2-3% coverage per module

### Strategy 2: Test Edge Cases

**Target:** Boundary conditions and special values

**Example:**
```python
# Original code (varidex/core/models.py)
class Variant:
    def validate_position(self) -> bool:
        if self.position < 1:  # 🔴 Not covered
            return False
        if self.position > 250_000_000:  # 🔴 Not covered
            return False
        return True

# Add tests (tests/test_core_models.py)
class TestVariantValidation:
    def test_position_too_low(self):
        """Test position below minimum."""
        variant = Variant(chromosome="1", position=0)
        assert not variant.validate_position()
    
    def test_position_too_high(self):
        """Test position above maximum."""
        variant = Variant(chromosome="1", position=250_000_001)
        assert not variant.validate_position()
    
    def test_position_at_boundaries(self):
        """Test position at exact boundaries."""
        # Minimum valid
        variant = Variant(chromosome="1", position=1)
        assert variant.validate_position()
        
        # Maximum valid
        variant = Variant(chromosome="1", position=250_000_000)
        assert variant.validate_position()
```

**Impact:** +1-2% coverage per module

### Strategy 3: Test Default Parameters

**Target:** Optional parameters and defaults

**Example:**
```python
# Original code (varidex/core/config.py)
def load_config(config_file: Optional[str] = None) -> Config:
    if config_file is None:  # 🔴 Not covered
        config_file = "config/default.yaml"
    return Config.from_file(config_file)

# Add test (tests/test_core_config.py)
class TestConfigLoading:
    def test_load_with_default_path(self, tmp_path):
        """Test loading config without specifying path."""
        # Setup default config location
        default_config = tmp_path / "config" / "default.yaml"
        default_config.parent.mkdir(parents=True)
        default_config.write_text("version: 1.0")
        
        with patch("varidex.core.config.DEFAULT_PATH", str(tmp_path)):
            config = load_config()  # No argument = default
        
        assert config.version == "1.0"
```

**Impact:** +1% coverage per module

### Strategy 4: Test Conditional Branches

**Target:** If/else branches, especially with multiple conditions

**Example:**
```python
# Original code (varidex/pipeline/orchestrator.py)
def determine_priority(variant: Variant) -> str:
    if variant.clinvar_significance == "Pathogenic":
        if variant.population_frequency < 0.01:  # 🟡 Partially covered
            return "high"
        else:  # 🔴 Not covered
            return "medium"
    return "low"

# Add tests (tests/test_pipeline_orchestrator.py)
class TestPriorityDetermination:
    def test_pathogenic_rare(self):
        """Test high priority: pathogenic and rare."""
        variant = Variant(
            clinvar_significance="Pathogenic",
            population_frequency=0.005
        )
        assert determine_priority(variant) == "high"
    
    def test_pathogenic_common(self):
        """Test medium priority: pathogenic but common."""
        variant = Variant(
            clinvar_significance="Pathogenic",
            population_frequency=0.05  # > 0.01
        )
        assert determine_priority(variant) == "medium"
    
    def test_benign(self):
        """Test low priority: benign."""
        variant = Variant(clinvar_significance="Benign")
        assert determine_priority(variant) == "low"
```

**Impact:** +2% coverage per module

---

## 📝 Module-Specific Action Plans

### 1. pipeline/stages.py (86% → 95%)

**Gap:** 9% (45 lines)

**Focus areas:**
- Error handling in stage transitions
- Empty input handling
- Stage failure recovery
- Partial data processing

**Quick wins:**
```python
# Add to tests/test_pipeline_stages.py
class TestStageErrorHandling:
    def test_stage_with_empty_data(self):
        """Test stage handling of empty dataset."""
        # ...
    
    def test_stage_failure_recovery(self):
        """Test recovery from stage failure."""
        # ...
    
    def test_stage_partial_success(self):
        """Test handling of partial stage success."""
        # ...
```

### 2. core/config.py (88% → 95%)

**Gap:** 7% (28 lines)

**Focus areas:**
- Default configuration loading
- Invalid configuration handling
- Environment variable overrides
- Configuration validation

**Quick wins:**
```python
# Add to tests/test_core_config.py
class TestConfigEdgeCases:
    def test_missing_config_file(self):
        """Test handling of missing config file."""
        # ...
    
    def test_invalid_yaml_syntax(self):
        """Test handling of invalid YAML."""
        # ...
    
    def test_env_var_override(self):
        """Test environment variable override."""
        # ...
```

### 3. integrations/gnomad.py (84% → 90%)

**Gap:** 6% (24 lines)

**Focus areas:**
- API timeout handling
- Rate limiting
- Malformed response handling
- Network errors

**Quick wins:**
```python
# Add to tests/test_gnomad_integration.py
class TestGnomadResilience:
    def test_api_timeout(self):
        """Test handling of API timeouts."""
        # ...
    
    def test_rate_limit_handling(self):
        """Test rate limit backoff."""
        # ...
    
    def test_malformed_response(self):
        """Test handling of malformed JSON."""
        # ...
```

---

## ✅ Implementation Checklist

### Week 1: High Priority Modules

**Day 1-2: pipeline/stages.py**
- [ ] Generate coverage report for module
- [ ] Identify untested lines
- [ ] Write 5-8 new tests
- [ ] Verify coverage increase
- [ ] Target: 90%+

**Day 3-4: core/config.py**
- [ ] Generate coverage report for module
- [ ] Focus on error handling
- [ ] Write 4-6 new tests
- [ ] Verify coverage increase
- [ ] Target: 92%+

**Day 5: pipeline/orchestrator.py**
- [ ] Generate coverage report for module
- [ ] Test conditional branches
- [ ] Write 4-5 new tests
- [ ] Verify coverage increase
- [ ] Target: 90%+

### Week 2: Medium/Low Priority

**Day 6: integrations/**
- [ ] gnomad.py - network errors
- [ ] dbnsfp.py - data parsing
- [ ] 3-4 tests per module
- [ ] Target: 88%+ each

**Day 7: Remaining modules**
- [ ] cli/interface.py
- [ ] reports/generator.py
- [ ] utils/helpers.py
- [ ] 2-3 tests per module
- [ ] Target: 85%+ each

### Final: Verify Overall Coverage

```bash
# Generate final report
pytest tests/ --cov=varidex --cov-report=html --cov-report=term

# Should see:
# TOTAL coverage: 90%+ ✅
```

---

## 📊 Tracking Progress

### Daily Verification

```bash
# Run after adding tests
pytest tests/test_<module>.py --cov=varidex.<module> --cov-report=term

# Example:
pytest tests/test_pipeline_stages.py --cov=varidex.pipeline.stages --cov-report=term
```

### Coverage Trends

| Day | Overall | Target Module | Status |
|-----|---------|---------------|--------|
| Start | 86% | - | Baseline |
| Day 2 | 87% | pipeline/stages 90% | 🟢 On track |
| Day 4 | 88% | core/config 92% | 🟢 On track |
| Day 7 | 89% | - | 🟡 Close |
| Done | 90%+ | All modules | ✅ Complete |

---

## 🎓 Best Practices

### Do:

✅ **Focus on meaningful tests**
- Test real scenarios, not just for coverage
- Ensure tests catch actual bugs

✅ **Test error paths**
- Error handling is critical for reliability
- Often has lowest coverage

✅ **Use parametrized tests**
```python
@pytest.mark.parametrize("value,expected", [
    (0, False),
    (1, True),
    (999999, True),
    (1000000, False),
])
def test_boundaries(value, expected):
    assert validate(value) == expected
```

✅ **Test edge cases**
- Empty inputs
- None/null values
- Boundary values
- Special characters

### Don't:

❌ **Chase 100% coverage**
- Some code doesn't need tests (e.g., `__repr__`)
- Focus on critical paths
- 90-95% is excellent

❌ **Write trivial tests**
```python
# Bad: Just for coverage
def test_getter():
    obj = MyClass()
    assert obj.value == obj.value  # Meaningless
```

❌ **Skip documentation**
- Every test needs a docstring
- Explain what is being tested

---

## 💡 Quick Commands

```bash
# Full coverage report
pytest tests/ --cov=varidex --cov-report=html --cov-report=term-missing

# Specific module
pytest tests/test_<module>.py --cov=varidex.<module> --cov-report=term

# Show missing lines
pytest tests/ --cov=varidex --cov-report=term-missing

# Coverage for changed files only
pytest tests/ --cov=varidex --cov-report=term --cov-fail-under=90
```

---

## 🎯 Success Criteria

- ✅ Overall coverage: **90%+**
- ✅ Critical modules (core, pipeline): **95%+**
- ✅ Integration modules: **88%+**
- ✅ CLI/Utils: **85%+**
- ✅ All tests pass
- ✅ No trivial/meaningless tests
- ✅ All tests documented

---

**Estimated time:** 4-6 hours over 1-2 weeks  
**Difficulty:** Moderate  
**Impact:** High (better reliability, fewer bugs)

🚀 **Let's get to 90%!**
