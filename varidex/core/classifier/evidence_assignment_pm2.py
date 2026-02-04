#!/usr/bin/env python3
"""
varidex/core/classifier/evidence_assignment_pm2.py

Enhanced evidence assignment with PM2 support for local gnomAD data.

Version: 1.0.1-dev
"""

import logging
from typing import Set

from varidex.core.classifier.config import ACMGConfig
from varidex.core.config import LOF_GENES, MISSENSE_RARE_GENES
from varidex.core.models import ACMGEvidenceSet, VariantData

logger = logging.getLogger(__name__)


def normalize_genes(gene_input: str) -> Set[str]:
    """Extract gene symbols from gene field."""
    if not gene_input or str(gene_input) == "nan":
        return set()

    genes = set()
    for gene in str(gene_input).split(";"):
        gene = gene.strip()
        if gene and gene != "nan":
            genes.add(gene)
    return genes


def check_lof(consequence: str, sig_lower: str = "") -> bool:
    """Check if variant is loss-of-function."""
    if not consequence:
        return False
    lof_terms = [
        "stop_gained",
        "frameshift",
        "splice_acceptor",
        "splice_donor",
        "start_lost",
        "transcript_ablation",
        "nonsense",
        "truncating",
    ]
    return any(term in consequence.lower() for term in lof_terms)


def check_missense(consequence: str) -> bool:
    """Check if variant is missense."""
    if not consequence:
        return False
    return "missense" in consequence.lower()


def check_inframe_indel(consequence: str) -> bool:
    """Check if variant is in-frame indel."""
    if not consequence:
        return False
    inframe_terms = ["inframe_insertion", "inframe_deletion"]
    return any(term in consequence.lower() for term in inframe_terms)


def check_pm2(variant: VariantData, config: ACMGConfig) -> bool:
    """Check PM2: Absent/rare in population databases."""
    if not config.enable_pm2:
        return False

    try:
        if not hasattr(variant, "gnomad_af"):
            return False

        gnomad_af = variant.gnomad_af

        # Absent from gnomAD
        if gnomad_af is None:
            logger.debug("PM2: Absent from gnomAD")
            return True

        # Very rare
        threshold = 0.0001
        if gnomad_af < threshold:
            logger.debug(f"PM2: Rare (AF={gnomad_af:.6f} < {threshold})")
            return True

        return False

    except Exception as e:
        logger.error(f"PM2 check failed: {e}")
        return False


def assign_pathogenic_evidence(
    evidence: ACMGEvidenceSet,
    variant: VariantData,
    genes: Set[str],
    consequence: str,
    config: ACMGConfig,
) -> None:
    """Assign pathogenic evidence codes."""

    # PVS1: LOF in LOF-intolerant genes
    if config.enable_pvs1:
        try:
            if check_lof(consequence):
                matching_genes = genes.intersection(LOF_GENES)
                if matching_genes:
                    evidence.pvs.add("PVS1")
                    logger.debug(f"PVS1: LOF in {matching_genes}")
        except Exception as e:
            logger.error(f"PVS1 failed: {e}")

    # PM4: Protein length changes
    if config.enable_pm4:
        try:
            if check_inframe_indel(consequence):
                evidence.pm.add("PM4")
                logger.debug("PM4: Protein length change")
        except Exception as e:
            logger.error(f"PM4 failed: {e}")

    # PP2: Missense in missense-rare genes
    if config.enable_pp2:
        try:
            if check_missense(consequence):
                matching_genes = genes.intersection(MISSENSE_RARE_GENES)
                if matching_genes:
                    evidence.pp.add("PP2")
                    logger.debug(f"PP2: Missense in {matching_genes}")
        except Exception as e:
            logger.error(f"PP2 failed: {e}")

    # PM2: Absent/rare in population
    if config.enable_pm2:
        try:
            if check_pm2(variant, config):
                evidence.pm.add("PM2")
                logger.debug("PM2: Rare/absent in gnomAD")
        except Exception as e:
            logger.error(f"PM2 failed: {e}")


def assign_benign_evidence(
    evidence: ACMGEvidenceSet,
    variant: VariantData,
    genes: Set[str],
    consequence: str,
    config: ACMGConfig,
) -> None:
    """Assign benign evidence codes."""

    # BA1: Very common (>5%)
    if config.enable_ba1:
        try:
            if hasattr(variant, "gnomad_af") and variant.gnomad_af is not None:
                if variant.gnomad_af > 0.05:
                    evidence.ba.add("BA1")
                    logger.debug(f"BA1: Common (AF={variant.gnomad_af:.4f})")
        except Exception as e:
            logger.error(f"BA1 failed: {e}")

    # BS1: Common (>1%)
    if config.enable_bs1:
        try:
            if hasattr(variant, "gnomad_af") and variant.gnomad_af is not None:
                if 0.01 < variant.gnomad_af <= 0.05:
                    evidence.bs.add("BS1")
                    logger.debug(f"BS1: Moderately common (AF={variant.gnomad_af:.4f})")
        except Exception as e:
            logger.error(f"BS1 failed: {e}")

    # BP1: Missense where LOF is mechanism
    if config.enable_bp1:
        try:
            if check_missense(consequence):
                matching_genes = genes.intersection(LOF_GENES)
                if matching_genes:
                    evidence.bp.add("BP1")
                    logger.debug(f"BP1: Missense in LOF gene {matching_genes}")
        except Exception as e:
            logger.error(f"BP1 failed: {e}")

    # BP3: In-frame indels
    if config.enable_bp3:
        try:
            if check_inframe_indel(consequence):
                if "frameshift" not in consequence:
                    evidence.bp.add("BP3")
                    logger.debug("BP3: In-frame indel")
        except Exception as e:
            logger.error(f"BP3 failed: {e}")


def assign_evidence_codes(
    variant: VariantData, config: ACMGConfig, metrics=None
) -> ACMGEvidenceSet:
    """Assign ACMG evidence codes with PM2 support."""
    evidence = ACMGEvidenceSet()

    # Get fields from VariantData
    gene_str = getattr(variant, "gene", "")
    genes = normalize_genes(gene_str)

    # Use molecular_consequence (not consequence)
    consequence_str = getattr(variant, "molecular_consequence", "")
    consequence = consequence_str.lower() if consequence_str else ""

    # Assign evidence
    assign_pathogenic_evidence(evidence, variant, genes, consequence, config)
    assign_benign_evidence(evidence, variant, genes, consequence, config)

    return evidence
