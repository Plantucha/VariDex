"""
VariDex Utilities Helpers Module v7.0.3
========================================
Helper utilities for variant analysis with ClinVar classification.

Changes v7.0.3:
- Fixed conflicting classification detection (check before pathogenic)
- Properly categorizes "Conflicting_classifications_of_pathogenicity"
- Maps ClinVar classifications to ACMG codes (P, LP, VUS, LB, B, CONFLICT)
"""

from typing import Any, Dict, List
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
        import pandas as pd

        if not isinstance(df, pd.DataFrame):
            return False
        try:
            return df is not None and len(df) > 0
        except Exception:
            return False

    @staticmethod
    def validate_dataframe_structure(
        df, stage_name: str, required_cols: List[str]
    ) -> tuple:
        """
        Validate DataFrame has required columns.

        Args:
            df: DataFrame to validate
            stage_name: Name of the stage for error messages
            required_cols: List of required column names

        Returns:
            Tuple of (is_valid, error_message)
        """
        import pandas as pd

        if not isinstance(df, pd.DataFrame):
            return False, f"{stage_name}: Expected DataFrame, got {type(df)}"

        missing = set(required_cols) - set(df.columns)
        if missing:
            return False, f"{stage_name}: Missing columns: {sorted(missing)}"

        return True, ""


def classify_variants_production(variants: List[Dict], classifier) -> List[Dict]:
    """
    Classify variants using ClinVar clinical significance - FIXED v7.0.3.

    Maps ClinVar classifications to ACMG codes:
    - Pathogenic → P
    - Likely_pathogenic → LP
    - Benign → B
    - Likely_benign → LB
    - Conflicting → CONFLICT (checked FIRST before pathogenic/benign)
    - Uncertain_significance/VUS → VUS

    Args:
        variants: List of variant dictionaries with clinical_sig field
        classifier: ACMG classifier instance (unused in v7.0)

    Returns:
        List of classified variants with classification and evidence
    """
    results = []

    for variant in variants:
        try:
            # Extract ClinVar classification
            clinical_sig = str(
                variant.get("clinical_sig", "Uncertain_significance")
            ).strip()
            review_status = str(variant.get("review_status", "")).strip()

            # Map ClinVar to ACMG classification
            classification = "VUS"
            evidence = []
            clinical_sig_lower = clinical_sig.lower()

            # CHECK CONFLICTING FIRST (before pathogenic/benign keywords)
            if "conflicting" in clinical_sig_lower:
                classification = "CONFLICT"
                evidence.append("ClinVar: Conflicting interpretations")
                # Extract what the conflict is about
                if "pathogenic" in clinical_sig_lower:
                    evidence.append("Conflicting: Pathogenicity disputed")
                elif "benign" in clinical_sig_lower:
                    evidence.append("Conflicting: Benignness disputed")
            # Pathogenic classifications
            elif (
                "pathogenic" in clinical_sig_lower
                and "likely" not in clinical_sig_lower
            ):
                classification = "P"
                evidence.append("ClinVar: Pathogenic")
            elif "likely" in clinical_sig_lower and "pathogenic" in clinical_sig_lower:
                if clinical_sig_lower.startswith("likely"):
                    classification = "LP"
                    evidence.append("ClinVar: Likely Pathogenic")
                else:
                    classification = "P"
                    evidence.append("ClinVar: Pathogenic/Likely Pathogenic")
            # Benign classifications
            elif "benign" in clinical_sig_lower and "likely" not in clinical_sig_lower:
                classification = "B"
                evidence.append("ClinVar: Benign")
            elif "likely" in clinical_sig_lower and "benign" in clinical_sig_lower:
                if clinical_sig_lower.startswith("likely"):
                    classification = "LB"
                    evidence.append("ClinVar: Likely Benign")
                else:
                    classification = "B"
                    evidence.append("ClinVar: Benign/Likely Benign")
            # VUS or unknown
            else:
                classification = "VUS"
                evidence.append(f"ClinVar: {clinical_sig}")

            # Add review status to evidence
            if review_status:
                if "multiple_submitters" in review_status:
                    evidence.append("Multiple submitters")
                if (
                    "expert_panel" in review_status
                    or "practice_guideline" in review_status
                ):
                    evidence.append("Expert reviewed")
                if "no_assertion" in review_status:
                    evidence.append("No assertion criteria")
                if "conflicting" in review_status:
                    evidence.append("Conflicting interpretations noted")

            result = {
                "variant": variant,
                "classification": classification,
                "evidence": evidence,
                "clinical_sig": clinical_sig,
                "review_status": review_status,
            }
            results.append(result)

        except Exception as e:
            logger.error(f"Error classifying variant: {e}")
            results.append(
                {"variant": variant, "classification": "ERROR", "error": str(e)}
            )

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

    Raises:
        TypeError: If key is None
    """
    if key is None:
        raise TypeError("Variant key cannot be None")

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
