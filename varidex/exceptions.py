"""
VariDex Exception Module
=========================
Custom exceptions for variant analysis pipeline.
Re-exports from varidex.core.exceptions for backward compatibility.
"""

from typing import List

# Import all exceptions from core.exceptions
from varidex.core.exceptions import (
    ACMGClassificationError,
    ACMGConfigurationError,
    ACMGValidationError,
    ClassificationError,
    ConfigurationError,
    DataLoadError,
    DataProcessingError,
    ErrorCode,
    FileProcessingError,
    ReportError,
    ValidationError,
    VaridexError,
    validate_not_empty,
    validate_not_none,
    validate_type,
)


# Additional exceptions not in core.exceptions
class VariDexError(VaridexError):
    """Alias for VaridexError (backward compatibility)."""


class DownloadError(VaridexError):
    """Raised when download operations fail."""


class DataIntegrityError(VaridexError):
    """Raised when data integrity checks fail."""


class MatchingError(VaridexError):
    """Raised when variant matching fails."""


class PipelineError(VaridexError):
    """Raised when pipeline execution fails."""


# Backward compatibility aliases
ProcessingError = DataProcessingError

__version__: str = "6.0.0"

__all__: List[str] = [
    "ConfigurationError",
    "VaridexError",
    "VariDexError",
    "ValidationError",
    "DataLoadError",
    "DownloadError",
    "DataIntegrityError",
    "MatchingError",
    "ClassificationError",
    "ReportError",
    "FileProcessingError",
    "ACMGValidationError",
    "ACMGClassificationError",
    "ACMGConfigurationError",
    "DataProcessingError",
    "PipelineError",
    "ProcessingError",
    "ErrorCode",
    "validate_not_none",
    "validate_not_empty",
    "validate_type",
]
