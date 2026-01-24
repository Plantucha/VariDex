"""
VariDex Exception Module
=========================
Custom exceptions for variant analysis pipeline.
"""

from enum import Enum
from typing import Any, Optional, Dict, List, Type, Tuple

__version__: str = "6.0.0"

__all__: List[str] = [
    "VaridexError",
    "VariDexError",
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
        self,
        message: str,
        code: Optional[ErrorCode] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code: Optional[ErrorCode] = code
        self.context: Dict[str, Any] = context or {}


# Backward compatibility alias (CamelCase variant)
VariDexError = VaridexError


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


# ACMG-specific aliases
ACMGValidationError = ValidationError
ACMGClassificationError = ClassificationError
ACMGConfigurationError = ValidationError


# --------------------------
# Validation helper functions
# --------------------------
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


if __name__ == "__main__":
    """Self-test: verify all exception classes can be instantiated."""
    print(f"VariDex Exceptions v{__version__} - All systems OK")

    # Test all exception classes
    exception_classes: List[Tuple[Type[Exception], str]] = [
        (VaridexError, "Base error"),
        (VariDexError, "Base error (CamelCase alias)"),
        (ValidationError, "Validation failed"),
        (DataLoadError, "Data load failed"),
        (ClassificationError, "Classification failed"),
        (ReportError, "Report generation failed"),
        (FileProcessingError, "File processing failed"),
        (ACMGValidationError, "ACMG validation failed"),
        (ACMGClassificationError, "ACMG classification failed"),
        (ACMGConfigurationError, "ACMG configuration failed"),
    ]

    try:
        for exc_class, test_msg in exception_classes:
            exc = exc_class(test_msg)
            assert isinstance(exc, Exception), f"{exc_class.__name__} is not an Exception"

        # Verify alias works
        assert VariDexError is VaridexError, "VariDexError alias broken"

        # Test validation helpers
        try:
            validate_not_none(None, "test_value")
            raise AssertionError("validate_not_none should have raised ValidationError")
        except ValidationError:
            pass

        try:
            validate_not_empty("", "test_value")
            raise AssertionError("validate_not_empty should have raised ValidationError")
        except ValidationError:
            pass

        try:
            validate_type("string", int, "test_value")
            raise AssertionError("validate_type should have raised ValidationError")
        except ValidationError:
            pass

        print("Self-test passed: all exception classes instantiable")
        exit(0)
    except Exception as e:
        print(f"Self-test FAILED: {e}")
        exit(1)
