
## v7.0.0-dev (2026-02-05)

### New Features
- **PM1 Classifier**: Gene-level critical domains (3,260 variants, 18.7%)
  - UniProt SwissProt domain parsing (49,772 genes)
  - Pickle caching for instant loads
- **PM5 Classifier**: Missense at pathogenic positions (926 variants, 5.3%)
  - Indexes 183,478 pathogenic positions from ClinVar
- **PM3 Classifier**: Compound heterozygotes (3 variants)

### Bug Fixes
- Fixed position column consolidation in matching_improved.py
- Position now properly populated from position_clinvar
- All 17,448 variants have valid positions (was 1)

### Improvements
- Evidence coverage: 54.7% (up from 41.7%)
- Total working criteria: 16/28 (up from 13/28)
- Pipeline debug tracking for position values

### Statistics
- Total variants analyzed: 17,449
- Variants with evidence: 9,541 (54.7%)
- Top PM1 genes: TSC2, VWF, COL1A1, COL1A2, OTC
