#!/usr/bin/env python3
"""
varidex/pipeline/orchestrator_v2.py

Complete pipeline orchestrator with 13-code ACMG classification.

Version: 2.0.0-dev
"""

import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

from varidex.io.loaders.clinvar import load_clinvar_vcf
from varidex.io.loaders.user import load_user_file
from varidex.pipeline.acmg_classifier_stage import apply_full_acmg_classification
from varidex.pipeline.gnomad_annotator_local import annotate_with_gnomad_local
from varidex.pipeline.matcher import match_variants

logger = logging.getLogger(__name__)


def apply_phase1_enhancements(df: pd.DataFrame) -> pd.DataFrame:
    """Apply Phase 1 ACMG enhancements (5 additional codes)."""
    logger.info("⭐ Applying Phase 1 enhancements (+5 codes)...")

    result = df.copy()

    # Initialize new columns
    for code in ["PS1", "PM5", "BP7", "BS2", "PP5", "BP6"]:
        result[code] = False

    # BP7: Synonymous variants
    bp7_count = 0
    for idx, row in result.iterrows():
        consequence = str(row.get("molecular_consequence", "")).lower()
        if "synonymous" in consequence or "silent" in consequence:
            if "splice" not in consequence:
                result.at[idx, "BP7"] = True
                bp7_count += 1

    # PP5/BP6: Expert panel reviewed
    pp5_count = 0
    bp6_count = 0
    for idx, row in result.iterrows():
        review_status = str(row.get("review_status", "")).lower()
        clinical_sig = str(row.get("clinical_sig", "")).lower()

        if "expert_panel" in review_status or "practice_guideline" in review_status:
            if "pathogenic" in clinical_sig and "benign" not in clinical_sig:
                result.at[idx, "PP5"] = True
                pp5_count += 1
            elif "benign" in clinical_sig:
                result.at[idx, "BP6"] = True
                bp6_count += 1

    # BS2: Common variants
    bs2_count = 0
    for idx, row in result.iterrows():
        gnomad_af = row.get("gnomad_af")
        clinical_sig = str(row.get("clinical_sig", "")).lower()
        if pd.notna(gnomad_af) and gnomad_af > 0.01:
            if "pathogenic" in clinical_sig and "benign" not in clinical_sig:
                result.at[idx, "BS2"] = True
                bs2_count += 1

    logger.info(f"  ✓ BP7: {bp7_count:,}")
    logger.info(f"  ✓ PP5: {pp5_count:,}")
    logger.info(f"  ✓ BP6: {bp6_count:,}")
    logger.info(f"  ✓ BS2: {bs2_count:,}")

    return result


def generate_priority_files(df: pd.DataFrame, output_dir: Path) -> Dict[str, int]:
    """Generate priority output files."""
    logger.info("📊 Generating priority files...")

    counts = {}

    # Priority 1: PVS1
    pathogenic = df[df["clinical_sig"].str.contains("athogenic", na=False, case=False)]
    pvs1 = pathogenic[pathogenic["PVS1"]]
    pvs1_file = output_dir / "PRIORITY_1_PVS1_loss_of_function.csv"
    pvs1.to_csv(pvs1_file, index=False)
    counts["pvs1"] = len(pvs1)
    logger.info(f"  Priority 1 (PVS1): {len(pvs1):,} variants")

    # Priority 2: PM2
    pm2 = pathogenic[pathogenic["PM2"]]
    pm2_file = output_dir / "PRIORITY_2_PM2_rare_pathogenic.csv"
    pm2.to_csv(pm2_file, index=False)
    counts["pm2"] = len(pm2)
    logger.info(f"  Priority 2 (PM2): {len(pm2):,} variants")

    # Benign: BA1
    benign = df[df["clinical_sig"].str.contains("enign", na=False, case=False)]
    ba1 = benign[benign["BA1"]]
    ba1_file = output_dir / "benign_BA1_common.csv"
    ba1.to_csv(ba1_file, index=False)
    counts["ba1"] = len(ba1)
    logger.info(f"  Benign (BA1): {len(ba1):,} variants")

    return counts


def find_genome_file() -> Optional[Path]:
    """Auto-detect user genome file in current directory."""
    patterns = ["genome_*.txt", "*.23andme.txt", "*.ancestry.txt"]

    for pattern in patterns:
        files = list(Path(".").glob(pattern))
        if files:
            return files[0]

    return None


def run_complete_pipeline(
    user_genome_file: str,
    clinvar_file: str = "clinvar/clinvar_GRCh37.vcf.gz",
    gnomad_file: Optional[str] = "gnomad_v3.1_GRCh37_cleaned.csv",
    output_dir: str = "output",
    enable_phase1: bool = True,
) -> Dict[str, Any]:
    """
    Run complete VariDex pipeline with 13-code ACMG classification.

    Args:
        user_genome_file: Path to user genome file
        clinvar_file: Path to ClinVar VCF
        gnomad_file: Path to gnomAD CSV (optional)
        output_dir: Output directory
        enable_phase1: Enable Phase 1 enhancements

    Returns:
        Dict with pipeline statistics
    """
    start_time = datetime.now()
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    print("=" * 80)
    print("VariDex Complete Pipeline v2.0")
    print("=" * 80)
    print(f"13-Code ACMG Classification\n")

    stats = {}

    # Step 1: Load ClinVar
    logger.info("Step 1/6: Loading ClinVar...")
    clinvar_df = load_clinvar_vcf(clinvar_file)
    stats["clinvar_variants"] = len(clinvar_df)
    logger.info(f"✅ {stats['clinvar_variants']:,} ClinVar variants")

    # Step 2: Load user genome
    logger.info("\nStep 2/6: Loading user genome...")
    user_df = load_user_file(Path(user_genome_file))
    stats["user_variants"] = len(user_df)
    logger.info(f"✅ {stats['user_variants']:,} user variants")

    # Step 3: Match variants
    logger.info("\nStep 3/6: Matching with ClinVar...")
    matched_df = match_variants(user_df, clinvar_df)
    stats["matched_variants"] = len(matched_df)
    logger.info(f"✅ {stats['matched_variants']:,} matched")

    # Step 4: Annotate with gnomAD
    if gnomad_file and Path(gnomad_file).exists():
        logger.info("\nStep 4/6: Annotating with gnomAD...")
        annotated_df = annotate_with_gnomad_local(matched_df, gnomad_file)
        stats["gnomad_annotated"] = (annotated_df["gnomad_af"].notna()).sum()
        logger.info(f"✅ {stats['gnomad_annotated']:,} annotated")
    else:
        logger.warning("\nStep 4/6: Skipping gnomAD (file not found)")
        annotated_df = matched_df
        annotated_df["gnomad_af"] = None
        stats["gnomad_annotated"] = 0

    # Step 5: Base ACMG (8 codes)
    logger.info("\nStep 5/6: ACMG classification (8 codes)...")
    acmg_df = apply_full_acmg_classification(annotated_df)

    # Step 6: Phase 1 (+5 codes)
    if enable_phase1:
        logger.info("\nStep 6/6: Phase 1 enhancements...")
        final_df = apply_phase1_enhancements(acmg_df)
        stats["total_codes"] = 13
    else:
        final_df = acmg_df
        stats["total_codes"] = 8

    # Save main results
    main_file = output_path / "complete_results_13codes.csv"
    final_df.to_csv(main_file, index=False)
    logger.info(f"\n💾 Saved: {main_file}")

    # Generate priority files
    priority_counts = generate_priority_files(final_df, output_path)
    stats.update(priority_counts)

    # Calculate coverage
    all_codes = [
        "PVS1",
        "PS1",
        "PM2",
        "PM4",
        "PM5",
        "PP2",
        "PP5",
        "BA1",
        "BS1",
        "BS2",
        "BP1",
        "BP3",
        "BP6",
        "BP7",
    ]
    has_evidence = final_df[all_codes].any(axis=1)
    stats["variants_with_evidence"] = has_evidence.sum()
    stats["coverage"] = stats["variants_with_evidence"] / len(final_df) * 100

    # Runtime
    stats["runtime"] = (datetime.now() - start_time).total_seconds()

    # Summary
    print("\n" + "=" * 80)
    print("✅ PIPELINE COMPLETE!")
    print("=" * 80)
    print(f"\n📊 Results:")
    print(f"  Total variants: {len(final_df):,}")
    print(
        f"  With evidence: {stats['variants_with_evidence']:,} ({stats['coverage']:.1f}%)"
    )
    print(f"  ACMG codes: {stats['total_codes']}")
    print(f"  Runtime: {stats['runtime']:.1f}s")
    print(f"\n📁 Output: {output_path.absolute()}")
    print("=" * 80)

    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VariDex 13-code ACMG Pipeline")
    parser.add_argument(
        "--genome", help="User genome file (auto-detect if not specified)"
    )
    parser.add_argument(
        "--clinvar", default="clinvar/clinvar_GRCh37.vcf.gz", help="ClinVar VCF file"
    )
    parser.add_argument(
        "--gnomad", default="gnomad_v3.1_GRCh37_cleaned.csv", help="gnomAD CSV file"
    )
    parser.add_argument("--output", default="output", help="Output directory")
    parser.add_argument(
        "--no-phase1", action="store_true", help="Disable Phase 1 enhancements"
    )

    args = parser.parse_args()

    # Auto-detect genome file if not specified
    genome_file = args.genome
    if not genome_file:
        genome_file = find_genome_file()
        if not genome_file:
            print("❌ No genome file found. Specify with --genome")
            exit(1)
        print(f"📂 Auto-detected genome file: {genome_file}\n")

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    stats = run_complete_pipeline(
        user_genome_file=str(genome_file),
        clinvar_file=args.clinvar,
        gnomad_file=args.gnomad,
        output_dir=args.output,
        enable_phase1=not args.no_phase1,
    )
