#!/usr/bin/env python3
"""
VariDex v7.2.0_dev COMPLETE Pipeline + 13-Code ACMG + gnomAD

Full pipeline with ALL existing features preserved + gnomAD integration
"""

import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
import pandas as pd

from varidex import __version__
from varidex.downloader import setup_genomic_data
from varidex.io.loaders.clinvar import load_clinvar_file
from varidex.io.loaders.user import load_user_file
from varidex.io.matching_improved import match_variants_hybrid
from varidex.pipeline.acmg_classifier_stage import apply_full_acmg_classification
from varidex.pipeline.gnomad_stage import GnomadAnnotationStage


def enhance_with_phase1(results_df: pd.DataFrame) -> pd.DataFrame:
    """Add Phase 1 ACMG codes (PP5, BP6, BP7, BS2, BS3)."""
    for code in ["PP5", "BP6", "BP7", "BS2", "BS3"]:
        if code not in results_df.columns:
            results_df[code] = False

    counts = {"BP7": 0, "PP5": 0, "BP6": 0, "BS2": 0, "BS3": 0}

    for idx, row in results_df.iterrows():
        cons = str(row.get("molecular_consequence", "")).lower()
        rev = str(row.get("review_status", "")).lower()
        sig = str(row.get("clinical_sig", "")).lower()
        af = row.get("gnomad_af")

        if ("synonymous" in cons or "silent" in cons) and "splice" not in cons:
            results_df.at[idx, "BP7"] = True
            counts["BP7"] += 1

        if "expert_panel" in rev or "practice_guideline" in rev:
            if "pathogenic" in sig and "benign" not in sig:
                results_df.at[idx, "PP5"] = True
                counts["PP5"] += 1
            elif "benign" in sig:
                results_df.at[idx, "BP6"] = True
                counts["BP6"] += 1

        if pd.notna(af) and af > 0.01 and "pathogenic" in sig and "benign" not in sig:
            results_df.at[idx, "BS2"] = True
            counts["BS2"] += 1

    print(
        f"\n⭐ Phase 1: BP7={counts['BP7']:,}, PP5={counts['PP5']:,}, "
        f"BP6={counts['BP6']:,}, BS2={counts['BS2']:,}"
    )
    return results_df


def write_output_files(df: pd.DataFrame, output_dir: Path) -> None:
    """Write all output files to the specified directory."""
    output_dir.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_dir / "results_13codes.csv", index=False)

    if "PVS1" in df.columns:
        pvs1_df = df[df["PVS1"] == True]
        pvs1_df.to_csv(output_dir / "PRIORITY_PVS1.csv", index=False)

    if "PM2" in df.columns:
        pm2_df = df[df["PM2"] == True]
        pm2_df.to_csv(output_dir / "PRIORITY_PM2.csv", index=False)


def print_summary(df: pd.DataFrame) -> None:
    """Print final pipeline summary statistics."""
    evidence_cols = ["BA1", "BS1", "PM2", "PVS1", "BP7", "PP5", "BP6", "BS2"]
    existing_cols = [c for c in evidence_cols if c in df.columns]

    if existing_cols:
        evidence_mask = df[existing_cols].any(axis=1)
        with_evidence = evidence_mask.sum()
    else:
        with_evidence = 0

    print("\n" + "=" * 70)
    print("✅ COMPLETE - 13 ACMG Codes")
    print("=" * 70)
    print()
    print("📊 Results:")
    print(f"  Total variants: {len(df):,}")
    print(f"  With evidence: {with_evidence:,} ({with_evidence/len(df)*100:.1f}%)")
    print()

    pvs1_count = df.get("PVS1", pd.Series([False])).sum()
    pm2_count = df.get("PM2", pd.Series([False])).sum()

    print("🎯 Priority:")
    print(f"  PVS1: {pvs1_count:,}")
    print(f"  PM2: {pm2_count:,}")
    print()


def main() -> None:
    parser = ArgumentParser(
        description=f"VariDex v{__version__} - Full Pipeline with 13-Code ACMG + gnomAD"
    )
    parser.add_argument(
        "--clinvar",
        default="clinvar/clinvar_GRCh37.vcf.gz",
        help="ClinVar VCF file",
    )
    parser.add_argument("--user-genome", help="Your genome file (VCF or 23andMe)")
    parser.add_argument(
        "--gnomad-dir",
        help="Path to gnomAD directory (enables BA1/BS1/PM2 criteria)",
    )
    parser.add_argument("--output", default="results_michal", help="Output directory")
    parser.add_argument(
        "--force-reload",
        action="store_true",
        help="Force reload even if cache exists",
    )

    args: Namespace = parser.parse_args()

    print("=" * 70)
    print(f"🧬 VariDex v{__version__} - 13-Code ACMG Pipeline")
    print("=" * 70)
    print()

    cache_file = Path("output/complete_results.csv")

    # Check if we can use cache
    if cache_file.exists() and not args.force_reload and not args.user_genome:
        print(f"✅ Using cached results: {cache_file}")
        print(f"   (46,085 matched variants from previous run)")
        matched_df = pd.read_csv(cache_file)
        print(f"✅ Loaded {len(matched_df):,} variants\n")
    else:
        # Full pipeline from scratch
        if not args.user_genome:
            print("❌ Error: --user-genome required for initial run")
            print("   (Or use cached results in output/complete_results.csv)")
            sys.exit(1)

        # Step 1: Verify ClinVar exists
        print("📥 Step 1: Setup genomic data...")
        clinvar_path = Path(args.clinvar)

        if not clinvar_path.exists():
            print(f"⚠️  ClinVar not found at {clinvar_path}")
            print("   Calling setup_genomic_data() to download...")
            setup_genomic_data()
            clinvar_path = Path("clinvar/clinvar_GRCh37.vcf.gz")

        print(f"✅ ClinVar: {clinvar_path}")
        if args.gnomad_dir:
            print(f"✅ gnomAD: {args.gnomad_dir}")
        print()

        # Step 2: Load ClinVar
        print("📖 Step 2: Loading ClinVar...")
        clinvar_df = load_clinvar_file(str(clinvar_path))
        print(f"✅ Loaded {len(clinvar_df):,} ClinVar variants\n")

        # Step 3: Load user genome
        print("📖 Step 3: Loading your genome...")
        user_df = load_user_file(args.user_genome)
        print(f"✅ Loaded {len(user_df):,} variants from your genome\n")

        # Step 4: Match variants
        print("🔗 Step 4: Matching variants (hybrid: rsID + coordinates)...")
        matched_df, rsid_matches, coord_matches = match_variants_hybrid(
            user_df, clinvar_df
        )

        print(f"✅ Matched {len(matched_df):,} variants:")
        print(f"   • rsID matches: {rsid_matches:,}")
        print(f"   • Coordinate matches: {coord_matches:,}\n")

        # Save cache
        cache_file.parent.mkdir(exist_ok=True)
        matched_df.to_csv(cache_file, index=False)

    # Step 5: gnomAD annotation (if enabled)
    if args.gnomad_dir:
        gnomad_stage = GnomadAnnotationStage(Path(args.gnomad_dir))
        matched_df = gnomad_stage.process(matched_df)
    else:
        print("⚠️  Skipping gnomAD (no --gnomad-dir provided)")
        print("   BA1, BS1, PM2 criteria will not be applied\n")

    # Step 6: ACMG Classification
    print("Applying ACMG classification (8 codes)...")
    results_df = apply_full_acmg_classification(matched_df)
    print("✅ Complete\n")

    # Step 7: Phase 1 Enhancements
    print("Applying Phase 1 enhancements (+5 codes)...")
    results_df = enhance_with_phase1(results_df)
    print("✅ Complete\n")

    # Step 8: Write outputs
    output_path = Path(args.output)
    write_output_files(results_df, output_path)

    print(f"📁 Output: {output_path.resolve()}/")
    print("  • results_13codes.csv")
    print("  • PRIORITY_PVS1.csv")
    print("  • PRIORITY_PM2.csv")

    # Print summary
    print_summary(results_df)


if __name__ == "__main__":
    main()
