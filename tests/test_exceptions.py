"""
Complete tests for exception hierarchy.
Target: 100% coverage of varidex/exceptions.py
"""

import pytest
from typing import Type, Any
from varidex.exceptions import (
    VaridexError,
    ValidationError,
    DataLoadError,
    ClassificationError,
    ReportError,
    FileProcessingError,
    ACMGValidationError,
    ACMGClassificationError,
    ACMGConfigurationError,
    ErrorCode,
    validate_not_none,
    validate_not_empty,
    validate_type,
)

pytestmark = pytest.mark.unit

EXCEPTION_CLASSES = [
    (ValidationError, ErrorCode.VALIDATION),
    (DataLoadError, ErrorCode.DATA_LOAD),
    (ClassificationError, ErrorCode.CLASSIFICATION),
    (ReportError, ErrorCode.REPORT),
    (FileProcessingError, ErrorCode.FILE_PROCESSING),
]

EMPTY_VALUES = [("", "empty string"), ([], "empty list"), ({}, "empty dict")]


@pytest.mark.smoke
class TestExceptionHierarchy:
    """Test exception class hierarchy."""

    def test_base_exception_class(self):
        err = VaridexError("Base error")
        assert str(err) == "Base error"
        assert isinstance(err, Exception)

    @pytest.mark.parametrize("exc_class,expected_code", EXCEPTION_CLASSES)
    def test_exception_inheritance_and_error_code(self, exc_class, expected_code):
        err = exc_class("Test error")
        assert isinstance(err, VaridexError)
        assert err.code == expected_code


class TestValidationHelpers:
    """Test validation helper functions."""

    @pytest.mark.parametrize("value", ["string", 0, [], {}, False])
    def test_validate_not_none_pass(self, value):
        validate_not_none(value, "test_field")

    def test_validate_not_none_fail(self):
        with pytest.raises(ValidationError) as exc:
            validate_not_none(None, "test_field")
        assert "test_field" in str(exc.value)

    @pytest.mark.parametrize("empty_value,description", EMPTY_VALUES)
    def test_validate_not_empty_fail(self, empty_value, description):
        with pytest.raises(ValidationError):
            validate_not_empty(empty_value, "test_field")
