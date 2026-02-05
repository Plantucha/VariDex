"""
Command-line interface for VariDex pipeline with integrated gnomAD support.

Development version v7.2.0_dev - Full ACMG + gnomAD pipeline.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional
import pandas as pd
from varidex.io.loaders.clinvar import load_clinvar_vcf
from varidex.io.loaders.user import load_user_file
from varidex.pipeline.matcher import match_variants_hybrid
from varidex.pipeline.gnomad_stage import GnomadAnnotationStage
from varidex.pipeline.acmg_classifier_stage import apply_full_acmg_classification
from varidex.pipeline.phase1_enhancer import apply_phase1_enhancements


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="VariDex ACMG Variant Classification Pipeline with gnomAD",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full pipeline with gnomAD
  python3 -m varidex.pipeline \
      --clinvar clinvar/clinvar_GRCh37.vcf.gz \
      --user-genome data/rawM.txt \
      --gnomad-dir gnomad/ \
      --output results/

  # Quick re-run using cached matching
  python3 -m varidex.pipeline --output results/

  # Without gnomAD (BA1, BS1, PM2 criteria skipped)
  python3 -m varidex.pipeline \
      --clinvar clinvar/clinvar_GRCh37.vcf.gz \
      --user-genome data/rawM.txt \
      --output results/
        """,
    )

    parser.add_argument(
        "--clinvar",
        type=str,
        help="Path to ClinVar VCF file (e.g., clinvar_GRCh37.vcf.gz)",
    )

    parser.add_argument(
        "--user-genome",
        type=str,
        help="Path to user genome file (VCF, 23andMe txt, or CSV)",
    )

    parser.add_argument(
        "--gnomad-dir",
        type=str,
        help="Path to directory containing gnomAD VCF files (enables BA1/BS1/PM2)",
    )

    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Output directory for results",
    )

    parser.add_argument(
        "--use-cache",
        action="store_true",
        default=True,
        help="Use cached matching results if available (default: True)",
    )

    parser.add_argument(
        "--force-reload",
        action="store_true",
        help="Force reload and matching even if cache exists",
    )

    parser.add_argument(
        "--build",
        type=str,
        default="GRCh37",
        choices=["GRCh37", "GRCh38"],
        help="Genome build (default: GRCh37)",
    )

    return parser.parse_args()


def run_pipeline_integrated(
    clinvar_path: Optional[str],
    user_genome_path: Optional[str],
    gnomad_dir: Optional[str],
    output_dir: str,
    use_cache: bool = True,
    force_reload: bool = False,
    build: str = "GRCh37",
):
    """
    Run the integrated VariDex pipeline with optional gnomAD annotation.

    Args:
        clinvar_path: Path to ClinVar VCF
        user_genome_path: Path to user genome file
        gnomad_dir: Path to gnomAD directory (None = skip gnomAD)
        output_dir: Output directory
        use_cache: Whether to use cached results
        force_reload: Force reload even with cache
        build: Genome build version
    """
    print("=" * 70)
    print("🧬 VariDex v7.2.0_dev - Integrated ACMG + gnomAD Pipeline")
    print("=" * 70)
    print()

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    cache_file = Path("output/complete_results.csv")

    # Stage 1 & 2: Load and match variants (or use cache)
    if use_cache and cache_file.exists() and not force_reload:
        print(f"✅ Using cached results: {cache_file}")
        print(f"   (Use --force-reload to regenerate)")
        matched_df = pd.read_csv(cache_file)
        print(f"✅ Loaded {len(matched_df):,} variants\n")
    else:
        if not clinvar_path or not user_genome_path:
            print("❌ Error: --clinvar and --user-genome required for initial run")
            sys.exit(1)

        print(f"📥 Step 1: Setup genomic data...")
        print(f"✅ ClinVar: {clinvar_path}")
        print(f"✅ User genome: {user_genome_path}")
        if gnomad_dir:
            print(f"✅ gnomAD: {gnomad_dir}")
        print()

        print("📖 Step 2: Loading ClinVar...")
        clinvar_df = load_clinvar_vcf(clinvar_path)
        print(f"✅ Loaded {len(clinvar_df):,} ClinVar variants\n")

        print("📖 Step 3: Loading your genome...")
        user_df = load_user_file(user_genome_path)
        print(f"✅ Loaded {len(user_df):,} variants from your genome\n")

        print("🔗 Step 4: Matching variants (hybrid: rsID + coordinates)...")
        matched_df = match_variants_hybrid(user_df, clinvar_df)

        # Save cache
        cache_file.parent.mkdir(exist_ok=True)
        matched_df.to_csv(cache_file, index=False)

    # Stage 3: gnomAD annotation (if enabled)
    gnomad_stage = GnomadAnnotationStage(Path(gnomad_dir) if gnomad_dir else None)
    matched_df = gnomad_stage.process(matched_df)

    # Stage 4: ACMG Classification (base codes)
    print("🔬 Step 5: Applying ACMG classification (base codes)...")
    classified_df = apply_full_acmg_classification(matched_df)
    print("✅ Complete\n")

    # Stage 5: Phase 1 Enhancements (+5 codes)
    print("⭐ Step 6: Applying Phase 1 enhancements (+5 codes)...")
    final_df = apply_phase1_enhancements(classified_df)
    print("✅ Complete\n")

    # Stage 6: Save results
    print("💾 Step 7: Saving results...")
    _write_output_files(final_df, output_path)
    print(f"✅ Saved to {output_path.resolve()}/\n")

    # Final summary
    print("=" * 70)
    print("✅ PIPELINE COMPLETE - Integrated ACMG + gnomAD")
    print("=" * 70)
    print()

    _print_summary(final_df)


def _write_output_files(df: pd.DataFrame, output_path: Path):
    """Write all output files to the specified directory."""
    # Main results file
    df.to_csv(output_path / "results_13codes.csv", index=False)

    # Priority files
    if "PVS1" in df.columns:
        pvs1_df = df[df["PVS1"] == True]
        pvs1_df.to_csv(output_path / "PRIORITY_PVS1.csv", index=False)

    if "PM2" in df.columns:
        pm2_df = df[df["PM2"] == True]
        pm2_df.to_csv(output_path / "PRIORITY_PM2.csv", index=False)

    # All pathogenic variants
    if "acmg_final_auto" in df.columns:
        pathogenic_df = df[df["acmg_final_auto"].str.contains("Pathogenic", na=False)]
        if len(pathogenic_df) > 0:
            pathogenic_df.to_csv(output_path / "ALL_PATHOGENIC.csv", index=False)


def _print_summary(df: pd.DataFrame):
    """Print final pipeline summary statistics."""
    evidence_cols = ["BA1", "BS1", "PM2", "PVS1", "BP7", "PP5", "BP6", "BS2"]
    existing_cols = [c for c in evidence_cols if c in df.columns]

    if existing_cols:
        evidence_mask = df[existing_cols].any(axis=1)
        with_evidence = evidence_mask.sum()
    else:
        with_evidence = 0

    pathogenic_count = 0
    if "acmg_final_auto" in df.columns:
        pathogenic_mask = df["acmg_final_auto"].str.contains("Pathogenic", na=False)
        pathogenic_count = pathogenic_mask.sum()

    print("📊 Results:")
    print(f"  Total variants: {len(df):,}")
    print(f"  With evidence: {with_evidence:,} ({with_evidence/len(df)*100:.1f}%)")
    print(f"  Pathogenic: {pathogenic_count:,}")
    print()

    pvs1_count = df.get("PVS1", pd.Series([False])).sum()
    pm2_count = df.get("PM2", pd.Series([False])).sum()

    print("🎯 Priority:")
    print(f"  PVS1 (loss of function): {pvs1_count:,}")
    print(f"  PM2 (rare pathogenic): {pm2_count:,}")
    print()

    print("📁 Output files:")
    print("  • results_13codes.csv")
    print("  • PRIORITY_PVS1.csv")
    print("  • PRIORITY_PM2.csv")
    if pathogenic_count > 0:
        print("  • ALL_PATHOGENIC.csv")
    print("=" * 70)


def main():
    """Main entry point for CLI."""
    args = parse_args()

    run_pipeline_integrated(
        clinvar_path=args.clinvar,
        user_genome_path=args.user_genome,
        gnomad_dir=args.gnomad_dir,
        output_dir=args.output,
        use_cache=args.use_cache and not args.force_reload,
        force_reload=args.force_reload,
        build=args.build,
    )


if __name__ == "__main__":
    main()
