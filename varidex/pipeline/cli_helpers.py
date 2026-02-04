#!/usr/bin/env python3

"""
varidex/pipeline/cli_helpers.py - CLI Helpers v1.0.0-dev
Command-line interface helpers and output formatting.
Development version - not for production use.
"""

from pathlib import Path
from typing import Dict


def print_pipeline_header() -> None:
    """Print pipeline header."""
    print("=" * 70)
    print("CLINVAR-WGS PIPELINE v7.0.0-dev")
    print("=" * 70)


def print_stage_header(stage_num: int, total: int, title: str) -> None:
    """Print stage header."""
    print()
    print("=" * 70)
    print(f"[{stage_num}/{total}] {title}")
    print("=" * 70)


def print_mode_flags(safeguard_config: Dict, force: bool, interactive: bool) -> None:
    """Print active mode flags."""
    if not safeguard_config["abort_on_threshold"]:
        print("⚠️ GRACEFUL MODE - Warnings won't stop pipeline")
    if force:
        print("⚡ FORCE MODE - Skipping safety checks")
    if not interactive:
        print("🤖 NON-INTERACTIVE - No user prompts")
    print()


def print_completion_summary(
    state, match_rate: float, stats: Dict[str, int], report_files: Dict[str, Path]
) -> None:
    """Print pipeline completion summary."""
    print()
    print("=" * 70)
    print("✅ PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 70)
    print(f"Coverage: {state.matches:,}/{state.user_variants:,} ({match_rate:.1f}%)")
    print(
        f"Pathogenic: {stats.get('pathogenic', 0):,} | "
        f"Likely Pathogenic: {stats.get('likely_pathogenic', 0):,} | "
        f"VUS: {stats.get('vus', 0):,}"
    )
    print()
    print("Output Files:")
    for report_type, file_path in report_files.items():
        print(f" • {report_type.upper()}: {file_path.name}")
    print()
    print("⚠️ RESEARCH USE ONLY")
    print("   Not for clinical diagnosis. Consult a genetic counselor.")
    print("   Reference: Richards et al. 2015 (PMID: 25741868)")
    print("=" * 70)


def print_usage() -> None:
    """Print CLI usage information."""
    print(
        """
CLINVAR-WGS PIPELINE v7.0.0-dev

USAGE:
  python -m varidex.pipeline [OPTIONS]

REQUIRED:
  clinvar_file    ClinVar database (txt, vcf, or tsv)
  user_data       User genomic data (vcf, 23andme, or tsv)

OPTIONS:
  --force                 Skip ClinVar freshness check
  --non-interactive       Disable user prompts
  --format FORMAT         Force format: vcf|23andme|tsv
  --config FILE           YAML configuration file
  --output-dir DIR        Output directory (default: results/)
  --log-file FILE         Log file (default: pipeline.log)
  --help                  Show this help

EXAMPLES:
  python -m varidex.pipeline clinvar.txt genome.txt
  python -m varidex.pipeline clinvar.vcf data.vcf --format vcf --force
  python -m varidex.pipeline clinvar.txt data.txt --output-dir my_results

OUTPUT:
  results/
    ├── classified_variants.csv
    ├── classified_variants.json
    ├── report.html
    └── conflicts_report.txt

⚠️ RESEARCH USE ONLY
   Reference: Richards et al. 2015, PMID 25741868
"""
    )
