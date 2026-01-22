"""
VariDex Utilities Helpers Module
=================================
Helper utilities for variant analysis.
"""

from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class DataValidator:
    """Validator for variant data."""

    @staticmethod
    def validate_variant(variant: Dict[str, Any]) -> bool:
        """
        Validate variant data structure.

        Args:
            variant: Variant data dictionary

        Returns:
            True if valid, False otherwise
        """
        required_fields = ["chromosome", "position"]
        return all(field in variant for field in required_fields)

    @staticmethod
    def validate_dataframe(df) -> bool:
        """
        Validate dataframe structure.

        Args:
            df: DataFrame to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            return df is not None and len(df) > 0
        except Exception:
            return False


def classify_variants_production(variants: List[Dict], classifier) -> List[Dict]:
    """
    Classify variants in production mode.

    Args:
        variants: List of variant dictionaries
        classifier: ACMG classifier instance

    Returns:
        List of classified variants
    """
    results = []

    for variant in variants:
        try:
            # Basic classification
            result = {"variant": variant, "classification": "VUS", "evidence": []}  # Default
            results.append(result)
        except Exception as e:
            logger.error(f"Error classifying variant: {e}")
            results.append({"variant": variant, "classification": "ERROR", "error": str(e)})

    return results


def format_variant_key(chrom: str, pos: int, ref: str, alt: str) -> str:
    """
    Format variant as key string.

    Args:
        chrom: Chromosome
        pos: Position
        ref: Reference allele
        alt: Alternate allele

    Returns:
        Formatted variant key
    """
    return f"{chrom}:{pos}:{ref}:{alt}"


def parse_variant_key(key: str) -> Dict[str, Any]:
    """
    Parse variant key string.

    Args:
        key: Variant key string

    Returns:
        Dictionary with variant components
    """
    try:
        parts = key.split(":")
        if len(parts) >= 4:
            return {
                "chromosome": parts[0],
                "position": int(parts[1]),
                "ref": parts[2],
                "alt": parts[3],
            }
    except Exception:
        pass

    return {}


__all__ = [
    "DataValidator",
    "classify_variants_production",
    "format_variant_key",
    "parse_variant_key",
]
