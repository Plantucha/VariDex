"""
VariDex Import Manager
======================
Complete import management utilities with all aliases.
"""

from typing import Any, Optional, Dict
import importlib


def get_module(module_name: str) -> Any:
    """
    Dynamically import a module.

    Args:
        module_name: Name of module to import

    Returns:
        Imported module
    """
    return importlib.import_module(module_name)


def get_config() -> Any:
    """
    Get configuration module.

    Returns:
        Config module or minimal fallback
    """
    try:
        from varidex.core import config

        return config
    except ImportError:

        class MinimalConfig:
            pass

        return MinimalConfig()


def get_models() -> Optional[Any]:
    """
    Get models module.

    Returns:
        Models module or None
    """
    try:
        from varidex.core import models

        return models
    except ImportError:
        return None


def get_model() -> Optional[Any]:
    """
    Alias for get_models().

    Returns:
        Models module or None
    """
    return get_models()


def get_loaders() -> Optional[Any]:
    """
    Get loaders module.

    Returns:
        Loaders module or None
    """
    try:
        from varidex.io import loaders

        return loaders
    except ImportError:
        return None


def get_loader() -> Optional[Any]:
    """
    Alias for get_loaders().

    Returns:
        Loaders module or None
    """
    return get_loaders()


def get_report_generator() -> Optional[Any]:
    """
    Get report generator module.

    Returns:
        Report generator module or None
    """
    try:
        from varidex.reports import generator

        return generator
    except ImportError:
        return None


def get_report_generators() -> Optional[Any]:
    """
    Alias for get_report_generator().

    Returns:
        Report generator module or None
    """
    return get_report_generator()


def get_reports() -> Optional[Any]:
    """
    Alias for get_report_generator().

    Returns:
        Report generator module or None
    """
    return get_report_generator()


def get_report() -> Optional[Any]:
    """
    Alias for get_report_generator().

    Returns:
        Report generator module or None
    """
    return get_report_generator()


def get_helpers() -> Optional[Any]:
    """
    Get helpers module.

    Returns:
        Helpers module or None
    """
    try:
        from varidex.utils import helpers

        return helpers
    except ImportError:
        return None


def get_helper() -> Optional[Any]:
    """
    Alias for get_helpers().

    Returns:
        Helpers module or None
    """
    return get_helpers()


def get_validator() -> Optional[Any]:
    """
    Get validators module.

    Returns:
        Validators module or None
    """
    try:
        from varidex.io import validators_advanced

        return validators_advanced
    except ImportError:
        return None


def get_validators() -> Optional[Any]:
    """
    Alias for get_validator().

    Returns:
        Validators module or None
    """
    return get_validator()


def check_dependencies() -> Dict[str, bool]:
    """
    Check if optional dependencies are available.

    Returns:
        Dictionary mapping dependency names to availability status
    """
    optional_deps: Dict[str, bool] = {
        "pandas": False,
        "numpy": False,
    }

    for dep in optional_deps:
        try:
            __import__(dep)
            optional_deps[dep] = True
        except ImportError:
            pass

    return optional_deps


# Complete list of all available functions
__all__ = [
    "get_module",
    "get_config",
    "get_models",
    "get_model",
    "get_loaders",
    "get_loader",
    "get_report_generator",
    "get_report_generators",
    "get_reports",
    "get_report",
    "get_helpers",
    "get_helper",
    "get_validator",
    "get_validators",
    "check_dependencies",
]
