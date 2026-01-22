#!/usr/bin/env python3
"""
varidex/io/validators_advanced.py - Advanced Validation Features

Extended validation features with all performance optimizations applied.
Version managed by varidex.version module.

Features: virus scanning, custom rules, validation reports, batch processing
"""
import hashlib
import datetime
import logging
from pathlib import Path
from typing import Optional, Dict, List, Callable, Any, Tuple
from functools import lru_cache
from dataclasses import dataclass, field

from varidex.version import __version__
from varidex.io.validators import ValidationResult

logger = logging.getLogger(__name__)

# ==================== VALIDATION REPORT MODEL ====================


@dataclass
class ValidationReport:
    """Comprehensive validation report. Uses __slots__ for efficiency."""

    __slots__ = ("filepath", "timestamp", "results", "overall_status")
    filepath: Path
    timestamp: datetime.datetime
    results: List[ValidationResult]
    overall_status: str

    def __init__(
        self,
        filepath: Path,
        timestamp: datetime.datetime,
        results: List[ValidationResult],
        overall_status: str,
    ):
        self.filepath = filepath
        self.timestamp = timestamp
        self.results = results
        self.overall_status = overall_status

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON export."""
        return {
            "filepath": str(self.filepath),
            "timestamp": self.timestamp.isoformat(),
            "overall_status": self.overall_status,
            "checks_passed": sum(1 for r in self.results if r.passed),
            "checks_failed": sum(1 for r in self.results if not r.passed),
            "results": [
                {
                    "check": r.check_name,
                    "passed": r.passed,
                    "message": r.message,
                    "severity": r.severity,
                    "details": r.details,
                }
                for r in self.results
            ],
        }

    def to_text(self) -> str:
        """Generate human-readable text report."""
        lines = [
            "=" * 70,
            f"VALIDATION REPORT: {self.filepath.name}",
            "=" * 70,
            f"Status: {self.overall_status.upper()}",
            f"Timestamp: {self.timestamp.isoformat()}",
            f"Checks: {sum(1 for r in self.results if r.passed)}/{len(self.results)} passed",
            "",
            "DETAILS:",
            "-" * 70,
        ]

        for result in self.results:
            symbol = "✓" if result.passed else "✗"
            lines.append(f"{symbol} {result.check_name}: {result.message}")
            if result.details:
                for key, val in result.details.items():
                    lines.append(f"   {key}: {val}")

        lines.append("=" * 70)
        return "\n".join(lines)


# ==================== CUSTOM VALIDATION RULES ====================

_CUSTOM_RULES: Dict[str, Callable[[Path], ValidationResult]] = {}


def add_custom_rule(name: str, validator: Callable[[Path], ValidationResult]):
    """Register a custom validation rule."""
    _CUSTOM_RULES[name] = validator
    logger.debug(f"Registered custom rule: {name}")


def remove_custom_rule(name: str) -> bool:
    """Unregister a custom validation rule."""
    if name in _CUSTOM_RULES:
        del _CUSTOM_RULES[name]
        logger.debug(f"Removed custom rule: {name}")
        return True
    return False


def get_custom_rules() -> Dict[str, Callable]:
    """Get all registered custom rules."""
    return _CUSTOM_RULES.copy()


def clear_custom_rules():
    """Clear all custom validation rules."""
    _CUSTOM_RULES.clear()
    logger.debug("Cleared all custom rules")


# ==================== VIRUS SCANNING HOOK ====================

_VIRUS_SCANNER: Optional[Callable[[Path], Tuple[bool, str]]] = None


def set_virus_scanner(scanner: Callable[[Path], Tuple[bool, str]]):
    """Register a virus scanning function."""
    global _VIRUS_SCANNER
    _VIRUS_SCANNER = scanner
    logger.info("Virus scanner registered")


def remove_virus_scanner():
    """Unregister the virus scanner."""
    global _VIRUS_SCANNER
    _VIRUS_SCANNER = None
    logger.info("Virus scanner removed")


def scan_for_viruses(filepath: Path) -> ValidationResult:
    """Scan file for viruses if scanner configured."""
    if _VIRUS_SCANNER is None:
        return ValidationResult(
            True, "virus_scan", "No virus scanner configured (optional)", "info"
        )

    try:
        is_clean, message = _VIRUS_SCANNER(filepath)
        return ValidationResult(
            is_clean,
            "virus_scan",
            message,
            "error" if not is_clean else "info",
            {"scanner_active": True},
        )
    except (OSError, RuntimeError) as e:
        return ValidationResult(
            False, "virus_scan", f"Virus scan error: {e}", "warning", {"error": str(e)}
        )


# ==================== OPTIMIZED VALIDATION CACHING ====================


@lru_cache(maxsize=256)
def _file_identity(filepath_str: str, mtime: float, size: int) -> str:
    """Create cache key from file identity."""
    return f"{filepath_str}:{mtime}:{size}"


@lru_cache(maxsize=256)
def _cached_content_validation(filepath_str: str, mtime: float, size: int) -> bool:
    """Cached content type validation result."""
    from varidex.io.validators import validate_content_type

    return validate_content_type(Path(filepath_str)).passed


@lru_cache(maxsize=256)
def _cached_encoding_validation(filepath_str: str, mtime: float, size: int) -> bool:
    """Cached encoding validation result."""
    from varidex.io.validators import validate_encoding

    return validate_encoding(Path(filepath_str)).passed


def validate_with_cache(
    filepath: Path, validation_func: Callable[[Path], ValidationResult]
) -> ValidationResult:
    """Validate with automatic caching. Optimized: single LRU layer."""
    if not filepath.exists():
        return validation_func(filepath)

    try:
        stat = filepath.stat()
        cache_key = _file_identity(str(filepath), stat.st_mtime, stat.st_size)

        func_name = validation_func.__name__

        if func_name == "validate_content_type":
            passed = _cached_content_validation(str(filepath), stat.st_mtime, stat.st_size)
            return ValidationResult(
                passed,
                "content_type",
                "Cached result" if passed else "Failed",
                "info" if passed else "error",
            )
        elif func_name == "validate_encoding":
            passed = _cached_encoding_validation(str(filepath), stat.st_mtime, stat.st_size)
            return ValidationResult(
                passed,
                "encoding",
                "Cached result" if passed else "Failed",
                "info" if passed else "error",
            )
        else:
            return validation_func(filepath)

    except (OSError, PermissionError) as e:
        logger.warning(f"Caching error for {filepath.name}: {e}")
        return validation_func(filepath)


def clear_validation_cache():
    """Clear all validation caches."""
    _cached_content_validation.cache_clear()
    _cached_encoding_validation.cache_clear()
    _file_identity.cache_clear()
    logger.debug("Validation cache cleared")


def get_cache_stats() -> Dict[str, Any]:
    """Get validation cache statistics."""
    return {
        "content_cache": _cached_content_validation.cache_info()._asdict(),
        "encoding_cache": _cached_encoding_validation.cache_info()._asdict(),
        "identity_cache": _file_identity.cache_info()._asdict(),
    }


# ==================== COMPREHENSIVE VALIDATION REPORT GENERATOR ====================


def generate_validation_report(
    filepath: Path,
    include_optional: bool = True,
    custom_checks: bool = True,
    use_cache: bool = True,
) -> ValidationReport:
    """Generate comprehensive validation report. Optimized: optional caching."""
    from varidex.io.validators import (
        validate_content_type,
        validate_encoding,
        validate_permissions,
        validate_parent_symlinks,
    )

    results = []

    if use_cache:
        results.append(validate_with_cache(filepath, validate_content_type))
        results.append(validate_with_cache(filepath, validate_encoding))
    else:
        results.append(validate_content_type(filepath))
        results.append(validate_encoding(filepath))

    results.append(validate_permissions(filepath))
    results.append(validate_parent_symlinks(filepath))

    if include_optional:
        results.append(scan_for_viruses(filepath))

    if custom_checks:
        for rule_name, rule_func in _CUSTOM_RULES.items():
            try:
                results.append(rule_func(filepath))
            except (ValueError, OSError, RuntimeError) as e:
                results.append(
                    ValidationResult(
                        False, rule_name, f"Custom rule error: {e}", "error", {"error": str(e)}
                    )
                )

    errors = sum(1 for r in results if not r.passed and r.severity == "error")
    warnings = sum(1 for r in results if not r.passed and r.severity == "warning")

    overall = "failed" if errors > 0 else "warning" if warnings > 0 else "passed"

    return ValidationReport(
        filepath=filepath,
        timestamp=datetime.datetime.now(),
        results=results,
        overall_status=overall,
    )


def batch_validate(
    filepaths: List[Path], parallel: bool = False, **kwargs
) -> List[ValidationReport]:
    """Validate multiple files. Optimized: optional parallel processing."""
    reports = []

    if parallel:
        logger.warning("Parallel processing not yet implemented, using sequential")

    for filepath in filepaths:
        try:
            report = generate_validation_report(filepath, **kwargs)
            reports.append(report)
        except (ValueError, OSError) as e:
            logger.error(f"Error validating {filepath}: {e}")
            reports.append(
                ValidationReport(
                    filepath=filepath,
                    timestamp=datetime.datetime.now(),
                    results=[
                        ValidationResult(
                            False, "batch_validation", f"Validation error: {e}", "error"
                        )
                    ],
                    overall_status="failed",
                )
            )

    return reports


def export_reports(
    reports: List[ValidationReport], output_path: Path, format: str = "json"
) -> bool:
    """Export validation reports to file. Optimized: supports JSON/text."""
    try:
        if format == "json":
            import json

            with open(output_path, "w") as f:
                json.dump([r.to_dict() for r in reports], f, indent=2)
        elif format == "text":
            with open(output_path, "w") as f:
                for report in reports:
                    f.write(report.to_text() + "\n\n")
        else:
            raise ValueError(f"Unsupported format: {format}")

        logger.info(f"Exported {len(reports)} reports to {output_path}")
        return True

    except (OSError, ValueError) as e:
        logger.error(f"Export failed: {e}")
        return False


# ==================== SELF-TEST ====================

if __name__ == "__main__":
    import tempfile
    import json

    print("=" * 70)
    print(f"VALIDATORS ADVANCED v{__version__} - Self-Test")
    print("=" * 70)

    tests_passed = 0
    tests_total = 7

    try:

        def custom_rule(p: Path) -> ValidationResult:
            return ValidationResult(True, "custom", "OK", "info")

        add_custom_rule("test", custom_rule)
        assert "test" in get_custom_rules()
        remove_custom_rule("test")
        print("✓ Test 1: Custom validation rules")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 1: {e}")

    try:

        def mock_scanner(p: Path) -> Tuple[bool, str]:
            return (True, "Clean")

        set_virus_scanner(mock_scanner)
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test")
            tmp_path = Path(tmp.name)
        result = scan_for_viruses(tmp_path)
        assert result.passed
        tmp_path.unlink()
        remove_virus_scanner()
        print("✓ Test 2: Virus scanning hook")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 2: {e}")

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w") as tmp:
            tmp.write("cache test")
            tmp_path = Path(tmp.name)

        from varidex.io.validators import validate_encoding

        result1 = validate_with_cache(tmp_path, validate_encoding)
        result2 = validate_with_cache(tmp_path, validate_encoding)
        assert result1.passed and result2.passed

        stats = get_cache_stats()
        assert "encoding_cache" in stats

        clear_validation_cache()
        tmp_path.unlink()
        print("✓ Test 3: Optimized caching")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 3: {e}")

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w") as tmp:
            tmp.write("test")
            tmp_path = Path(tmp.name)

        report = generate_validation_report(tmp_path, include_optional=False)
        assert isinstance(report, ValidationReport)
        assert report.overall_status in ["passed", "failed", "warning"]

        tmp_path.unlink()
        print("✓ Test 4: Report generation")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 4: {e}")

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w") as tmp:
            tmp.write("test")
            tmp_path = Path(tmp.name)

        report = generate_validation_report(tmp_path, include_optional=False)

        report_dict = report.to_dict()
        assert "overall_status" in report_dict

        report_text = report.to_text()
        assert "VALIDATION REPORT" in report_text

        tmp_path.unlink()
        print("✓ Test 5: Report formats")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 5: {e}")

    try:
        temp_files = []
        for i in range(3):
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w")
            tmp.write(f"test {i}")
            temp_files.append(Path(tmp.name))
            tmp.close()

        reports = batch_validate(temp_files, include_optional=False, use_cache=True)
        assert len(reports) == 3

        for tmp_path in temp_files:
            tmp_path.unlink()

        print("✓ Test 6: Batch validation")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 6: {e}")

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w") as tmp:
            tmp.write("export test")
            tmp_path = Path(tmp.name)

        report = generate_validation_report(tmp_path, include_optional=False)

        output_json = Path(tempfile.gettempdir()) / "test_report.json"
        output_text = Path(tempfile.gettempdir()) / "test_report.txt"

        assert export_reports([report], output_json, format="json")
        assert export_reports([report], output_text, format="text")

        output_json.unlink()
        output_text.unlink()
        tmp_path.unlink()

        print("✓ Test 7: Report export")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 7: {e}")

    print("=" * 70)
    print(f"Self-test: {tests_passed}/{tests_total} passed")
    score = 10.0 if tests_passed == tests_total else (tests_passed / tests_total) * 10
    print(f"Score: {score:.1f}/10 {'✅' if score >= 10.0 else '⚠️'}")
    print("=" * 70)
