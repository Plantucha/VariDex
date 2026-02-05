
## [8.2.6] - 2026-01-31 (Development)

### Added
- **Genomic coordinate liftover utility** (`varidex/utils/liftover.py`)
  - Bidirectional conversion: GRCh37 ↔ GRCh38
  - Progress tracking for large datasets (600K+ variants)
  - Automatic UCSC chain file download via pyliftover
  - Successfully tested with 601,842 variants (99.1% success rate)
  - Command-line interface with flexible options

### Changed
- Updated `.gitignore` to protect sensitive genomic data files
- Improved `orchestrator.py` compatibility with lifted coordinate files

### Testing
- ✅ Processed 601,842 raw variants → 596,682 lifted (99.1%)
- ✅ Pipeline integration: 24,966 ClinVar matches, 2,482 pathogenic variants
- ✅ Black-formatted, PEP 8 compliant (88-char lines)

### Dependencies
- Added: `pyliftover>=0.4.1` for coordinate conversion

