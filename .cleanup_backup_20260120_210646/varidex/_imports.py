"""
VariDex Import Manager
======================
Complete import management utilities with all aliases.
"""

def get_module(module_name):
    """Dynamically import a module."""
    import importlib
    return importlib.import_module(module_name)


def get_config():
    """Get configuration module."""
    try:
        from varidex.core import config
        return config
    except ImportError:
        class MinimalConfig:
            pass
        return MinimalConfig()


def get_models():
    """Get models module."""
    try:
        from varidex.core import models
        return models
    except ImportError:
        return None


def get_model():
    """Alias for get_models()."""
    return get_models()


def get_loaders():
    """Get loaders module."""
    try:
        from varidex.io import loaders
        return loaders
    except ImportError:
        return None


def get_loader():
    """Alias for get_loaders()."""
    return get_loaders()


def get_report_generator():
    """Get report generator module."""
    try:
        from varidex.reports import generator
        return generator
    except ImportError:
        return None


def get_report_generators():
    """Alias for get_report_generator()."""
    return get_report_generator()


def get_reports():
    """Alias for get_report_generator()."""
    return get_report_generator()


def get_report():
    """Alias for get_report_generator()."""
    return get_report_generator()


def get_helpers():
    """Get helpers module."""
    try:
        from varidex.utils import helpers
        return helpers
    except ImportError:
        return None


def get_helper():
    """Alias for get_helpers()."""
    return get_helpers()


def get_validator():
    """Get validators module."""
    try:
        from varidex.io import validators_advanced
        return validators_advanced
    except ImportError:
        return None


def get_validators():
    """Alias for get_validator()."""
    return get_validator()


def check_dependencies():
    """Check if optional dependencies are available."""
    optional_deps = {
        'pandas': False,
        'numpy': False,
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
    'get_module',
    'get_config',
    'get_models',
    'get_model',
    'get_loaders',
    'get_loader',
    'get_report_generator',
    'get_report_generators',
    'get_reports',
    'get_report',
    'get_helpers',
    'get_helper',
    'get_validator',
    'get_validators',
    'check_dependencies'
]
