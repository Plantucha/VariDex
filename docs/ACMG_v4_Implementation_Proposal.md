# VariDex ACMG v4 Implementation Proposal
**Version**: 7.0.0
**Date**: 2026-01-19
**Standard**: ACMG/AMP 2024 Points-Based System (Tavtigian et al. 2020)
**Target**: Replace current Richards et al. 2015 rule-based system

---

## 1. EXECUTIVE SUMMARY

### Current System (v6.0.0)
- **Standard**: ACMG 2015 Richards et al. (PMID: 25741868)
- **Method**: Rule-based combinations (e.g., "1 PVS1 + 1 PS = Pathogenic")
- **Coverage**: 7/28 evidence codes (25%)
- **Limitation**: No mathematical conflict resolution

### Proposed System (v7.0.0)
- **Standard**: ACMG/AMP 2024 Points-Based (Tavtigian et al. 2020, PMID: 32720330)
- **Method**: Additive scoring proportional to log(odds)
- **Point Scale**: Very Strong=8, Strong=4, Moderate=2, Supporting=1
- **Coverage**: Target 12/28 codes (43%) - add PM2, PP3, BP4, BS1, BS2

---

## 2. POINT SYSTEM SPECIFICATIONS

### Evidence Strength Points

| Strength | Pathogenic | Benign | Notes |
|----------|-----------|--------|-------|
| Very Strong | +8 | -8 | PVS1, BA1 |
| Strong | +4 | -4 | PS1-PS4, BS1-BS4 |
| Moderate | +2 | -2 | PM1-PM6, BM1 (new) |
| Supporting | +1 | -1 | PP1-PP5, BP1-BP7 |

### Classification Thresholds

| Classification | Point Range | Probability |
|----------------|-------------|-------------|
| Pathogenic (P) | >=10 | >0.99 |
| Likely Pathogenic (LP) | 6 to 9 | 0.90-0.99 |
| Uncertain Significance (VUS) | -1 to 5 | 0.10-0.90 |
| Likely Benign (LB) | -2 to -6 | 0.01-0.10 |
| Benign (B) | <=-7 | <0.01 |

**Formula**: `final_classification = sum(pathogenic_points) - sum(benign_points)`

---

## 3. KEY EVIDENCE CODE UPDATES

### PM2: Downgrade to Supporting (ClinGen SVI 2020)
**Current**: Moderate (2 points)
**Proposed**: Supporting (1 point)
**Reason**: Excessive weight on variant rarity; 50% of missense variants meet PM2
**Status**: Currently DISABLED - must implement with gnomAD API

### PP3/BP4: In Silico Predictors (ClinGen 2024)
**Current**: Not implemented
**Proposed**: Calibrated thresholds for REVEL, CADD, MPC, MetaSVM
**Thresholds**:
- BP4 (benign): REVEL <=0.3, CADD <20
- PP3 (pathogenic): REVEL >=0.7, CADD >=25

### BS1: High Frequency Enhancement
**Current**: Simple text matching ("high frequency")
**Proposed**: Quantitative thresholds based on disease prevalence
**Formula**: `AF_threshold = (prevalence * penetrance) / allelic_contribution`
**Example**: For rare AD disease (1/100,000), threshold = 0.001

---

## 4. IMPLEMENTATION ARCHITECTURE

### File Structure (All <600 lines)

```
varidex/
├── _version.py                     [15 lines modified]
│   └── acmg_version = "2024"
│
├── core/
│   ├── config.py                   [180 lines - add point weights]
│   │   └── EVIDENCE_POINTS = {"PVS1": 8, "PS1": 4, "PM1": 2, "PP1": 1}
│   │
│   ├── models.py                   [450 lines - add 30 lines]
│   │   └── @dataclass ACMGEvidenceSet:
│   │       └── total_points: int = 0
│   │
│   └── classifier/
│       ├── engine.py               [520 lines - replace 120 lines]
│       │   └── combine_evidence() -> calculate_points()
│       │   └── apply_acmg_2015_rules() -> REMOVED
│       │
│       └── validators.py           [200 lines - NEW FILE]
│
├── io/
│   └── gnomad_client.py            [350 lines - NEW FILE]
│       └── query_allele_frequency()
│
└── reports/
    └── generator.py                [590 lines - add 15 lines]
        └── Display point breakdown in HTML
```

### Migration Strategy: Dual-Mode Operation

**Phase 1** (v6.5.0 - Transition): Support both systems
- Add `mode` parameter: "2015" or "2024"
- Maintain backward compatibility
- Allow users to compare results

**Phase 2** (v7.0.0 - Full Switch): Default to 2024, deprecate 2015

---

## 5. DETAILED CODE MODIFICATIONS

### 5.1 Core Classification Engine (file_4a_classifier_CORE.txt)

**REMOVE** (100 lines): Current rule-based combine_evidence() method

**REPLACE WITH** (60 lines): Points-based calculation
- Define POINTS dictionary mapping codes to values
- Loop through evidence lists and sum points
- Handle PM2 downgrade (2 -> 1 point)
- Return (total_points, breakdown_dict)

**ADD** (15 lines): classify_by_points() method
- Map point total to classification thresholds
- Return (classification, confidence_level)

### 5.2 Evidence Assignment (file_4a_classifier_CORE.txt)

**NEW CRITERIA** (PM2, PP3, BP4) - 40 lines:
- **PM2**: Query gnomAD API for allele frequency
  - If AF < 0.0001 or absent: append "PM2_Supporting" (+1 point)
- **PP3**: Check in silico predictors
  - If REVEL >= 0.7: append "PP3" (+1 point)
- **BP4**: Check in silico predictors
  - If REVEL <= 0.3: append "BP4" (-1 point)

### 5.3 Configuration Updates (file_1_config.py)

**ADD** (30 lines):
- EVIDENCE_POINTS dictionary (28 codes)
- CLASSIFICATION_THRESHOLDS list
- PM2_DOWNGRADE_NOTE string
- INSILICO_THRESHOLDS dictionary (REVEL, CADD, MPC)

---

## 6. GNOMAD INTEGRATION (NEW FILE)

**File**: `varidex/io/gnomad_client.py` (350 lines)

**Purpose**: Query gnomAD v4 for population allele frequencies

**Key Components**:
- `GnomADClient` class with LRU caching
- `get_allele_frequency()` - single variant query
- `batch_query()` - bulk queries (100 variants/request)
- Error handling for API timeouts/rate limits

**API Endpoint**: https://gnomad.broadinstitute.org/api

**Caching Strategy**:
- LRU cache (10,000 variants)
- 30-day TTL for allele frequencies
- Persistent disk cache for offline use

---

## 7. TESTING REQUIREMENTS

### 7.1 Unit Tests (61 -> 95 test cases)

**New Test Cases** (34 additions):
1. `test_points_pathogenic_pvs1_ps1()` - PVS1(8) + PS1(4) = 12 -> P
2. `test_points_likely_pathogenic_threshold()` - 6 points -> LP
3. `test_conflict_resolution_points()` - PVS1(8) + BS1(-4) + BP1(-1) = 3 -> VUS
4. `test_pm2_downgrade()` - PM2 worth 1 point not 2
5. `test_benign_threshold()` - BA1(-8) -> Benign
6-34. Additional edge cases for all thresholds

### 7.2 Integration Tests

**Test File**: `tests/test_acmg_v4_integration.py`
- Compare v6.0.0 vs v7.0.0 on 1000 variants
- Expected differences: ~15-25%
- Validate against ClinVar 4-star variants

---

## 8. BACKWARD COMPATIBILITY

### 8.1 Report Format Changes

**CSV/JSON**: Add new columns
- `total_points`: Integer score
- `point_breakdown`: "PVS1:8|PS1:4"
- `acmg_version`: "2024"

**HTML**: Display point breakdown
- Visual score indicator (progress bar)
- Detailed evidence table with point values
- Threshold explanation

### 8.2 Data Persistence

- **ClinVar data**: No changes (read-only) ✓
- **User data**: No changes (read-only) ✓
- **Output files**: Backward-compatible columns ✓

---

## 9. DEPLOYMENT TIMELINE

| Phase | Version | Duration | Deliverables |
|-------|---------|----------|--------------|
| **Alpha** | v6.5.0-alpha | 2 weeks | Dual-mode classifier, unit tests |
| **Beta** | v6.5.0-beta | 2 weeks | gnomAD integration, PP3/BP4 |
| **RC** | v6.9.0 | 1 week | Full test suite, documentation |
| **Release** | v7.0.0 | - | ACMG 2024 default, deprecate 2015 |

**Total Development Time**: 5 weeks

---

## 10. RISKS & MITIGATION

### Risk 1: gnomAD API Rate Limiting
**Impact**: PM2 criterion failures (Medium)
**Mitigation**:
- Local caching with 30-day TTL
- Batch queries (100 variants/request)
- Fallback to "insufficient evidence" if API unavailable

### Risk 2: Classification Discrepancies
**Impact**: 15-25% different classifications vs v6.0.0 (High)
**Mitigation**:
- Detailed changelog mapping old -> new
- Side-by-side comparison reports
- User education materials on PM2 downgrade

### Risk 3: Increased Code Complexity
**Impact**: Harder to maintain (Low)
**Mitigation**:
- Keep files <600 lines (currently 520 -> 580 for classifier)
- Modular design (separate gnomad_client.py)
- Maintain 90%+ test coverage

---

## 11. REFERENCES

1. **Tavtigian et al. 2020**: Fitting a naturally scaled point system to the ACMG/AMP variant classification guidelines. *Hum Mutat* 41(10):1734-1737. PMID: 32720330
2. **Richards et al. 2015**: Standards and guidelines for interpretation of sequence variants. *Genet Med* 17(5):405-424. PMID: 25741868
3. **ClinGen SVI 2020**: Recommendation for Absence/Rarity (PM2) - Version 1.0
4. **ClinGen 2024**: Calibration of computational tools for PP3/BP4 criteria

---

## 12. APPENDIX: QUICK MIGRATION CHECKLIST

- [ ] Update `_version.py`: Set `acmg_version = "2024"`
- [ ] Modify `classifier/engine.py`: Replace `combine_evidence()` with `calculate_points()`
- [ ] Add `config.py`: Define `EVIDENCE_POINTS` and `CLASSIFICATION_THRESHOLDS`
- [ ] Create `io/gnomad_client.py`: Implement API client
- [ ] Update `models.py`: Add `total_points` field to `ACMGEvidenceSet`
- [ ] Extend `assign_evidence()`: Add PM2, PP3, BP4 logic
- [ ] Write 34 new unit tests for points-based system
- [ ] Update reports: Display point breakdown in HTML/JSON
- [ ] Run integration tests: Compare v6 vs v7 on 1000 variants
- [ ] Document changes: Update README and API docs

**Estimated Total Changes**: ~300 lines added, ~120 lines removed, ~50 lines modified across 8 files

---

*END OF PROPOSAL*