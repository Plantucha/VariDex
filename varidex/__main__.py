#!/usr/bin/env python3
"""
VariDex v7.2.0-dev - 20-Code ACMG Pipeline (FIXED VERSION)
Phase 1: Data Enrichment (gnomAD, dbNSFP)
Phase 2: ACMG Classification (20/28 criteria)
Phase 3: Final ACMG Classification (Pathogenic/Benign/VUS)

FIXED: Only applies PS3 in Step 10 (PP2 remains in Step 7)
- Avoids double PP2 application
- Better error handling for missing dbNSFP data
- Clear logging for PS3 application
"""
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
import pandas as pd

from varidex import version
from varidex.downloader import setup_genomic_data
from varidex.io.loaders.clinvar import load_clinvar_file
from varidex.io.loaders.user import load_user_file
from varidex.io.matching_improved import match_variants_hybrid
from varidex.pipeline.acmg_classifier_stage import apply_full_acmg_classification
from varidex.pipeline.gnomad_stage import GnomadAnnotationStage


def detect_genome_build_from_filename(filepath: str) -> str:
    """Detect genome build from ClinVar filename"""
    filepath_lower = filepath.lower()

    if "grch38" in filepath_lower or "hg38" in filepath_lower:
        return "GRCh38"
    elif "grch37" in filepath_lower or "hg19" in filepath_lower:
        return "GRCh37"
    else:
        print("⚠️  Could not detect genome build from filename, defaulting to GRCh37")
        return "GRCh37"


def enhance_with_phase1(result_df: pd.DataFrame) -> pd.DataFrame:
    """Add Phase 1 ACMG codes: PP5, BP6, BP7, BS2, BS3"""
    phase1_codes = ["PP5", "BP6", "BP7", "BS2", "BS3"]
    for code in phase1_codes:
        if code not in result_df.columns:
            result_df[code] = False

    counts = {code: 0 for code in phase1_codes}
    for idx, row in result_df.iterrows():
        cons = str(row.get("molecular_consequence", "")).lower()
        rev = str(row.get("review_status", "")).lower()
        sig = str(row.get("clinical_sig", "")).lower()
        af = row.get("gnomad_af")

        if ("synonymous" in cons or "silent" in cons) and "splice" not in cons:
            result_df.at[idx, "BP7"] = True
            counts["BP7"] += 1

        if "expert panel" in rev or "practice guideline" in rev:
            if "pathogenic" in sig and "benign" not in sig:
                result_df.at[idx, "PP5"] = True
                counts["PP5"] += 1
            elif "benign" in sig:
                result_df.at[idx, "BP6"] = True
                counts["BP6"] += 1

        if pd.notna(af) and af > 0.01 and "pathogenic" in sig and "benign" not in sig:
            result_df.at[idx, "BS2"] = True
            counts["BS2"] += 1

    print(
        f"  PP5={counts['PP5']}, BP6={counts['BP6']}, BP7={counts['BP7']}, "
        f"BS2={counts['BS2']}, BS3=0"
    )
    return result_df


def write_output_files(df: pd.DataFrame, output_dir: Path) -> None:
    """Write ALL output files with classification-based exports"""
    output_dir.mkdir(parents=True, exist_ok=True)

    # 20 codes (PS3 added, PP2 remains from Step 7)
    acmg_20 = [
        "BA1",
        "BS1",
        "PM2",
        "PVS1",
        "PM4",
        "PP2",
        "BP1",
        "BP3",
        "PP5",
        "BP6",
        "BP7",
        "BS2",
        "BS3",
        "PM1",
        "PM5",
        "PM3",
        "PS1",
        "PS3",
        "PP3",
        "BP4",
    ]

    essentials = [
        "rsid",
        "chromosome",
        "position",
        "genotype",
        "gene",
        "clinical_sig",
        "review_status",
        "molecular_consequence",
        "gnomad_af",
        "acmg_classification",
    ]

    pred_scores = [
        "SIFT_score",
        "PolyPhen_score",
        "CADD_phred",
        "REVEL_score",
        "AlphaMissense_score",
    ]
    export_base = essentials + acmg_20 + pred_scores
    export_cols = [col for col in export_base if col in df.columns]

    # Full export
    full_df = df[export_cols].copy()
    full_path = output_dir / "results_20codes_FULL.csv"
    full_df.to_csv(full_path, index=False)
    print(
        f"\n✅ FULL EXPORT: {len(full_df)} rows x {len(export_cols)} cols -> {full_path}"
    )

    # Complete results
    df.to_csv(output_dir / "results_20codes.csv", index=False)

    # Priority code files
    priority_codes = {
        "PVS1": "PRIORITY_PVS1.csv",
        "PM2": "PRIORITY_PM2.csv",
        "PS1": "PRIORITY_PS1.csv",
        "PS3": "PRIORITY_PS3.csv",
        "PP3": "PRIORITY_PP3.csv",
    }
    for code, filename in priority_codes.items():
        if code in df.columns:
            priority_df = df[df[code] == True]
            if len(priority_df) > 0:
                priority_df.to_csv(output_dir / filename, index=False)
                print(f"  📄 {filename} ({len(priority_df)} variants)")

    # Classification-based files
    if "acmg_classification" in df.columns:
        print("\n🔬 Classification-based exports:")

        # Pathogenic + Likely Pathogenic
        pathogenic_df = df[
            df["acmg_classification"].isin(["Pathogenic", "Likely Pathogenic"])
        ]
        if len(pathogenic_df) > 0:
            path_file = output_dir / "PATHOGENIC_variants.csv"
            pathogenic_df.to_csv(path_file, index=False)
            print(f"  🔴 PATHOGENIC_variants.csv ({len(pathogenic_df)} variants)")

        # Benign + Likely Benign
        benign_df = df[df["acmg_classification"].isin(["Benign", "Likely Benign"])]
        if len(benign_df) > 0:
            benign_file = output_dir / "BENIGN_variants.csv"
            benign_df.to_csv(benign_file, index=False)
            print(f"  🟢 BENIGN_variants.csv ({len(benign_df)} variants)")

        # VUS / Uncertain Significance
        vus_df = df[df["acmg_classification"].isin(["VUS", "Uncertain Significance"])]
        if len(vus_df) > 0:
            vus_file = output_dir / "VUS_variants.csv"
            vus_df.to_csv(vus_file, index=False)
            print(f"  🟡 VUS_variants.csv ({len(vus_df)} variants)")

    # ACMG criteria summary
    summary_cols = [col for col in acmg_20 if col in df.columns]
    summary = {col: int(df[col].sum()) for col in summary_cols}

    print("\n📊 20 ACMG Criteria Summary:")
    for col in sorted(summary, key=summary.get, reverse=True):
        if summary[col] > 0:
            print(f"   {col}: {summary[col]}")


def print_summary(df: pd.DataFrame) -> None:
    """Print final pipeline summary with ACMG classifications"""
    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE - 20/28 ACMG Codes")
    print("=" * 70)
    print(f"Total variants: {len(df):,}")

    # Count by final ACMG classification
    if "acmg_classification" in df.columns:
        print("\n🔬 ACMG Final Classifications:")
        classifications = df["acmg_classification"].value_counts()

        # Define order and emojis
        class_order = [
            ("Pathogenic", "🔴"),
            ("Likely Pathogenic", "🟠"),
            ("VUS", "🟡"),
            ("Uncertain Significance", "🟡"),
            ("Likely Benign", "🟢"),
            ("Benign", "🟢"),
        ]

        total_classified = 0
        for class_name, emoji in class_order:
            count = classifications.get(class_name, 0)
            if count > 0:
                pct = count / len(df) * 100
                print(f"  {emoji} {class_name}: {count:,} ({pct:.1f}%)")
                total_classified += count

        # Handle any other classifications
        other_count = len(df) - total_classified
        if other_count > 0:
            pct = other_count / len(df) * 100
            print(f"  ⚪ Other/Unclassified: {other_count:,} ({pct:.1f}%)")

    # Evidence coverage
    evidence_cols = [
        "BA1",
        "BS1",
        "PM2",
        "PVS1",
        "BP7",
        "PP5",
        "BP6",
        "BS2",
        "PM1",
        "PM5",
        "PS1",
        "PS3",
        "PP3",
        "BP4",
    ]
    existing_cols = [c for c in evidence_cols if c in df.columns]

    if existing_cols:
        evidence_mask = df[existing_cols].any(axis=1)
        with_evidence = evidence_mask.sum()
    else:
        with_evidence = 0

    print(
        f"\n📊 Evidence Coverage: {with_evidence:,}/{len(df):,} "
        f"({with_evidence/len(df)*100:.1f}%)"
    )

    # Priority codes breakdown
    priority_codes = {
        "PVS1": ("🔴", "loss of function"),
        "PM2": ("🟠", "rare pathogenic"),
        "PM1": ("🟡", "critical domains"),
        "PM5": ("🟠", "pathogenic position"),
        "PS1": ("🔴", "same AA change"),
        "PS3": ("🔴", "functional evidence"),
        "PP3": ("🟡", "computational deleterious"),
        "BP4": ("🟢", "computational benign"),
        "BA1": ("🟢", "common benign"),
        "BS1": ("🟢", "high frequency"),
    }

    print("\n🎯 Top Priority Codes:")
    for code, (emoji, desc) in priority_codes.items():
        count = int(df.get(code, pd.Series([False])).sum())
        if count > 0:
            print(f"  {emoji} {code} ({desc}): {count:,}")

    # High-risk summary
    if "PVS1" in df.columns or "PM2" in df.columns or "PS3" in df.columns:
        pvs1_mask = df.get("PVS1", pd.Series([False], dtype=bool))
        pm2_mask = df.get("PM2", pd.Series([False], dtype=bool))
        ps3_mask = df.get("PS3", pd.Series([False], dtype=bool))
        pp3_mask = df.get("PP3", pd.Series([False], dtype=bool))

        high_risk = df[pvs1_mask | ps3_mask | (pm2_mask & pp3_mask)].shape[0]
        if high_risk > 0:
            print(
                f"\n⚠️  High-Risk Variants (PVS1/PS3 or PM2+PP3): {high_risk:,} "
                f"({high_risk/len(df)*100:.1f}%)"
            )


def main() -> None:
    parser = ArgumentParser(
        description=f"VariDex v{version} - 20-Code ACMG Pipeline (FIXED)"
    )
    parser.add_argument("--clinvar", default="clinvar/clinvar_GRCh37.vcf.gz")
    parser.add_argument("--user-genome", help="Your genome file (VCF or 23andMe)")
    parser.add_argument("--gnomad-dir", help="gnomAD directory path")
    parser.add_argument(
        "--gnomad-constraint", help="gnomAD constraint file for PP2 (optional)"
    )
    parser.add_argument("--output", default="results_michal")
    parser.add_argument("--force-reload", action="store_true")
    parser.add_argument(
        "--genome-build",
        choices=["GRCh37", "GRCh38"],
        help="Genome build (auto-detected if not specified)",
    )

    args: Namespace = parser.parse_args()

    print("=" * 70)
    print(f"VariDex v{version} - 20-Code ACMG Pipeline (FIXED)")
    print("=" * 70)

    # Detect genome build
    if args.genome_build:
        genome_build = args.genome_build
        print(f"\n🧬 Genome build: {genome_build} (user-specified)")
    else:
        genome_build = detect_genome_build_from_filename(args.clinvar)
        print(f"\n🧬 Genome build: {genome_build} (auto-detected from filename)")

    # Check for cached results
    cache_file = Path("output/complete_results.csv")
    if cache_file.exists() and not args.force_reload and not args.user_genome:
        print(f"\nUsing cached matched results: {cache_file}")
        matched_df = pd.read_csv(cache_file)
        print(f"Loaded {len(matched_df)} matched variants")
    else:
        if not args.user_genome:
            print("\nError: --user-genome required for initial run")
            sys.exit(1)

        # Steps 1-4: Load and Match
        print("\n" + "=" * 70)
        print("PHASE 1: DATA LOADING & MATCHING")
        print("=" * 70)

        clinvar_path = Path(args.clinvar)
        if not clinvar_path.exists():
            print(f"\n❌ ClinVar not found at {clinvar_path}")
            sys.exit(1)

        print(f"\nStep 1: Loading ClinVar from {clinvar_path}...")
        clinvar_df = load_clinvar_file(str(clinvar_path))
        print(f"  ✓ Loaded {len(clinvar_df):,} ClinVar variants")

        print(f"\nStep 2: Loading user genome from {args.user_genome}...")
        user_df = load_user_file(args.user_genome)
        print(f"  ✓ Loaded {len(user_df):,} variants")

        print(f"\nStep 3: Matching variants (rsID + coordinates)...")
        matched_df, rsid_matches, coord_matches = match_variants_hybrid(
            clinvar_df, user_df, clinvar_type="vcf", user_type="23andme"
        )
        print(f"  ✓ Matched {len(matched_df):,} variants")
        print(f"    - rsID matches: {rsid_matches:,}")
        print(f"    - Coordinate matches: {coord_matches:,}")

        print(f"\nStep 4: Caching matched results...")
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        matched_df.to_csv(cache_file, index=False)
        print(f"  ✓ Cached to {cache_file}")

    # Store clinvar_df for later use
    if "clinvar_df" not in locals():
        print("\nLoading ClinVar for criteria reference...")
        clinvar_df = load_clinvar_file(str(Path(args.clinvar)))

    # Phase 2: Data Enrichment
    print("\n" + "=" * 70)
    print("PHASE 2: DATA ENRICHMENT")
    print("=" * 70)

    print("\nStep 5: Annotating with gnomAD population frequencies...")
    if args.gnomad_dir:
        gnomad_stage = GnomadAnnotationStage(Path(args.gnomad_dir))
        matched_df = gnomad_stage.process(matched_df)
    else:
        print("  ⚠️  Skipped (no --gnomad-dir provided)")
        print("  BA1, BS1, PM2 criteria will be limited")

    print("\nStep 6: Annotating with dbNSFP prediction scores...")
    try:
        from varidex.acmg.dbnsfp_annotator import annotate_with_dbnsfp

        matched_df = annotate_with_dbnsfp(
            matched_df, "data/external/dbNSFP", genome_build
        )
        print("  ✓ Complete")
    except Exception as e:
        print(f"  ⚠️  dbNSFP annotation failed: {e}")
        print("  PS3, PP3, BP4 criteria will be limited")

    # Phase 3: ACMG Classification
    print("\n" + "=" * 70)
    print("PHASE 3: ACMG CLASSIFICATION (20/28 criteria)")
    print("=" * 70)

    print("\nStep 7: Base ACMG criteria (PVS1, PM4, PP2, BP1, BP3)...")
    result_df = apply_full_acmg_classification(matched_df)
    print("  ✓ Complete")
    print("  Note: PP2 applied here (basic version)")

    print("\nStep 8: Phase 1 enhancements (PP5, BP6, BP7, BS2, BS3)...")
    result_df = enhance_with_phase1(result_df)

    print("\nStep 9: Domain/position-based criteria (PM1, PM5, PM3, PS1)...")
    try:
        from varidex.acmg.criteria_pm1 import PM1Classifier
        from varidex.acmg.criteria_pm5 import PM5Classifier
        from varidex.acmg.criteria_pm3 import PM3Classifier
        from varidex.acmg.criteria_ps1 import PS1Classifier

        pm1 = PM1Classifier("uniprot/uniprot_sprot.xml.gz")
        result_df = pm1.apply_pm1(result_df)

        pm5 = PM5Classifier(clinvar_df)
        result_df = pm5.apply_pm5(result_df)

        pm3 = PM3Classifier()
        result_df = pm3.apply_pm3(result_df)

        ps1 = PS1Classifier(clinvar_df)
        result_df = ps1.apply_ps1(result_df)

        print("  ✓ Complete")
    except Exception as e:
        print(f"  ⚠️  Warning: {e}")

    print("\nStep 10: Functional evidence (PS3 only - PP2 already in Step 7)...")
    try:
        from varidex.acmg.criteria_PS3_PP2 import (
            PS3_PP2_Classifier,
            load_curated_gene_lists,
        )

        # Load gene lists (for future PP2 enhancement if needed)
        lof_genes, missense_genes = load_curated_gene_lists()

        ps3_classifier = PS3_PP2_Classifier(
            gnomad_constraint_path=args.gnomad_constraint,
            lof_genes=lof_genes,
            missense_genes=missense_genes,
        )

        # CRITICAL: Use apply_ps3_only() to avoid overwriting Step 7's PP2
        result_df = ps3_classifier.apply_ps3_only(result_df)
        print("  ✓ Complete")
    except Exception as e:
        print(f"  ⚠️  Warning: {e}")
        print("  PS3 criterion may be missing")
        # Ensure PS3 column exists even if classifier fails
        if "PS3" not in result_df.columns:
            result_df["PS3"] = False

    print("\nStep 11: Computational prediction criteria (PP3, BP4)...")
    try:
        from varidex.acmg.criteria_pp3_bp4 import PP3_BP4_Classifier

        pp3_bp4 = PP3_BP4_Classifier()
        result_df = pp3_bp4.apply_pp3_bp4(result_df)
        print("  ✓ Complete")
    except Exception as e:
        print(f"  ⚠️  Warning: {e}")

    # Output
    output_path = Path(args.output)
    write_output_files(result_df, output_path)

    print(f"\nOutput directory: {output_path.resolve()}")
    print("  - results_20codes.csv (all data)")
    print("  - results_20codes_FULL.csv (essentials + 20 criteria)")
    print("  - PATHOGENIC_variants.csv (high-risk)")
    print("  - BENIGN_variants.csv (safe)")
    print("  - VUS_variants.csv (uncertain)")
    print("  - PRIORITY_*.csv (code-specific)")

    print_summary(result_df)


if __name__ == "__main__":
    main()
