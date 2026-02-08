#!/usr/bin/env python3
"""
varidex/pipeline/acmg_classifier_stage.py

Full ACMG classification stage with PM2 + BA4/BP2 support - 22 codes!
Version: 1.1.0-dev (BA4/BP2 integrated)
"""

import logging
from typing import Any, Dict, Tuple

import pandas as pd

from varidex.core.classifier.config import ACMGConfig
from varidex.acmg.criteria_ba4_bp2 import BA4BP2Classifier
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


def classify_from_evidence(
    evidence: ACMGEvidenceSet, ba4: bool = False
) -> Tuple[str, str]:
    """Apply ACMG classification rules with BA4 support."""
    pvs_count = len(evidence.pvs)
    pm_count = len(evidence.pm)
    pp_count = len(evidence.pp)
    ba_count = len(evidence.ba)
    bs_count = len(evidence.bs)
    bp_count = len(evidence.bp)

    summary = evidence_summary(evidence)

    # BA4 is stand-alone benign criterion
    if ba_count > 1 or ba4:
        return "Benign", f"BA4 ({summary})" if ba4 else f"Multiple BA ({summary})"

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
    """Classify a single variant with ACMG criteria including BA4/BP2."""
    try:
        variant = VariantData(
            chromosome=str(row.get("chromosome_clinvar", row.get("chromosome"))),
            position=str(row.get("position_clinvar", row.get("position"))),
            ref=str(row["ref_allele"]),
            alt=str(row["alt_allele"]),
        )

        variant.gene = str(row.get("gene", ""))
        variant.molecular_consequence = str(row.get("molecular_consequence", ""))

        if pd.notna(row.get("gnomad_af")):
            object.__setattr__(variant, "gnomad_af", float(row["gnomad_af"]))

        evidence = assign_evidence_codes(variant, config)

        # Pass BA4 status to classification function
        ba4_status = row.get("BA4", False)
        classification, reason = classify_from_evidence(evidence, ba4=ba4_status)

        return {
            "PVS1": "PVS1" in evidence.pvs,
            "PM2": "PM2" in evidence.pm,
            "PM4": "PM4" in evidence.pm,
            "PP2": "PP2" in evidence.pp,
            "BA1": "BA1" in evidence.ba,
            "BS1": "BS1" in evidence.bs,
            "BP1": "BP1" in evidence.bp,
            "BP3": "BP3" in evidence.bp,
            "BA4": ba4_status,
            "BP2": row.get("BP2", False),
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
            "BA4": False,
            "BP2": False,
            "acmg_classification": "Uncertain Significance",
            "classification_reason": "Error",
            "evidence_summary": "",
        }


def apply_full_acmg_classification(
    df: pd.DataFrame, gnomad_constraint_path: str = None
) -> pd.DataFrame:
    """Apply full ACMG classification to all variants (22 codes with BA4/BP2)."""
    logger.info("🧬 Applying full ACMG classification (22 codes)...")

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

    # Initialize all ACMG code columns if not present
    for code in [
        "PVS1",
        "PM2",
        "PM4",
        "PP2",
        "BA1",
        "BS1",
        "BP1",
        "BP3",
        "BA4",
        "BP2",
    ]:
        if code not in result.columns:
            result[code] = False

    result["acmg_classification"] = "Uncertain Significance"
    result["classification_reason"] = ""
    result["evidence_summary"] = ""

    # Apply BA4/BP2 criteria BEFORE main classification
    if gnomad_constraint_path:
        logger.info("Applying BA4/BP2 (LoF constraint + homozygotes)...")
        try:
            ba4_bp2 = BA4BP2Classifier(constraint_path=gnomad_constraint_path)
            result = ba4_bp2.apply(result)
        except Exception as e:
            logger.warning(f"BA4/BP2 application failed: {e}")
    else:
        logger.warning("gnomad_constraint_path not provided - skipping BA4/BP2")

    # Apply main ACMG classification
    for idx, row in result.iterrows():
        classification_result = classify_variant_with_acmg(row, config)
        for key, value in classification_result.items():
            result.at[idx, key] = value

    logger.info(f"✅ Classified {len(result):,} variants")

    # Report statistics for all codes
    for code in [
        "PVS1",
        "PM2",
        "PM4",
        "PP2",
        "BA1",
        "BS1",
        "BP1",
        "BP3",
        "BA4",
        "BP2",
    ]:
        count = result[code].sum()
        pct = count / len(result) * 100
        if count > 0:
            logger.info(f"  {code}: {count:,} ({pct:.1f}%)")

    return result
