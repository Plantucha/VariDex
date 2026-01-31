#!/usr/bin/env python3
"""
varidex/core/classifier/evidence_assignment_gnomad.py v6.5.0-dev
===================================================================
ACMG evidence assignment with gnomAD integration.

Enhances evidence_assignment.py with population frequency data:
- PM2: Absent/rare in gnomAD (AF < 0.01%)
- BA1: Common in gnomAD (AF > 5%)
- BS1: High frequency in gnomAD (AF > 1%)

Falls back to text-based heuristics if gnomAD data unavailable.

Author: VariDex Team
Version: 6.5.0-dev
Date: 2026-01-31
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


def get_gnomad_af(variant: VariantData) -> Optional[float]:
    """
    Extract gnomAD allele frequency from variant annotations.

    Args:
        variant: VariantData object with annotations

    Returns:
        Allele frequency or None if not available
    """
    try:
        # Check variant annotations dict
        if hasattr(variant, "annotations") and variant.annotations:
            # Try common gnomAD field names
            for field in ["gnomad_af", "gnomad_genome_af", "gnomad_popmax_af", "af"]:
                if field in variant.annotations:
                    af = variant.annotations[field]
                    if af is not None and af != "" and af != ".":
                        return float(af)

        # Check direct attributes
        for attr in ["gnomad_af", "allele_frequency", "af"]:
            if hasattr(variant, attr):
                af = getattr(variant, attr)
                if af is not None:
                    return float(af)

        return None

    except (ValueError, TypeError) as e:
        logger.debug(f"Failed to parse gnomAD AF: {e}")
        return None


def assign_pathogenic_evidence_gnomad(
    evidence: ACMGEvidenceSet,
    variant: VariantData,
    genes: Set[str],
    consequence: str,
    sig_lower: str,
    config: ACMGConfig,
) -> None:
    """
    Assign pathogenic evidence codes with gnomAD integration.

    Evidence codes:
    - PVS1: LOF in LOF-intolerant genes
    - PM2: Absent/rare in gnomAD (NEW: uses actual AF)
    - PM4: Protein length changes
    - PP2: Missense in missense-rare genes

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

    # PM2: Absent/rare in population databases (gnomAD-aware)
    if config.enable_pm2:
        try:
            gnomad_af = get_gnomad_af(variant)

            if gnomad_af is not None:
                # Use actual gnomAD frequency
                pm2_threshold = getattr(config, "pm2_threshold", 0.0001)

                if gnomad_af < pm2_threshold:
                    evidence.pm.add("PM2")
                    logger.debug(f"PM2: Rare in gnomAD (AF={gnomad_af:.6f})")
                else:
                    logger.debug(
                        f"PM2 not applied: gnomAD AF={gnomad_af:.6f} "
                        f">= {pm2_threshold}"
                    )
            else:
                # Fallback to text-based heuristics
                if "rare" in sig_lower or "novel" in sig_lower:
                    evidence.pm.add("PM2")
                    logger.debug("PM2: Rare variant (text-based)")
                else:
                    logger.debug("PM2: No gnomAD data, no text evidence")

        except Exception as e:
            logger.error(f"PM2 assignment failed: {e}")

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


def assign_benign_evidence_gnomad(
    evidence: ACMGEvidenceSet,
    variant: VariantData,
    genes: Set[str],
    consequence: str,
    sig_lower: str,
    config: ACMGConfig,
) -> None:
    """
    Assign benign evidence codes with gnomAD integration.

    Evidence codes:
    - BA1: Common polymorphism in gnomAD (NEW: uses actual AF)
    - BS1: High population frequency in gnomAD (NEW: uses actual AF)
    - BP1: Missense in LOF genes
    - BP3: In-frame indel in repetitive region

    Args:
        evidence: ACMGEvidenceSet to populate
        variant: VariantData object
        genes: Set of gene symbols
        consequence: Normalized molecular consequence
        sig_lower: Normalized clinical significance
        config: ACMG configuration
    """
    # Get gnomAD frequency for BA1/BS1
    gnomad_af = get_gnomad_af(variant)

    # BA1: Stand-alone benign (AF > 5%)
    if config.enable_ba1:
        try:
            ba1_threshold = getattr(config, "ba1_threshold", 0.05)

            if gnomad_af is not None:
                # Use actual gnomAD frequency
                if gnomad_af >= ba1_threshold:
                    evidence.ba.add("BA1")
                    logger.debug(f"BA1: Common in gnomAD (AF={gnomad_af:.4f})")
            else:
                # Fallback to text-based
                if "common" in sig_lower and "polymorphism" in sig_lower:
                    evidence.ba.add("BA1")
                    logger.debug("BA1: Common polymorphism (text-based)")

        except Exception as e:
            logger.error(f"BA1 assignment failed: {e}")

    # BS1: High population frequency (AF > 1%)
    if config.enable_bs1:
        try:
            bs1_threshold = getattr(config, "bs1_threshold", 0.01)

            if gnomad_af is not None:
                # Use actual gnomAD frequency
                # BS1 should NOT be assigned if BA1 already applies
                ba1_threshold = getattr(config, "ba1_threshold", 0.05)

                if bs1_threshold <= gnomad_af < ba1_threshold:
                    evidence.bs.add("BS1")
                    logger.debug(f"BS1: High frequency in gnomAD (AF={gnomad_af:.4f})")
            else:
                # Fallback to text-based
                if (
                    "population" in sig_lower
                    and "frequency" in sig_lower
                    and "high" in sig_lower
                ) or ("common" in sig_lower and "pathogenic" not in sig_lower):
                    evidence.bs.add("BS1")
                    logger.debug("BS1: High frequency (text-based)")

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


def assign_evidence_codes_gnomad(
    variant: VariantData, config: ACMGConfig, metrics: Optional[any] = None
) -> ACMGEvidenceSet:
    """
    Assign ACMG evidence codes with gnomAD integration.

    Main entry point for evidence assignment. Uses gnomAD allele frequencies
    when available, falls back to text-based heuristics otherwise.

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

        # Log gnomAD availability
        gnomad_af = get_gnomad_af(variant)
        if gnomad_af is not None:
            logger.debug(f"gnomAD AF available: {gnomad_af:.6f}")
        else:
            logger.debug("gnomAD AF not available, using text-based fallback")

        # Assign pathogenic evidence (with gnomAD PM2)
        assign_pathogenic_evidence_gnomad(
            evidence, variant, genes, consequence, sig_lower, config
        )

        # Assign benign evidence (with gnomAD BA1/BS1)
        assign_benign_evidence_gnomad(
            evidence, variant, genes, consequence, sig_lower, config
        )

        # Convert sets to lists
        for attr in ["pvs", "ps", "pm", "pp", "ba", "bs", "bp"]:
            setattr(evidence, attr, list(getattr(evidence, attr)))

        return evidence

    except Exception as e:
        logger.error(f"Evidence assignment failed: {e}", exc_info=True)
        evidence.conflicts.add(f"Assignment error: {str(e)}")
        return evidence
