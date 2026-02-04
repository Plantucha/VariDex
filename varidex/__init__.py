"""
VariDex - Variant Analysis Pipeline
====================================

A production-grade genetic variant analysis system implementing ACMG 2015 guidelines.

Usage:
    from varidex import version
    from varidex.pipeline import run_pipeline

Version: 6.0.0
Author: VariDex Team
License: MIT
"""

from varidex.exceptions import (
    ClassificationError,
    DataLoadError,
    ReportError,
    ValidationError,
    VaridexError,
)
from varidex.version import get_version, version

__version__ = version
__all__ = [
    "version",
    "get_version",
    "VaridexError",
    "ValidationError",
    "DataLoadError",
    "ClassificationError",
    "ReportError",
]

# Optional import manager
try:
    from varidex import _imports
except ImportError:
    _imports = None
