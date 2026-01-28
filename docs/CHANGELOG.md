# Changelog

All notable changes to VariDex will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [6.0.0] - 2026-01-24

### Added
- Comprehensive ACMG 2015 guidelines implementation (28 evidence criteria)
- Engine v8 with computational predictions (SIFT, PolyPhen-2, CADD, REVEL)
- Engine v7 with gnomAD population frequency integration
- Engine v6 with ClinVar data integration
- Graceful degradation system across classifier engines
- Complete test suite with 95%+ coverage
- Property-based testing with Hypothesis
- CI/CD pipeline with GitHub Actions
- Security scanning with Bandit
- Type checking with mypy (strict mode)
- Black code formatting (88-character line limit)
- Commercial dual-licensing option (AGPL-3.0 / Commercial)
- Comprehensive documentation (ACMG implementation, testing guides)

### Changed
- Migrated to 88-character line limit (Black standard)
- Updated all classifier engines with type hints
- Improved error handling and graceful degradation
- Enhanced evidence assignment logic
- Optimized ClinVar data loading

### Fixed
- Bandit B310 security issue (URL scheme validation)
- Black formatting configuration mismatch
- Type checking errors in core modules
- Test coverage gaps

### Security
- Added URL scheme validation to prevent file:// exploitation
- Implemented strict type checking for critical modules
- Added dependency vulnerability scanning with Safety
- Security linting with Bandit (medium+ severity)

## [5.0.0] - 2026-01-15

### Added
- Initial ACMG classification framework
- Basic ClinVar integration
- Population frequency analysis
- Core variant models

### Changed
- Project restructured for modular design
- Improved data loading pipeline

## [4.0.0] - 2025-12-10

### Added
- Multi-file VCF support
- Batch processing capabilities

## [3.0.0] - 2025-11-01

### Added
- Basic variant classification
- ClinVar data loader

## [2.0.0] - 2025-10-01

### Added
- VCF parser
- Basic CLI interface

## [1.0.0] - 2025-09-01

### Added
- Initial release
- Basic variant data structures

---

## Version Naming Convention

- **MAJOR**: Incompatible API changes
- **MINOR**: Backward-compatible functionality additions
- **PATCH**: Backward-compatible bug fixes

## Categories

- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Vulnerability fixes
