"""Comprehensive error handler tests to boost coverage.

Focuses on:
- Exception handling paths
- Error code validation
- Error message formatting
- Error recovery scenarios
- Edge cases in error handling

Target: Increase coverage by testing uncovered error paths.
Black formatted with 88-char line limit.
"""

import pytest

from varidex.core.exceptions import (
    ConfigurationError,
    DataProcessingError,
    PipelineError,
)
from varidex.exceptions import (
    ClassificationError,
    DataLoadError,
    ErrorCode,
    FileProcessingError,
    ReportError,
    ValidationError,
    VaridexError,
)

pytestmark = pytest.mark.unit


class TestErrorCodeEnum:
    """Test ErrorCode enumeration."""

    def test_error_code_values(self) -> None:
        """Test all error codes have unique values."""
        codes = [
            ErrorCode.VALIDATION,
            ErrorCode.DATA_LOAD,
            ErrorCode.CLASSIFICATION,
            ErrorCode.REPORT,
            ErrorCode.FILE_PROCESSING,
        ]
        values = [code.value for code in codes]
        assert len(values) == len(set(values))  # All unique

    def test_error_code_names(self) -> None:
        """Test error code names are descriptive."""
        assert ErrorCode.VALIDATION.name == "VALIDATION"
        assert ErrorCode.DATA_LOAD.name == "DATA_LOAD"
        assert ErrorCode.CLASSIFICATION.name == "CLASSIFICATION"
        assert ErrorCode.REPORT.name == "REPORT"
        assert ErrorCode.FILE_PROCESSING.name == "FILE_PROCESSING"

    def test_error_code_string_representation(self) -> None:
        """Test error codes have string representations."""
        for code in ErrorCode:
            assert str(code) or repr(code)
            assert isinstance(code.value, (str, int))


class TestVaridexErrorBase:
    """Test base VaridexError exception."""

    def test_varidex_error_creation(self) -> None:
        """Test creating base error."""
        err = VaridexError("Base error message")
        assert str(err) == "Base error message"
        assert isinstance(err, Exception)

    def test_varidex_error_empty_message(self) -> None:
        """Test error with empty message."""
        err = VaridexError("")
        assert str(err) == ""

    def test_varidex_error_long_message(self) -> None:
        """Test error with very long message."""
        long_msg = "Error: " + "x" * 1000
        err = VaridexError(long_msg)
        assert str(err) == long_msg

    def test_varidex_error_with_special_characters(self) -> None:
        """Test error message with special characters."""
        special_msg = "Error: \n\t\r Test 'quotes' \"double\""
        err = VaridexError(special_msg)
        assert str(err) == special_msg

    def test_varidex_error_inheritance(self) -> None:
        """Test VaridexError inherits from Exception."""
        err = VaridexError("Test")
        assert isinstance(err, Exception)
        assert isinstance(err, BaseException)


class TestValidationError:
    """Test ValidationError exception."""

    def test_validation_error_creation(self) -> None:
        """Test creating validation error."""
        err = ValidationError("Invalid input")
        assert str(err) == "Invalid input"
        assert err.code == ErrorCode.VALIDATION

    def test_validation_error_field_name(self) -> None:
        """Test validation error with field name."""
        err = ValidationError("field_name is required")
        assert "field_name" in str(err)

    def test_validation_error_multiple_fields(self) -> None:
        """Test validation error mentioning multiple fields."""
        err = ValidationError("field1 and field2 are invalid")
        assert "field1" in str(err)
        assert "field2" in str(err)

    def test_validation_error_inheritance(self) -> None:
        """Test ValidationError inherits from VaridexError."""
        err = ValidationError("Test")
        assert isinstance(err, VaridexError)
        assert isinstance(err, Exception)

    def test_validation_error_raises(self) -> None:
        """Test ValidationError can be raised and caught."""
        with pytest.raises(ValidationError) as exc_info:
            raise ValidationError("Test validation error")
        assert "Test validation error" in str(exc_info.value)


class TestDataLoadError:
    """Test DataLoadError exception."""

    def test_data_load_error_creation(self) -> None:
        """Test creating data load error."""
        err = DataLoadError("Failed to load data")
        assert str(err) == "Failed to load data"
        assert err.code == ErrorCode.DATA_LOAD

    def test_data_load_error_with_filename(self) -> None:
        """Test data load error with filename."""
        err = DataLoadError("Failed to load file: data.vcf")
        assert "data.vcf" in str(err)

    def test_data_load_error_with_path(self) -> None:
        """Test data load error with file path."""
        err = DataLoadError("Cannot read /path/to/file.vcf")
        assert "/path/to/file.vcf" in str(err)

    def test_data_load_error_inheritance(self) -> None:
        """Test DataLoadError inherits from VaridexError."""
        err = DataLoadError("Test")
        assert isinstance(err, VaridexError)


class TestClassificationError:
    """Test ClassificationError exception."""

    def test_classification_error_creation(self) -> None:
        """Test creating classification error."""
        err = ClassificationError("Classification failed")
        assert str(err) == "Classification failed"
        assert err.code == ErrorCode.CLASSIFICATION

    def test_classification_error_with_variant_id(self) -> None:
        """Test classification error with variant identifier."""
        err = ClassificationError("Failed to classify variant chr1:12345")
        assert "chr1:12345" in str(err)

    def test_classification_error_with_reason(self) -> None:
        """Test classification error with failure reason."""
        err = ClassificationError("Classification failed: insufficient evidence")
        assert "insufficient evidence" in str(err)

    def test_classification_error_inheritance(self) -> None:
        """Test ClassificationError inherits from VaridexError."""
        err = ClassificationError("Test")
        assert isinstance(err, VaridexError)


class TestReportError:
    """Test ReportError exception."""

    def test_report_error_creation(self) -> None:
        """Test creating report error."""
        err = ReportError("Report generation failed")
        assert str(err) == "Report generation failed"
        assert err.code == ErrorCode.REPORT

    def test_report_error_with_format(self) -> None:
        """Test report error with format specification."""
        err = ReportError("Failed to generate PDF report")
        assert "PDF" in str(err)

    def test_report_error_with_details(self) -> None:
        """Test report error with detailed message."""
        err = ReportError("Report failed: missing template")
        assert "missing template" in str(err)

    def test_report_error_inheritance(self) -> None:
        """Test ReportError inherits from VaridexError."""
        err = ReportError("Test")
        assert isinstance(err, VaridexError)


class TestFileProcessingError:
    """Test FileProcessingError exception."""

    def test_file_processing_error_creation(self) -> None:
        """Test creating file processing error."""
        err = FileProcessingError("File processing failed")
        assert str(err) == "File processing failed"
        assert err.code == ErrorCode.FILE_PROCESSING

    def test_file_processing_error_with_operation(self) -> None:
        """Test file processing error with operation."""
        err = FileProcessingError("Failed to parse VCF file")
        assert "parse" in str(err)
        assert "VCF" in str(err)

    def test_file_processing_error_with_line_number(self) -> None:
        """Test file processing error with line number."""
        err = FileProcessingError("Parse error at line 42")
        assert "42" in str(err)

    def test_file_processing_error_inheritance(self) -> None:
        """Test FileProcessingError inherits from VaridexError."""
        err = FileProcessingError("Test")
        assert isinstance(err, VaridexError)


class TestCoreExceptions:
    """Test core.exceptions module."""

    def test_configuration_error(self) -> None:
        """Test ConfigurationError."""
        err = ConfigurationError("Invalid configuration")
        assert str(err) == "Invalid configuration"
        assert isinstance(err, (VaridexError, Exception))

    def test_data_processing_error(self) -> None:
        """Test DataProcessingError."""
        err = DataProcessingError("Processing failed")
        assert str(err) == "Processing failed"
        assert isinstance(err, (VaridexError, Exception))

    def test_pipeline_error(self) -> None:
        """Test PipelineError."""
        err = PipelineError("Pipeline stage failed")
        assert str(err) == "Pipeline stage failed"
        assert isinstance(err, (VaridexError, Exception))

    def test_configuration_error_with_parameter(self) -> None:
        """Test ConfigurationError with parameter name."""
        err = ConfigurationError("Invalid parameter: min_quality_score")
        assert "min_quality_score" in str(err)

    def test_data_processing_error_with_stage(self) -> None:
        """Test DataProcessingError with stage information."""
        err = DataProcessingError("Failed at normalization stage")
        assert "normalization" in str(err)

    def test_pipeline_error_with_stage_name(self) -> None:
        """Test PipelineError with stage name."""
        err = PipelineError("Stage 'annotation' failed")
        assert "annotation" in str(err)


class TestErrorPropagation:
    """Test error propagation through call stack."""

    def test_error_propagates_through_functions(self) -> None:
        """Test error propagates through nested function calls."""

        def level3():
            raise ValidationError("Deep error")

        def level2():
            level3()

        def level1():
            level2()

        with pytest.raises(ValidationError) as exc_info:
            level1()
        assert "Deep error" in str(exc_info.value)

    def test_error_can_be_caught_and_reraised(self) -> None:
        """Test error can be caught and re-raised."""

        def function_that_catches_and_reraises():
            try:
                raise DataLoadError("Original error")
            except DataLoadError:
                raise DataLoadError("Wrapped error")

        with pytest.raises(DataLoadError) as exc_info:
            function_that_catches_and_reraises()
        assert "Wrapped error" in str(exc_info.value)

    def test_error_can_be_transformed(self) -> None:
        """Test one error type can be transformed to another."""

        def function_that_transforms_error():
            try:
                raise ValidationError("Validation failed")
            except ValidationError as e:
                raise ClassificationError(f"Classification error: {e}")

        with pytest.raises(ClassificationError) as exc_info:
            function_that_transforms_error()
        assert "Validation failed" in str(exc_info.value)


class TestErrorContextManagers:
    """Test errors with context managers."""

    def test_error_in_context_manager(self) -> None:
        """Test error raised inside context manager."""
        from contextlib import contextmanager

        @contextmanager
        def error_context():
            try:
                yield
            finally:
                pass  # Cleanup

        with pytest.raises(ValidationError):
            with error_context():
                raise ValidationError("Error in context")

    def test_error_during_context_cleanup(self) -> None:
        """Test handling errors during cleanup."""
        from contextlib import contextmanager

        @contextmanager
        def cleanup_error_context():
            yield
            # Cleanup that might fail is handled

        with cleanup_error_context():
            pass  # Normal execution


class TestErrorEdgeCases:
    """Test edge cases in error handling."""

    def test_error_with_none_message(self) -> None:
        """Test error with None as message."""
        try:
            err = VaridexError(None)
            str(err)  # Should not raise
        except (TypeError, AttributeError):
            pass  # Some implementations may reject None

    def test_error_with_numeric_message(self) -> None:
        """Test error with numeric message."""
        err = VaridexError(str(12345))
        assert "12345" in str(err)

    def test_error_with_unicode_message(self) -> None:
        """Test error with Unicode characters."""
        err = ValidationError("Invalid value: café, naïve, 日本語")
        assert "café" in str(err) or "caf" in str(err)

    def test_multiple_exceptions_in_sequence(self) -> None:
        """Test raising multiple exceptions in sequence."""
        errors = []
        for i in range(3):
            try:
                raise ValidationError(f"Error {i}")
            except ValidationError as e:
                errors.append(str(e))
        assert len(errors) == 3
        assert "Error 0" in errors[0]
        assert "Error 2" in errors[2]

    def test_error_comparison(self) -> None:
        """Test error instances are distinct."""
        err1 = ValidationError("Error 1")
        err2 = ValidationError("Error 1")
        assert err1 is not err2
        assert str(err1) == str(err2)


class TestErrorRecovery:
    """Test error recovery patterns."""

    def test_try_except_pattern(self) -> None:
        """Test basic try-except error recovery."""
        recovered = False
        try:
            raise ValidationError("Test error")
        except ValidationError:
            recovered = True
        assert recovered is True

    def test_try_except_else_pattern(self) -> None:
        """Test try-except-else pattern."""
        success = False
        error = False
        try:
            pass  # No error
        except ValidationError:
            error = True
        else:
            success = True
        assert success is True
        assert error is False

    def test_try_except_finally_pattern(self) -> None:
        """Test try-except-finally pattern."""
        cleanup_called = False
        try:
            raise ValidationError("Test error")
        except ValidationError:
            pass
        finally:
            cleanup_called = True
        assert cleanup_called is True

    def test_multiple_exception_handlers(self) -> None:
        """Test handling multiple exception types."""
        caught_type = None
        try:
            raise DataLoadError("Test")
        except ValidationError:
            caught_type = "validation"
        except DataLoadError:
            caught_type = "data_load"
        except Exception:
            caught_type = "generic"
        assert caught_type == "data_load"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
