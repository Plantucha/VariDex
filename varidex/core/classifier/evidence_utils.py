#!/usr/bin/env python3
"""varidex/core/classifier/evidence_utils.py - Evidence Utilities

Utility functions for ACMG evidence assignment.
Extracted from engine.py v6.3.1 for modularity and line limit compliance.

Functions:
- get_star_rating: Convert ClinVar review status to star rating (0-4)
- validate_variant: Validate variant data completeness
- extract_genes: Parse gene symbols from multi-gene fields
- check_lof: Detect loss-of-function variants
"""

from typing import Tuple, List, Set
from functools import lru_cache
import pandas as pd
import logging

from varidex.core.models import VariantData
from varidex.core.config import CLINVAR_STAR_RATINGS
from varidex.core.classifier.text_utils import normalize_text, split_delimited_value

logger = logging.getLogger(__name__)

# LOF indicators - frozen set for efficient membership testing
LOF_INDICATORS = frozenset(
    [
        "frameshift",
        "nonsense",
        "stop-gain",
        "stop-gained",
        "canonical-splice",
        "splice-donor",
        "splice-acceptor",
        "start-lost",
        "stop-lost",
        "initiator-codon",
    ]
)

# Pre-sorted ratings for efficient lookup
SORTED_STAR_RATINGS = sorted(CLINVAR_STAR_RATINGS.items(), key=lambda x: -len(x[0]))


@lru_cache(maxsize=512)
def get_star_rating(review_status: str) -> int:
    """Convert ClinVar review status to star rating (0-4) CACHED.

    Cached for performance with up to 512 unique review statuses.

    Args:
        review_status: ClinVar review status string

    Returns:
        Star rating from 0 (no assertion) to 4 (practice guideline)
    """
    try:
        if pd.isna(review_status):
            return 0

        review_lower = normalize_text(review_status)

        if review_lower in CLINVAR_STAR_RATINGS:
            return CLINVAR_STAR_RATINGS[review_lower]

        for key, stars in SORTED_STAR_RATINGS:
            if key in review_lower:
                return stars

        return 0

    except Exception as e:
        logger.warning(f"Failed to get star rating for '{review_status}': {e}")
        return 0


def validate_variant(variant: VariantData) -> Tuple[bool, List[str]]:
    """Validate variant data completeness and correctness.

    Args:
        variant: VariantData object to validate

    Returns:
        Tuple of (is_valid, error_list)
    """
    errors: List[str] = []

    try:
        if not variant:
            errors.append("Variant object is None")
            return False, errors

        required_fields = {
            "clinical_sig": "Clinical significance",
            "gene": "Gene annotation",
            "variant_type": "Variant type",
            "molecular_consequence": "Molecular consequence",
        }

        for field, description in required_fields.items():
            if not hasattr(variant, field):
                errors.append(f"Missing {field}: {description}")
            elif pd.isna(getattr(variant, field)) or not getattr(variant, field):
                errors.append(f"Empty {field}: {description}")

        if hasattr(variant, "star_rating"):
            if variant.star_rating < 0 or variant.star_rating > 4:
                errors.append(f"Star rating out of bounds: {variant.star_rating}")

        return len(errors) == 0, errors

    except Exception as e:
        logger.error(f"Validation exception: {e}")
        errors.append(f"Validation exception: {str(e)}")
        return False, errors


def extract_genes(gene_field: str) -> Set[str]:
    """Extract unique gene symbols from multi-gene field.

    Args:
        gene_field: Gene field that may contain multiple genes

    Returns:
        Set of unique gene symbols
    """
    try:
        if pd.isna(gene_field):
            return set()

        return set(split_delimited_value(str(gene_field)))

    except Exception as e:
        logger.warning(f"Gene extraction failed for '{gene_field}': {e}")
        return set()


def check_lof(variant_consequence: str, sig: str) -> bool:
    """Check if variant is loss-of-function.

    Args:
        variant_consequence: Molecular consequence annotation
        sig: Clinical significance annotation

    Returns:
        True if LOF indicators detected
    """
    try:
        cons_lower = normalize_text(variant_consequence)
        sig_lower = normalize_text(sig)

        return any(ind in cons_lower or ind in sig_lower for ind in LOF_INDICATORS)

    except Exception as e:
        logger.warning(f"LOF check failed: {e}")
        return False
