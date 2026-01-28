#!/usr/bin/env python3
"""
Enhanced orchestrator with gnomAD and full ACMG criteria.
Extends existing pipeline with stages 4b and 4c.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
import pandas as pd

# Import existing orchestrator functions
from varidex.pipeline.orchestrator import (
    configure_logging,
    PipelineState,
    _IMPORT_MODE,
    loader,
    reports,
)

from varidex.pipeline.stages import (
    execute_stage2_load_clinvar,
    execute_stage3_load_user_data,
    execute_stage4_hybrid_matching,
    execute_stage4b_gnomad_annotation,
    execute_stage4c_consequence_criteria,
    execute_stage5_acmg_classification,
    execute_stage6_create_results,
    execute_stage7_generate_reports,
)

from varidex.pipeline.cli_helpers import (
    print_pipeline_header,
    print_stage_header,
    print_completion_summary,
)

from varidex.pipeline.pipeline_config import get_safeguard_config, load_yaml_config

logger = logging.getLogger(__name__)


def main_enhanced(
    clinvar_path: str,
    user_genome_path: str,
    output_dir: str = "output",
    gnomad_dir: str = "gnomad",
    enable_gnomad: bool = True,
    config_file: Optional[str] = None,
) -> Dict:
    """
    Enhanced pipeline with gnomAD annotation and full ACMG criteria.

    Pipeline stages:
    1. Setup
    2. Load ClinVar
    3. Load user genome
    4. Match variants
    4b. gnomAD annotation (NEW)
    4c. Consequence criteria (NEW)
    5. ACMG classification
    6. Create results
    7. Generate reports
    """
    logger = configure_logging()
    start_time = datetime.now()

    print_pipeline_header()
    print("VARIDEX ENHANCED v6.4.0-dev")
    print(f"gnomAD: {'✓ Enabled' if enable_gnomad else '✗ Disabled'}")
    print("=" * 70)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    checkpoint_dir = output_path / "checkpoints"
    checkpoint_dir.mkdir(exist_ok=True)

    # Load config
    yaml_config = load_yaml_config(Path(config_file)) if config_file else {}
    safeguard_config = get_safeguard_config(yaml_config)

    total_stages = 7 if enable_gnomad else 5

    try:
        # Stage 2: Load ClinVar
        print_stage_header(2, total_stages, "Loading ClinVar")
        clinvar_data = execute_stage2_load_clinvar(
            Path(clinvar_path), checkpoint_dir, loader, safeguard_config
        )
        logger.info(f"✓ Loaded {len(clinvar_data):,} ClinVar variants")

        # Stage 3: Load user genome
        print_stage_header(3, total_stages, "Loading User Genome")
        user_data = execute_stage3_load_user_data(
            Path(user_genome_path), "23andme", loader
        )
        logger.info(f"✓ Loaded {len(user_data):,} user variants")

        # Stage 4: Match variants
        print_stage_header(4, total_stages, "Matching Variants")
        match_result = execute_stage4_hybrid_matching(
            clinvar_data,
            user_data,
            "vcf",
            "23andme",
            loader,
            safeguard_config,
            _IMPORT_MODE,
        )

        # Unpack result (could be tuple or DataFrame)
        if isinstance(match_result, tuple):
            matched_df, rsid_matches, coord_matches = match_result
        else:
            matched_df = match_result

        logger.info(f"✓ Matched {len(matched_df):,} variants")

        # Save intermediate
        matched_file = output_path / "matched_variants.csv"
        matched_df.to_csv(matched_file, index=False)
        logger.info(f"✓ Saved matched variants to {matched_file}")

        if enable_gnomad:
            # Stage 4b: gnomAD annotation
            print_stage_header(5, total_stages, "gnomAD Annotation (NEW)")
            annotated_df = execute_stage4b_gnomad_annotation(
                matched_df, Path(gnomad_dir), logger
            )

            # Stage 4c: Consequence criteria
            print_stage_header(6, total_stages, "Consequence Criteria (NEW)")
            classified_df = execute_stage4c_consequence_criteria(annotated_df, logger)

            # Save with ACMG criteria
            acmg_file = output_path / "acmg_classified.csv"
            classified_df.to_csv(acmg_file, index=False)
            logger.info(f"✓ Saved ACMG classifications to {acmg_file}")
        else:
            classified_df = matched_df

        # Stage 5: Original ACMG classification (if needed)
        stage_num = 7 if enable_gnomad else 5
        print_stage_header(stage_num, total_stages, "Additional ACMG Rules")
        stage5_result = execute_stage5_acmg_classification(
            classified_df, safeguard_config, "vcf", "23andme", _IMPORT_MODE
        )

        if isinstance(stage5_result, tuple):
            results, classification_stats = stage5_result
        else:
            results = stage5_result
            classification_stats = {}

        # Create results DataFrame
        if results and len(results) > 0:
            results_df = pd.DataFrame(results)
        else:
            results_df = classified_df.copy()

        # Ensure we have ACMG columns if gnomAD was enabled
        if enable_gnomad:
            acmg_cols = [
                "BA1",
                "BS1",
                "PM2",
                "PVS1",
                "BP7",
                "acmg_final_auto",
                "gnomad_af",
            ]
            for col in acmg_cols:
                if col in classified_df.columns and col not in results_df.columns:
                    # Try to merge back
                    key_cols = ["chromosome", "position"]
                    if all(
                        c in classified_df.columns and c in results_df.columns
                        for c in key_cols
                    ):
                        results_df = results_df.merge(
                            classified_df[key_cols + acmg_cols].drop_duplicates(
                                key_cols
                            ),
                            on=key_cols,
                            how="left",
                            suffixes=("", "_acmg"),
                        )
                        break

        # Generate reports
        stats = {
            "total": len(results_df),
            "pathogenic": 0,
            "likely_pathogenic": 0,
        }

        if enable_gnomad and "acmg_final_auto" in results_df.columns:
            stats["pathogenic"] = len(
                results_df[
                    results_df["acmg_final_auto"]
                    .astype(str)
                    .str.contains("Pathogenic", na=False)
                ]
            )
            stats["likely_pathogenic"] = len(
                results_df[
                    results_df["acmg_final_auto"]
                    .astype(str)
                    .str.contains("Likely pathogenic", na=False, case=False)
                ]
            )

        report_files = execute_stage7_generate_reports(
            results_df, stats, output_path, reports
        )

        # Print summary
        duration = (datetime.now() - start_time).total_seconds()
        print("\n" + "=" * 70)
        print("✅ PIPELINE COMPLETE")
        print("=" * 70)
        print(f"⏱️  Runtime: {duration:.1f}s")
        print(f"🧬 Variants analyzed: {len(results_df):,}")
        if enable_gnomad:
            print(f"🔴 Pathogenic: {stats.get('pathogenic', 0):,}")
            print(f"🟠 Likely Pathogenic: {stats.get('likely_pathogenic', 0):,}")
        print(f"\n📁 Output: {output_path}/")
        for rf in report_files:
            fname = rf.name if hasattr(rf, "name") else Path(rf).name
            print(f"   ✓ {fname}")

        return {
            "results": results_df,
            "stats": stats,
            "output_path": output_path,
            "duration": duration,
        }

    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print(
            "Usage: python -m varidex.pipeline.orchestrator_enhanced CLINVAR_VCF USER_GENOME [OUTPUT_DIR] [GNOMAD_DIR]"
        )
        print(
            "Example: python -m varidex.pipeline.orchestrator_enhanced clinvar/clinvar_GRCh37.vcf data/raw.txt"
        )
        sys.exit(1)

    result = main_enhanced(
        clinvar_path=sys.argv[1],
        user_genome_path=sys.argv[2],
        output_dir=sys.argv[3] if len(sys.argv) > 3 else "output",
        gnomad_dir=sys.argv[4] if len(sys.argv) > 4 else "gnomad",
        enable_gnomad=True,
    )
