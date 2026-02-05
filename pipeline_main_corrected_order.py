#!/usr/bin/env python3
"""
VariDex v7.2.0_dev COMPLETE Pipeline + 13-Code ACMG + gnomAD

Optimized order: gnomAD annotation → ClinVar matching → ACMG classification
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
from varidex.pipeline.gnomad_annotator import (
    annotate_with_gnomad,
    apply_frequency_acmg_criteria,
)


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
        description=f"VariDex v{__version__} - Integrated ACMG + gnomAD Pipeline"
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

    cache_file = Path("output/user_with_gnomad.csv")
    matched_cache = Path("output/complete_results.csv")

    # ==================================================================
    # STAGE 1-3: Load User Genome + gnomAD Annotation
    # ==================================================================
    if cache_file.exists() and not args.force_reload and not args.user_genome:
        print(f"✅ Using cached user genome with gnomAD: {cache_file}")
        user_annotated = pd.read_csv(cache_file)
        print(f"✅ Loaded {len(user_annotated):,} variants\n")
    else:
        if not args.user_genome:
            print("❌ Error: --user-genome required for initial run")
            print(f"   (Or use cached data in {cache_file})")
            sys.exit(1)

        # Step 1: Load user genome
        print("📖 Step 1: Loading your genome...")
        user_df = load_user_file(args.user_genome)
        print(f"✅ Loaded {len(user_df):,} variants from your genome\n")

        # Step 2: Annotate with gnomAD (BEFORE matching to ClinVar)
        if args.gnomad_dir:
            print("📊 Step 2: gnomAD Population Frequency Annotation")
            print("=" * 70)
            print(f"Annotating {len(user_df):,} variants with gnomAD...")

            # Prepare columns for gnomAD
            user_prep = user_df.copy()
            if "ref_allele" not in user_prep.columns and "ref" in user_prep.columns:
                user_prep["ref_allele"] = user_prep["ref"]
            if "alt_allele" not in user_prep.columns and "alt" in user_prep.columns:
                user_prep["alt_allele"] = user_prep["alt"]

            try:
                user_annotated = annotate_with_gnomad(user_prep, Path(args.gnomad_dir))
                print("Applying BA1, BS1, PM2 frequency criteria...")
                user_annotated = apply_frequency_acmg_criteria(user_annotated)

                ba1_count = user_annotated.get("BA1", pd.Series([False])).sum()
                bs1_count = user_annotated.get("BS1", pd.Series([False])).sum()
                pm2_count = user_annotated.get("PM2", pd.Series([False])).sum()

                print()
                print(
                    f"⭐ gnomAD applied to full genome: "
                    f"BA1={ba1_count:,}, BS1={bs1_count:,}, PM2={pm2_count:,}"
                )
                print("✅ Complete\n")

            except Exception as e:
                print(f"⚠️  gnomAD annotation failed: {e}")
                print("   Continuing without gnomAD data\n")
                user_annotated = user_df
        else:
            print("⚠️  Skipping gnomAD (no --gnomad-dir provided)")
            print("   BA1, BS1, PM2 criteria will not be applied\n")
            user_annotated = user_df

        # Cache the gnomAD-annotated user genome
        cache_file.parent.mkdir(exist_ok=True)
        user_annotated.to_csv(cache_file, index=False)
        print(f"💾 Cached gnomAD-annotated genome: {cache_file}\n")

    # ==================================================================
    # STAGE 4-5: Load ClinVar + Match
    # ==================================================================
    if matched_cache.exists() and not args.force_reload:
        print(f"✅ Using cached matched results: {matched_cache}")
        matched_df = pd.read_csv(matched_cache)
        print(f"✅ Loaded {len(matched_df):,} matched variants\n")
    else:
        # Step 3: Verify ClinVar exists
        print("📥 Step 3: Setup genomic data...")
        clinvar_path = Path(args.clinvar)

        if not clinvar_path.exists():
            print(f"⚠️  ClinVar not found at {clinvar_path}")
            print("   Calling setup_genomic_data() to download...")
            setup_genomic_data()
            clinvar_path = Path("clinvar/clinvar_GRCh37.vcf.gz")

        print(f"✅ ClinVar: {clinvar_path}\n")

        # Step 4: Load ClinVar
        print("📖 Step 4: Loading ClinVar...")
        clinvar_df = load_clinvar_file(str(clinvar_path))
        print(f"✅ Loaded {len(clinvar_df):,} ClinVar variants\n")

        # Step 5: Match gnomAD-annotated user genome to ClinVar
        print("🔗 Step 5: Matching variants (hybrid: rsID + coordinates)...")
        matched_df, rsid_matches, coord_matches = match_variants_hybrid(
            clinvar_df, user_annotated, clinvar_type="vcf", user_type="23andme"
        )

        print(f"✅ Matched {len(matched_df):,} variants:")
        print(f"   • rsID matches: {rsid_matches:,}")
        print(f"   • Coordinate matches: {coord_matches:,}\n")

        # Save matched cache
        matched_cache.parent.mkdir(exist_ok=True)
        matched_df.to_csv(matched_cache, index=False)

    # ==================================================================
    # STAGE 6-7: ACMG Classification + Phase 1
    # ==================================================================
    # Step 6: ACMG Classification (remaining codes)
    print("Applying ACMG classification (remaining codes)...")
    results_df = apply_full_acmg_classification(matched_df)
    print("✅ Complete\n")

    # Step 7: Phase 1 Enhancements
    print("Applying Phase 1 enhancements (+5 codes)...")
    results_df = enhance_with_phase1(results_df)
    print("✅ Complete\n")

    # ==================================================================
    # STAGE 8: Save Results
    # ==================================================================
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
