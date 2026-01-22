"""
VariDex Exception Module
=========================
Custom exceptions for variant analysis pipeline.
"""

from enum import Enum
from typing import Any, Optional

__all__ = [
    "VaridexError",
    "ValidationError",
    "DataLoadError",
    "ClassificationError",
    "ReportError",
    "FileProcessingError",
    "ACMGValidationError",
    "ACMGClassificationError",
    "ACMGConfigurationError",
    "ErrorCode",
    "validate_not_none",
    "validate_not_empty",
    "validate_type",
]


class ErrorCode(Enum):
    """Error codes for categorizing exceptions."""

    VALIDATION = "VALIDATION"
    DATA_LOAD = "DATA_LOAD"
    CLASSIFICATION = "CLASSIFICATION"
    REPORT = "REPORT"
    CONFIG = "CONFIG"
    FILE_PROCESSING = "FILE_PROCESSING"


class VaridexError(Exception):
    """Base exception for all VariDex errors."""

    def __init__(
        self, message: str, code: Optional[ErrorCode] = None, context: Optional[dict] = None
    ):
        super().__init__(message)
        self.code = code
        self.context = context or {}


class ValidationError(VaridexError):
    """Raised when validation fails."""

    def __init__(self, message: str, context: Optional[dict] = None):
        super().__init__(message, ErrorCode.VALIDATION, context)


class DataLoadError(VaridexError):
    """Raised when data loading fails."""

    def __init__(self, message: str, context: Optional[dict] = None):
        super().__init__(message, ErrorCode.DATA_LOAD, context)


class ClassificationError(VaridexError):
    """Raised when variant classification fails."""

    def __init__(self, message: str, context: Optional[dict] = None):
        super().__init__(message, ErrorCode.CLASSIFICATION, context)


class ReportError(VaridexError):
    """Raised when report generation fails."""

    def __init__(self, message: str, context: Optional[dict] = None):
        super().__init__(message, ErrorCode.REPORT, context)


class FileProcessingError(VaridexError):
    """Raised when file processing fails."""

    def __init__(self, message: str, context: Optional[dict] = None):
        super().__init__(message, ErrorCode.FILE_PROCESSING, context)


# ACMG-specific exception aliases
ACMGValidationError = ValidationError
ACMGClassificationError = ClassificationError
ACMGConfigurationError = ValidationError


# Validation helper functions
def validate_not_none(value: Any, name: str) -> None:
    """Raise ValidationError if value is None."""
    if value is None:
        raise ValidationError("{name} cannot be None")


def validate_not_empty(value: Any, name: str) -> None:
    """Raise ValidationError if value is empty."""
    if not value:
        raise ValidationError("{name} cannot be empty")


def validate_type(value: Any, expected_type: type, name: str) -> None:
    """Raise ValidationError if value is not of expected type."""
    if not isinstance(value, expected_type):
        raise ValidationError(
            "{name} must be {expected_type.__name__}, got {type(value).__name__}"
        )


# Self-test
if __name__ == "__main__":
    print("=" * 70)
    print("EXCEPTIONS MODULE - Self-Test")
    print("=" * 70)

    passed = 0
    total = 14

    try:
        raise VaridexError("test")
    except VaridexError:
        print("✓ Test 1: Base VaridexError")
        passed += 1

    try:
        raise ValidationError("test", {"field": "value"})
    except ValidationError as e:
        assert e.context == {"field": "value"}
        print("✓ Test 2: ValidationError with context")
        passed += 1

    try:
        raise DataLoadError("test")
    except DataLoadError:
        print("✓ Test 3: DataLoadError")
        passed += 1

    try:
        raise ClassificationError("test")
    except ClassificationError:
        print("✓ Test 4: ClassificationError")
        passed += 1

    try:
        raise ReportError("test")
    except ReportError:
        print("✓ Test 5: ReportError")
        passed += 1

    try:
        raise FileProcessingError("test")
    except FileProcessingError:
        print("✓ Test 6: FileProcessingError")
        passed += 1

    try:
        raise ACMGValidationError("test")
    except ValidationError:
        print("✓ Test 7: ACMGValidationError alias works")
        passed += 1

    try:
        raise ACMGClassificationError("test")
    except ClassificationError:
        print("✓ Test 8: ACMGClassificationError alias works")
        passed += 1

    try:
        raise ACMGConfigurationError("test")
    except ValidationError:
        print("✓ Test 9: ACMGConfigurationError alias works")
        passed += 1

    try:
        validate_not_none(None, "test")
    except ValidationError:
        print("✓ Test 10: validate_not_none")
        passed += 1

    try:
        validate_not_empty("", "test")
    except ValidationError:
        print("✓ Test 11: validate_not_empty")
        passed += 1

    try:
        validate_type("string", int, "test")
    except ValidationError:
        print("✓ Test 12: validate_type")
        passed += 1

    assert ErrorCode.VALIDATION.value == "VALIDATION"
    assert ErrorCode.FILE_PROCESSING.value == "FILE_PROCESSING"
    print("✓ Test 13: ErrorCode enum")
    passed += 1

    for name in __all__:
        assert name in globals(), "{name} not defined"
    print("✓ Test 14: All exports defined")
    passed += 1

    print("=" * 70)
    print("Self-test: {passed}/{total} passed")
    print("✅ ALL TESTS PASSED" if passed == total else "❌ SOME TESTS FAILED")
    print("=" * 70)
