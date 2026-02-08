"""
varidex/acmg/frequency_criteria.py v7.3.0-dev

Population frequency-based ACMG criteria (PM2, BA1, BS1).

FIXED v7.3.0-dev: PM2 now uses disease-mode-specific thresholds

Development version - not for production use.
"""

import logging
from dataclasses import dataclass
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class FrequencyCriteria:
    """Container for frequency-based ACMG criteria."""

    BA1: bool = False  # Stand-alone benign: AF >5%
    BS1: bool = False  # Strong benign: AF >1%
    PM2: bool = False  # Moderate pathogenic: Absent/rare (AF <0.01%)


def evaluate_frequency_criteria(
    allele_freq: Optional[float], disease_mode: str = "unknown"
) -> FrequencyCriteria:
    """
    Evaluate BA1, BS1, and PM2 criteria based on allele frequency.

    Args:
        allele_freq: Allele frequency from gnomAD (0.0 to 1.0)
        disease_mode: Disease inheritance mode (dominant/recessive)

    Returns:
        FrequencyCriteria with evaluated criteria

    ACMG Thresholds:
        BA1: >5% (0.05) - Stand-alone benign
        BS1: >1% (0.01) - Strong benign (may vary by disease)
        PM2: Disease-mode-specific (absent/extremely rare):
        - Dominant/AD: <0.005% (5e-5)
        - Recessive/AR: <0.1% (1e-3)
        - Unknown: <0.01% (1e-4)
    """
    criteria = FrequencyCriteria()

    if allele_freq is None:
        # No frequency data available
        return criteria

    # BA1: Allele frequency >5% in population
    if allele_freq > 0.05:
        criteria.BA1 = True
        logger.debug(f"BA1 met: AF={allele_freq:.4f} >5%")
        return criteria  # BA1 overrides other criteria

    # BS1: Allele frequency greater than expected for disorder
    # Default threshold: >1%, but may need disease-specific adjustment
    if allele_freq > 0.01:
        criteria.BS1 = True
        logger.debug(f"BS1 met: AF={allele_freq:.4f} >1%")

    # PM2: Absent or extremely rare (disease-mode-specific)
    else:
        pm2_threshold = None
        if disease_mode in {"dominant", "ad", "AD"}:
            pm2_threshold = 5e-5  # 0.005% for dominant
        elif disease_mode in {"recessive", "ar", "AR"}:
            pm2_threshold = 1e-3  # 0.1% for recessive
        else:
            pm2_threshold = 1e-4  # 0.01% default

        if allele_freq < pm2_threshold:
            criteria.PM2 = True
            logger.debug(
                f"PM2 met: AF={allele_freq:.4f} <{pm2_threshold:.5f} "
                f"(mode={disease_mode})"
            )

    return criteria


def apply_frequency_criteria(variant_data: Dict, allele_freq: Optional[float]) -> Dict:
    """
    Apply frequency criteria to variant and return updated data.

    Args:
        variant_data: Dictionary with variant information
        allele_freq: gnomAD allele frequency

    Returns:
        Updated variant_data with frequency criteria
    """
    criteria = evaluate_frequency_criteria(allele_freq)

    # Add criteria to variant data
    variant_data["gnomad_af"] = allele_freq
    variant_data["BA1"] = criteria.BA1
    variant_data["BS1"] = criteria.BS1
    variant_data["PM2"] = criteria.PM2

    # Update ACMG classification based on frequency
    if criteria.BA1:
        variant_data["acmg_frequency_class"] = "Benign (BA1)"
    elif criteria.BS1:
        variant_data["acmg_frequency_class"] = "Likely Benign (BS1)"
    elif criteria.PM2:
        variant_data["acmg_frequency_class"] = "PM2 evidence"
    else:
        variant_data["acmg_frequency_class"] = "Neutral"

    return variant_data
