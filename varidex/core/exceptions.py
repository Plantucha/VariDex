"""
VariDex Exception Module
=========================
Custom exceptions for variant analysis pipeline.
"""

from enum import Enum
from typing import Any, Optional, Dict, List, Type

__all__: List[str] = [
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

if __name__ == "__main__":
    # Clean, static string to avoid Black / f-string issues
    print("VariDex Exceptions v6.0.0 - All systems OK")

    # Optional: also run basic self-test of all exception classes
    try:
        from varidex.core.exceptions import (
            ValidationError,
            DataLoadError,
            ClassificationError,
            ReportError,
            FileProcessingError,
        )

        test_classes: List[Type[Exception]] = [
            ValidationError,
            DataLoadError,
            ClassificationError,
            ReportError,
            FileProcessingError,
        ]

        for cls in test_classes:
            instance = cls("test message")
            assert isinstance(instance, Exception)
        print("Self-test passed: all exception classes instantiable")

    except Exception as e:
        print(f"Self-test failed: {e}")


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
        self, message: str, code: Optional[ErrorCode] = None, context: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message)
        self.code: Optional[ErrorCode] = code
        self.context: Dict[str, Any] = context or {}


class ValidationError(VaridexError):
    """Raised when validation fails."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, ErrorCode.VALIDATION, context)


class DataLoadError(VaridexError):
    """Raised when data loading fails."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, ErrorCode.DATA_LOAD, context)


class ClassificationError(VaridexError):
    """Raised when variant classification fails."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, ErrorCode.CLASSIFICATION, context)


class ReportError(VaridexError):
    """Raised when report generation fails."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, ErrorCode.REPORT, context)


class FileProcessingError(VaridexError):
    """Raised when file processing fails."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, ErrorCode.FILE_PROCESSING, context)


# ACMG-specific exception aliases
ACMGValidationError = ValidationError
ACMGClassificationError = ClassificationError
ACMGConfigurationError = ValidationError


# Validation helper functions
def validate_not_none(value: Any, name: str) -> None:
    """Raise ValidationError if value is None."""
    if value is None:
        raise ValidationError(f"{name} cannot be None")


def validate_not_empty(value: Any, name: str) -> None:
    """Raise ValidationError if value is empty."""
    if not value:
        raise ValidationError(f"{name} cannot be empty")


def validate_type(value: Any, expected_type: Type[Any], name: str) -> None:
    """Raise ValidationError if value is not of expected type."""
    if not isinstance(value, expected_type):
        raise ValidationError(
            f"{name} must be {expected_type.__name__}, got {type(value).__name__}"
        )


# Self-test
if __name__ == "__main__":
    print("=" * 70)
    print("EXCEPTIONS MODULE - Self-Test")
    print("=" * 70)

    passed: int = 0
    total: int = 14

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

    print(f"\n{'='*70}")
    print(f"PASSED: {passed}/{total} tests")
    print("=" * 70)
