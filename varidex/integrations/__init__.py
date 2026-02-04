"""External API integrations for VariDex.

This package contains clients for external genomic databases and services.
"""

from varidex.version import __version__

try:
    from varidex.integrations.gnomad_annotator import (
        AnnotationConfig,
        GnomADAnnotator,
        annotate_variants,
    )

    GNOMAD_ANNOTATOR_AVAILABLE = True
except ImportError:
    GNOMAD_ANNOTATOR_AVAILABLE = False

try:
    from varidex.integrations.gnomad_client import GnomadClient, GnomadVariantFrequency

    GNOMAD_CLIENT_AVAILABLE = True
except ImportError:
    GNOMAD_CLIENT_AVAILABLE = False

__all__ = [
    "__version__",
    "GnomADAnnotator",
    "AnnotationConfig",
    "annotate_variants",
    "GnomadClient",
    "GnomadVariantFrequency",
]
