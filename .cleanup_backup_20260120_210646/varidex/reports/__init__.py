"""
VariDex Reports Module
======================

Report generation in multiple formats (CSV, JSON, HTML).

Components:
    - generator: Main report orchestration
    - formatters: Format-specific generators

Usage:
    from varidex.reports import generate_all_reports

    reports = generate_all_reports(results_df, output_dir="./reports")
"""

from varidex.version import get_version

__version__ = get_version("reports.generator")

def generate_all_reports(*args, **kwargs):
    """Generate all report formats. Lazy import wrapper."""
    from varidex.reports.generator import generate_all_reports as _generate
    return _generate(*args, **kwargs)

__all__ = ["generate_all_reports"]
