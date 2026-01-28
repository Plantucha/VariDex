#!/usr/bin/env python3
"""
VariDex v6.0.0 COMPLETE Pipeline CLI + Auto-Downloader
"""

import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Any, List, Dict

from varidex import __version__
from varidex.downloader import setup_genomic_data  # type: ignore[attr-defined]
from varidex.pipeline.orchestrator import (
    execute_stage5_acmg_classification,
    PipelineState,
)
from varidex.io.loaders.clinvar import load_clinvar_file  # type: ignore[import]
from varidex.io.loaders.user import load_user_file  # type: ignore[import]


def main() -> None:
    parser = ArgumentParser(
        description=f"VariDex v{__version__} - Genome + ClinVar ACMG"
    )
    parser.add_argument("--clinvar", help="ClinVar VCF (auto-downloads if missing)")
    parser.add_argument("--user-genome", required=True, help="YOUR genome VCF/23andMe")
    parser.add_argument("--output", default="michal_results", help="Results directory")
    parser.add_argument(
        "--download-clinvar", action="store_true", help="Auto-download ClinVar"
    )
    parser.add_argument("--threads", type=int, default=4)

    args: Namespace = parser.parse_args()

    # Auto-download if requested/missing
    if args.download_clinvar or not args.clinvar:
        print("📥 Auto-downloading ClinVar...")
        data_paths: Dict[str, Any] = setup_genomic_data(clinvar_size="small")
        args.clinvar = str(data_paths["clinvar"])

    print(f"🧬 Analyzing {args.user_genome} vs ClinVar...")

    state: PipelineState = PipelineState()
    clinvar_data = load_clinvar_file(args.clinvar)
    user_data = load_user_file(args.user_genome)

    # Match variants first
    from varidex.io.matching import match_variants_hybrid

    result = match_variants_hybrid(
        clinvar_data, user_data, clinvar_type="vcf", user_type="23andme"
    )

    # Handle whatever is returned
    if isinstance(result, tuple):
        matched_df = result[0]
    else:
        matched_df = result

    print(f"✅ Matched: {len(matched_df):,} variants")

    # Now run ACMG classification on matched variants
    safeguard_config = {"max_variants": 1000000, "allow_parallel": True}

    # Stage 5 returns (classified_variants, stats)
    stage5_result = execute_stage5_acmg_classification(
        matched_df,
        safeguard_config=safeguard_config,
        clinvar_type="vcf",
        user_type="23andme",
    )

    # Unpack the tuple
    if isinstance(stage5_result, tuple):
        results, classification_stats = stage5_result
    else:
        results = stage5_result
        classification_stats = {}

    # Stage 6: Convert to DataFrame (results are already dicts)
    import pandas as pd

    results_df = pd.DataFrame(results) if results else pd.DataFrame()

    # Stage 7: Generate all reports (CSV, JSON, HTML)
    from varidex.pipeline.stages import execute_stage7_generate_reports
    import varidex.reports as reports

    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    stats = {
        "total": len(results_df),
        "pathogenic": (
            len(
                results_df[
                    results_df.get("acmg_final", results_df.get("classification", ""))
                    == "P"
                ]
            )
            if len(results_df) > 0
            else 0
        ),
        "likely_pathogenic": (
            len(
                results_df[
                    results_df.get("acmg_final", results_df.get("classification", ""))
                    == "LP"
                ]
            )
            if len(results_df) > 0
            else 0
        ),
    }

    report_files = execute_stage7_generate_reports(
        results_df, stats, output_path, reports
    )

    print(f"\n🔴 PATHOGENIC: {stats.get('pathogenic', 0)}")
    print(f"🟠 LIKELY PATHOGENIC: {stats.get('likely_pathogenic', 0)}")
    print(f"📁 Reports: {output_path}/")
    for report_file in report_files:
        print(
            f"   ✓ {report_file.name if hasattr(report_file, 'name') else Path(report_file).name}"
        )
    print("\n✅ COMPLETE")


if __name__ == "__main__":
    main()
