#!/usr/bin/env python3
"""
varidex/pipeline/acmg_classifier_stage.py

Full ACMG classification stage with PM2 support - WORKING!

Version: 1.0.3-dev
"""

import logging
from typing import Any, Dict, Tuple

import pandas as pd

from varidex.core.classifier.config import ACMGConfig
from varidex.core.classifier.evidence_assignment_pm2 import assign_evidence_codes
from varidex.core.models import ACMGEvidenceSet, VariantData

logger = logging.getLogger(__name__)


def evidence_summary(evidence: ACMGEvidenceSet) -> str:
    """Create summary string from evidence set."""
    codes = []
    codes.extend(sorted(evidence.pvs))
    codes.extend(sorted(evidence.ps))
    codes.extend(sorted(evidence.pm))
    codes.extend(sorted(evidence.pp))
    codes.extend(sorted(evidence.ba))
    codes.extend(sorted(evidence.bs))
    codes.extend(sorted(evidence.bp))
    return ", ".join(codes) if codes else ""


def classify_from_evidence(evidence: ACMGEvidenceSet) -> Tuple[str, str]:
    """Apply ACMG classification rules."""
    pvs_count = len(evidence.pvs)
    pm_count = len(evidence.pm)
    pp_count = len(evidence.pp)
    ba_count = len(evidence.ba)
    bs_count = len(evidence.bs)
    bp_count = len(evidence.bp)

    summary = evidence_summary(evidence)

    if ba_count > 0:
        return "Benign", f"BA1 ({summary})"
    if bs_count >= 2:
        return "Benign", f"Multiple BS ({summary})"
    if bs_count >= 1 and bp_count >= 1:
        return "Likely Benign", f"BS+BP ({summary})"
    if bp_count >= 2:
        return "Likely Benign", f"Multiple BP ({summary})"
    if pvs_count >= 1 and pm_count >= 2:
        return "Pathogenic", f"PVS1+2PM ({summary})"
    if pvs_count >= 1 and pm_count >= 1 and pp_count >= 1:
        return "Pathogenic", f"PVS1+PM+PP ({summary})"
    if pvs_count >= 1 and pm_count >= 1:
        return "Likely Pathogenic", f"PVS1+PM ({summary})"
    if pvs_count > 0 or pm_count > 0 or pp_count > 0 or bs_count > 0 or bp_count > 0:
        return "Uncertain Significance", f"Insufficient ({summary})"
    return "Uncertain Significance", "No evidence"


def classify_variant_with_acmg(row: pd.Series, config: ACMGConfig) -> Dict[str, Any]:
    """Classify a single variant."""
    try:
        variant = VariantData(
            chromosome=str(row.get("chromosome_clinvar", row.get("chromosome"))),  # Use clinvar column
            position=str(row.get("position_clinvar", row.get("position"))),  # Use clinvar column
            ref=str(row["ref_allele"]),
            alt=str(row["alt_allele"]),
        )

        variant.gene = str(row.get("gene", ""))
        variant.molecular_consequence = str(row.get("molecular_consequence", ""))

        if pd.notna(row.get("gnomad_af")):
            object.__setattr__(variant, "gnomad_af", float(row["gnomad_af"]))

        evidence = assign_evidence_codes(variant, config)
        classification, reason = classify_from_evidence(evidence)

        return {
            "PVS1": "PVS1" in evidence.pvs,
            "PM2": "PM2" in evidence.pm,
            "PM4": "PM4" in evidence.pm,
            "PP2": "PP2" in evidence.pp,
            "BA1": "BA1" in evidence.ba,
            "BS1": "BS1" in evidence.bs,
            "BP1": "BP1" in evidence.bp,
            "BP3": "BP3" in evidence.bp,
            "acmg_classification": classification,
            "classification_reason": reason,
            "evidence_summary": evidence_summary(evidence),
        }

    except Exception as e:
        logger.debug(f"Classification error: {e}")
        return {
            "PVS1": False,
            "PM2": False,
            "PM4": False,
            "PP2": False,
            "BA1": False,
            "BS1": False,
            "BP1": False,
            "BP3": False,
            "acmg_classification": "Uncertain Significance",
            "classification_reason": "Error",
            "evidence_summary": "",
        }


def apply_full_acmg_classification(df: pd.DataFrame) -> pd.DataFrame:
    """Apply full ACMG classification to all variants."""
    logger.info("🧬 Applying full ACMG classification (8 codes)...")

    config = ACMGConfig(
        enable_pvs1=True,
        enable_pm2=True,
        enable_pm4=True,
        enable_pp2=True,
        enable_ba1=True,
        enable_bs1=True,
        enable_bp1=True,
        enable_bp3=True,
    )

    result = df.copy()
    # Only initialize codes that don't exist yet (preserve gnomAD codes)
    for code in ["PVS1", "PM2", "PM4", "PP2", "BA1", "BS1", "BP1", "BP3"]:
        if code not in result.columns:
            result[code] = False

    result["acmg_classification"] = "Uncertain Significance"
    result["classification_reason"] = ""
    result["evidence_summary"] = ""

    for idx, row in result.iterrows():
        classification_result = classify_variant_with_acmg(row, config)
        for key, value in classification_result.items():
            result.at[idx, key] = value

    logger.info(f"✅ Classified {len(result):,} variants")

    for code in ["PVS1", "PM2", "PM4", "PP2", "BA1", "BS1", "BP1", "BP3"]:
        count = result[code].sum()
        pct = count / len(result) * 100
        if count > 0:
            logger.info(f"  {code}: {count:,} ({pct:.1f}%)")

    return result
