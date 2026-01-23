#!/usr/bin/env python3
"""varidex/core/classifier/evidence_assignment.py - Evidence Assignment Logic

ACMG evidence code assignment logic.
Extracted from engine.py v6.3.1 for better organization and line limit compliance.

Functions:
- assign_pathogenic_evidence: Assign PVS1, PM4, PP2
- assign_benign_evidence: Assign BA1, BS1, BP1, BP3
- assign_evidence_codes: Main wrapper coordinating evidence assignment
"""

from typing import Set, Optional
import logging

from varidex.core.models import ACMGEvidenceSet, VariantData
from varidex.core.config import LOF_GENES, MISSENSE_RARE_GENES
from varidex.core.classifier.text_utils import normalize_text
from varidex.core.classifier.evidence_utils import (
    validate_variant,
    extract_genes,
    check_lof,
)
from varidex.core.classifier.config import ACMGConfig

logger = logging.getLogger(__name__)


def assign_pathogenic_evidence(
    evidence: ACMGEvidenceSet,
    variant: VariantData,
    genes: Set[str],
    consequence: str,
    sig_lower: str,
    config: ACMGConfig,
) -> None:
    """Assign pathogenic evidence codes (PVS1, PM4, PP2).

    Args:
        evidence: ACMGEvidenceSet to populate
        variant: VariantData object
        genes: Set of gene symbols
        consequence: Normalized molecular consequence
        sig_lower: Normalized clinical significance
        config: ACMG configuration
    """
    # PVS1: LOF in LOF-intolerant genes
    if config.enable_pvs1:
        try:
            if check_lof(consequence, sig_lower):
                matching_genes = genes.intersection(LOF_GENES)
                if matching_genes:
                    evidence.pvs.add("PVS1")
                    logger.debug(f"PVS1: LOF in {matching_genes}")
        except Exception as e:
            logger.error(f"PVS1 assignment failed: {e}")

    # PM4: Protein length changes
    if config.enable_pm4:
        try:
            if (
                "inframe" in consequence
                or "in-frame" in consequence
                or "stop-lost" in consequence
            ):
                if "deletion" in consequence or "insertion" in consequence:
                    evidence.pm.add("PM4")
                    logger.debug("PM4: Protein length change")
        except Exception as e:
            logger.error(f"PM4 assignment failed: {e}")

    # PP2: Missense in missense-rare genes
    if config.enable_pp2:
        try:
            if "missense" in consequence:
                matching_genes = genes.intersection(MISSENSE_RARE_GENES)
                if matching_genes and "pathogenic" in sig_lower:
                    evidence.pp.add("PP2")
                    logger.debug(f"PP2: Missense in {matching_genes}")
        except Exception as e:
            logger.error(f"PP2 assignment failed: {e}")

    # PM2 DISABLED - add to conflicts
    if not config.enable_pm2:
        evidence.conflicts.add("PM2 DISABLED: requires gnomAD API")


def assign_benign_evidence(
    evidence: ACMGEvidenceSet,
    variant: VariantData,
    genes: Set[str],
    consequence: str,
    sig_lower: str,
    config: ACMGConfig,
) -> None:
    """Assign benign evidence codes (BA1, BS1, BP1, BP3).

    Args:
        evidence: ACMGEvidenceSet to populate
        variant: VariantData object
        genes: Set of gene symbols
        consequence: Normalized molecular consequence
        sig_lower: Normalized clinical significance
        config: ACMG configuration
    """
    # BA1: Common polymorphism
    if config.enable_ba1:
        try:
            if "common" in sig_lower and "polymorphism" in sig_lower:
                evidence.ba.add("BA1")
                logger.debug("BA1: Common polymorphism")
        except Exception as e:
            logger.error(f"BA1 assignment failed: {e}")

    # BS1: High population frequency
    if config.enable_bs1:
        try:
            if (
                "population" in sig_lower
                and "frequency" in sig_lower
                and "high" in sig_lower
            ) or ("common" in sig_lower and "pathogenic" not in sig_lower):
                evidence.bs.add("BS1")
                logger.debug("BS1: High population frequency")
        except Exception as e:
            logger.error(f"BS1 assignment failed: {e}")

    # BP1: Missense in LOF genes
    if config.enable_bp1:
        try:
            if "missense" in consequence:
                matching_genes = genes.intersection(LOF_GENES)
                if matching_genes and "benign" in sig_lower:
                    evidence.bp.add("BP1")
                    logger.debug(f"BP1: Missense in LOF gene {matching_genes}")
        except Exception as e:
            logger.error(f"BP1 assignment failed: {e}")

    # BP3: In-frame indel in repetitive region
    if config.enable_bp3:
        try:
            if "inframe" in consequence or "in-frame" in consequence:
                if "repeat" in sig_lower or "repetitive" in sig_lower:
                    evidence.bp.add("BP3")
                    logger.debug("BP3: In-frame indel in repeat")
        except Exception as e:
            logger.error(f"BP3 assignment failed: {e}")

    # BP7 DISABLED - add to conflicts
    if not config.enable_bp7:
        evidence.conflicts.add("BP7 DISABLED: requires SpliceAI scores")


def assign_evidence_codes(
    variant: VariantData, config: ACMGConfig, metrics: Optional[any] = None
) -> ACMGEvidenceSet:
    """Assign ACMG evidence codes to a variant.

    Main entry point for evidence assignment. Coordinates validation,
    field extraction, and calls to pathogenic/benign assignment functions.

    Args:
        variant: VariantData object to classify
        config: ACMG configuration
        metrics: Optional metrics collector

    Returns:
        ACMGEvidenceSet with assigned evidence codes
    """
    evidence = ACMGEvidenceSet()

    try:
        # Validate variant
        is_valid, errors = validate_variant(variant)
        if not is_valid:
            if metrics:
                metrics.record_validation_error()
            for error in errors:
                evidence.conflicts.add(f"Validation error: {error}")
            logger.warning(f"Validation failed: {errors}")
            return evidence

        # Extract fields
        sig_lower = normalize_text(variant.clinical_sig)
        genes = extract_genes(variant.gene)
        consequence = normalize_text(variant.molecular_consequence)

        # Early exit optimization for empty molecular consequence
        if not consequence:
            logger.debug("Empty molecular consequence, skipping evidence assignment")
            return evidence

        # Check for conflicting interpretations
        if "conflict" in sig_lower or "/" in variant.clinical_sig:
            evidence.conflicts.add("ClinVar conflicting interpretations")

        # Assign pathogenic evidence
        assign_pathogenic_evidence(
            evidence, variant, genes, consequence, sig_lower, config
        )

        # Assign benign evidence
        assign_benign_evidence(evidence, variant, genes, consequence, sig_lower, config)

        # Convert sets to lists
        for attr in ["pvs", "ps", "pm", "pp", "ba", "bs", "bp"]:
            setattr(evidence, attr, list(getattr(evidence, attr)))

        return evidence

    except Exception as e:
        logger.error(f"Evidence assignment failed: {e}", exc_info=True)
        evidence.conflicts.add(f"Assignment error: {str(e)}")
        return evidence
