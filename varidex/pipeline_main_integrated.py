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
from varidex.io.writers import write_results
from varidex.pipeline.acmg_classifier_stage import ACMGClassifierStage
from varidex.pipeline.gnomad_stage import GnomadAnnotationStage
from varidex.pipeline.matcher import match_variants_hybrid
from varidex.pipeline.phase1_enhancer import Phase1EnhancementStage


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

        rsid_matches = matched_df["rsid"].notna().sum() if "rsid" in matched_df else 0
        coord_matches = len(matched_df) - rsid_matches

        print(f"✅ Matched {len(matched_df):,} variants:")
        print(f"   • rsID matches: {rsid_matches:,}")
        print(f"   • Coordinate matches: {coord_matches:,}\n")

        # Save cache
        cache_file.parent.mkdir(exist_ok=True)
        matched_df.to_csv(cache_file, index=False)

    # Stage 3: gnomAD annotation (if enabled)
    gnomad_stage = GnomadAnnotationStage(Path(gnomad_dir) if gnomad_dir else None)
    matched_df = gnomad_stage.process(matched_df)

    # Stage 4: ACMG Classification (base 8 codes)
    print("🔬 Step 5: Applying ACMG classification (base codes)...")
    acmg_stage = ACMGClassifierStage()
    classified_df = acmg_stage.process(matched_df)
    print("✅ Complete\n")

    # Stage 5: Phase 1 Enhancements (+5 codes)
    print("⭐ Step 6: Applying Phase 1 enhancements (+5 codes)...")
    phase1_stage = Phase1EnhancementStage()
    final_df = phase1_stage.process(classified_df)
    print("✅ Complete\n")

    # Stage 6: Save results
    print("💾 Step 7: Saving results...")
    write_results(final_df, output_path)
    print(f"✅ Saved to {output_path.resolve()}/\n")

    # Final summary
    print("=" * 70)
    print("✅ PIPELINE COMPLETE - Integrated ACMG + gnomAD")
    print("=" * 70)
    print()

    evidence_cols = ["BA1", "BS1", "PM2", "PVS1", "BP7", "PP5", "BP6", "BS2"]
    evidence_mask = final_df[evidence_cols].any(axis=1)
    with_evidence = evidence_mask.sum()

    pathogenic_mask = final_df.get("acmg_final_auto", pd.Series()).str.contains(
        "Pathogenic", na=False
    )
    pathogenic_count = pathogenic_mask.sum()

    print("📊 Results:")
    print(f"  Total variants: {len(final_df):,}")
    print(
        f"  With evidence: {with_evidence:,} ({with_evidence/len(final_df)*100:.1f}%)"
    )
    print(f"  Pathogenic: {pathogenic_count:,}")
    print()

    pvs1_count = final_df.get("PVS1", pd.Series([False])).sum()
    pm2_count = final_df.get("PM2", pd.Series([False])).sum()

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
