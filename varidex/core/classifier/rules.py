#!/usr/bin/env python3
"""
varidex/core/classifier/rules.py - ACMG 2015 Combination Rules
===============================================================
ACMG 2015 evidence combination and conflict resolution logic.

Reference: Richards et al. 2015, PMID 25741868, Table 5
"""

from typing import Tuple, List
import logging

from varidex.core.models import ACMGEvidenceSet
from varidex.core.classifier.config import ACMGConfig

logger = logging.getLogger(__name__)


def calculate_evidence_score(evidence: ACMGEvidenceSet, config: ACMGConfig) -> Tuple[float, float]:
    """
    Calculate numerical evidence scores for pathogenic and benign.

    Args:
        evidence: ACMGEvidenceSet with assigned codes
        config: ACMGConfig with evidence weights

    Returns:
        Tuple of (pathogenic_score, benign_score)
    """
    weights = config.get_evidence_weights()

    path_score = (
        len(evidence.pvs) * weights["PVS"]
        + len(evidence.ps) * weights["PS"]
        + len(evidence.pm) * weights["PM"]
        + len(evidence.pp) * weights["PP"]
    )

    benign_score = (
        len(evidence.ba) * weights["BA"]
        + len(evidence.bs) * weights["BS"]
        + len(evidence.bp) * weights["BP"]
    )

    return float(path_score), float(benign_score)


def validate_evidence_combination(
    evidence: ACMGEvidenceSet, config: ACMGConfig
) -> Tuple[bool, List[str]]:
    """
    Validate evidence combination follows ACMG guidelines.

    Args:
        evidence: ACMGEvidenceSet to validate
        config: ACMGConfig with thresholds

    Returns:
        Tuple of (is_valid, warnings_list)
    """
    warnings = []

    if len(evidence.pvs) > 1:
        warnings.append("Multiple PVS codes detected - review manually")

    if len(evidence.ba) > 1:
        warnings.append("Multiple BA codes detected - review manually")

    if len(evidence.ps) > 4:
        warnings.append(f"Excessive PS codes ({len(evidence.ps)}) - may indicate error")

    if evidence.has_conflict():
        path_score, benign_score = calculate_evidence_score(evidence, config)
        warnings.append(f"Conflicting evidence: Path={path_score}, Benign={benign_score}")

    total_evidence = (
        len(evidence.pvs)
        + len(evidence.ps)
        + len(evidence.pm)
        + len(evidence.pp)
        + len(evidence.ba)
        + len(evidence.bs)
        + len(evidence.bp)
    )
    if total_evidence == 0:
        warnings.append("No evidence codes assigned")

    return len([w for w in warnings if "error" in w.lower()]) == 0, warnings


def combine_evidence(evidence: ACMGEvidenceSet, config: ACMGConfig) -> Tuple[str, str]:
    """
    Apply ACMG 2015 combination rules (Richards et al. Table 5).

    Implements all 19 ACMG 2015 evidence combination rules with
    weighted conflict resolution.

    Args:
        evidence: ACMGEvidenceSet with assigned codes
        config: ACMGConfig with weights and thresholds

    Returns:
        Tuple of (classification, confidence_level)

    Classifications:
        - "Pathogenic" (P)
        - "Likely Pathogenic" (LP)
        - "Uncertain Significance" (VUS)
        - "Likely Benign" (LB)
        - "Benign" (B)
    """
    # Cache evidence counts (optimization)
    pvs = len(evidence.pvs)
    ps = len(evidence.ps)
    pm = len(evidence.pm)
    pp = len(evidence.pp)
    ba = len(evidence.ba)
    bs = len(evidence.bs)
    bp = len(evidence.bp)

    # Stand-alone benign (BA1) overrides all
    if ba > 0:
        if pvs + ps + pm + pp > 0:
            return "Benign", "Stand-alone (BA1 overrides conflict)"
        return "Benign", "Stand-alone (BA1)"

    # Calculate scores once (optimization)
    path_score, benign_score = calculate_evidence_score(evidence, config)

    # Conflict resolution
    if path_score > 0 and benign_score > 0:
        total = path_score + benign_score
        path_ratio = path_score / total if total > 0 else 0

        if (
            path_score >= config.strong_evidence_threshold
            and benign_score >= config.strong_evidence_threshold
        ):
            return "Uncertain Significance", f"Strong conflict ({path_score}v{benign_score})"

        if config.conflict_balanced_min <= path_ratio <= config.conflict_balanced_max:
            return "Uncertain Significance", f"Balanced conflict ({path_score}v{benign_score})"

    # ===================================================================
    # PATHOGENIC RULES (8 combinations)
    # ===================================================================

    # Rule 1: PVS1 + PS (Very High)
    if pvs >= 1:
        if ps >= 1:
            return "Pathogenic", "Very High (PVS1+PS)"
        if pm >= 2:
            return "Pathogenic", "High (PVS1+2PM)"
        if pm == 1 and pp >= 1:
            return "Pathogenic", "High (PVS1+PM+PP)"
        if pp >= 2:
            return "Pathogenic", "Moderate (PVS1+2PP)"

    # Rule 5: 2+ PS (High)
    if ps >= 2:
        return "Pathogenic", "High (2+PS)"

    # Rules 6-8: PS combinations
    if ps == 1:
        if pm >= 3:
            return "Pathogenic", "High (PS+3PM)"
        if pm == 2 and pp >= 2:
            return "Pathogenic", "Moderate (PS+2PM+2PP)"
        if pm == 1 and pp >= 4:
            return "Pathogenic", "Moderate (PS+PM+4PP)"

    # ===================================================================
    # LIKELY PATHOGENIC RULES (6 combinations)
    # ===================================================================

    # Rule 1: PVS1 + PM (Moderate)
    if pvs == 1 and pm == 1:
        return "Likely Pathogenic", "Moderate (PVS1+PM)"

    # Rule 2: PS + 1-2 PM (Moderate)
    if ps == 1 and pm >= 1 and pm <= 2:
        return "Likely Pathogenic", "Moderate (PS+PM)"

    # Rule 3: PS + 2+ PP (Moderate)
    if ps == 1 and pp >= 2:
        return "Likely Pathogenic", "Moderate (PS+2+PP)"

    # Rule 4: 3+ PM (Moderate)
    if pm >= 3:
        return "Likely Pathogenic", "Moderate (3+PM)"

    # Rule 5: 2PM + 2+PP (Low)
    if pm == 2 and pp >= 2:
        return "Likely Pathogenic", "Low (2PM+2PP)"

    # Rule 6: PM + 4+PP (Low)
    if pm == 1 and pp >= 4:
        return "Likely Pathogenic", "Low (PM+4PP)"

    # ===================================================================
    # BENIGN RULES (3 combinations)
    # ===================================================================

    # Rule 1: BA1 (Stand-alone) - handled above

    # Rule 2: 2+ BS (High)
    if bs >= 2:
        return "Benign", "High (2+BS)"

    # Rule 3: BS + BP (High)
    if bs == 1 and bp >= 1:
        return "Benign", "High (BS+BP)"

    # ===================================================================
    # LIKELY BENIGN RULES (2 combinations)
    # ===================================================================

    # Rule 1: 1 BS (Moderate)
    if bs == 1:
        return "Likely Benign", "Moderate (BS)"

    # Rule 2: 2+ BP (Low)
    if bp >= 2:
        return "Likely Benign", "Low (2+BP)"

    # ===================================================================
    # UNCERTAIN SIGNIFICANCE (default)
    # ===================================================================

    # VUS with some evidence
    if pvs + ps + pm + pp > 0 or bs + bp > 0:
        return "Uncertain Significance", "Insufficient Evidence"

    # VUS with no evidence
    return "Uncertain Significance", "No Evidence"


def get_acmg_rule_summary() -> str:
    """
    Get human-readable summary of all ACMG 2015 rules.

    Returns:
        Formatted string with all 19 combination rules
    """
    rules = """
ACMG 2015 Evidence Combination Rules (Richards et al. Table 5)
===============================================================

PATHOGENIC (8 rules):
  1. 1 PVS + 1 PS                    → Very High confidence
  2. 1 PVS + 2 PM                    → High confidence
  3. 1 PVS + 1 PM + 1 PP             → High confidence
  4. 1 PVS + 2 PP                    → Moderate confidence
  5. 2 PS                            → High confidence
  6. 1 PS + 3 PM                     → High confidence
  7. 1 PS + 2 PM + 2 PP              → Moderate confidence
  8. 1 PS + 1 PM + 4 PP              → Moderate confidence

LIKELY PATHOGENIC (6 rules):
  9. 1 PVS + 1 PM                    → Moderate confidence
 10. 1 PS + 1-2 PM                   → Moderate confidence
 11. 1 PS + 2+ PP                    → Moderate confidence
 12. 3+ PM                           → Moderate confidence
 13. 2 PM + 2+ PP                    → Low confidence
 14. 1 PM + 4+ PP                    → Low confidence

BENIGN (3 rules):
 15. 1 BA (stand-alone)              → Stand-alone
 16. 2+ BS                           → High confidence
 17. 1 BS + 1 BP                     → High confidence

LIKELY BENIGN (2 rules):
 18. 1 BS                            → Moderate confidence
 19. 2+ BP                           → Low confidence

Evidence Weights:
  PVS (Very Strong): 8 points
  PS  (Strong):      4 points
  PM  (Moderate):    2 points
  PP  (Supporting):  1 point
  BA  (Stand-alone): 8 points (benign)
  BS  (Strong):      4 points (benign)
  BP  (Supporting):  1 point (benign)

Conflict Resolution:
  - BA1 overrides all pathogenic evidence
  - Weighted scoring: path_score vs benign_score
  - Strong conflict: both ≥4 points → VUS
  - Balanced conflict: 40-60% ratio → VUS
"""
    return rules


if __name__ == "__main__":
    print(get_acmg_rule_summary())
