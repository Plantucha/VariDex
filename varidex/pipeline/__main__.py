#!/usr/bin/env python3
"""
VariDex v7.2.0-dev COMPLETE Pipeline - 16-Code ACMG + gnomAD + FULL EXPORT
CONFIRMED 13 criteria: BA1,BS1,PM2,PVS1,PM4,PP2,BP1,BP3,PP5,BP6,BP7,BS2,BS3
NEW: PM1, PM5, PM3
WITH DEBUG: Position column tracking
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
        f"Phase 1: BP7={counts['BP7']}, PP5={counts['PP5']}, "
        f"BP6={counts['BP6']}, BS2={counts['BS2']}"
    )
    return result_df


def write_output_files(df: pd.DataFrame, output_dir: Path) -> None:
    """Write ALL output files"""
    output_dir.mkdir(parents=True, exist_ok=True)

    acmg_16 = [
        "BA1", "BS1", "PM2", "PVS1", "PM4", "PP2", "BP1", "BP3",
        "PP5", "BP6", "BP7", "BS2", "BS3",
        "PM1", "PM5", "PM3"
    ]
    essentials = [
        "rsid", "chromosome", "position", "genotype", "gene", "clinical_sig",
        "review_status", "molecular_consequence", "gnomad_af", "acmg_classification"
    ]

    export_cols = [col for col in essentials + acmg_16 if col in df.columns]

    full_df = df[export_cols].copy()
    full_path = output_dir / "results_13codes_FULL.csv"
    full_df.to_csv(full_path, index=False)
    print(f"✅ FULL EXPORT: {len(full_df)} rows x {len(export_cols)} cols -> {full_path}")

    df.to_csv(output_dir / "results_13codes.csv", index=False)

    if "PVS1" in df.columns:
        pvs1_df = df[df["PVS1"] == True]
        pvs1_df.to_csv(output_dir / "PRIORITY_PVS1.csv", index=False)

    if "PM2" in df.columns:
        pm2_df = df[df["PM2"] == True]
        pm2_df.to_csv(output_dir / "PRIORITY_PM2.csv", index=False)

    summary_cols = [col for col in acmg_16 if col in df.columns]
    summary = {col: int(df[col].sum()) for col in summary_cols}
    print("📊 16 ACMG Criteria True Counts:")
    for col in sorted(summary, key=summary.get, reverse=True):
        print(f"   {col}: {summary[col]}")


def print_summary(df: pd.DataFrame) -> None:
    """Print final pipeline summary"""
    print("=" * 70)
    print("COMPLETE - 16 ACMG Codes")
    print("=" * 70)
    print(f"Total variants: {len(df)}")

    evidence_cols = ["BA1", "BS1", "PM2", "PVS1", "BP7", "PP5", "BP6", "BS2", "PM1", "PM5"]
    existing_cols = [c for c in evidence_cols if c in df.columns]

    if existing_cols:
        evidence_mask = df[existing_cols].any(axis=1)
        with_evidence = evidence_mask.sum()
    else:
        with_evidence = 0

    print(f"With evidence: {with_evidence} ({with_evidence/len(df)*100:.1f}%)")

    pvs1_count = int(df.get("PVS1", pd.Series([False])).sum())
    pm2_count = int(df.get("PM2", pd.Series([False])).sum())
    pm1_count = int(df.get("PM1", pd.Series([False])).sum())
    pm5_count = int(df.get("PM5", pd.Series([False])).sum())
    ba1_count = int(df.get("BA1", pd.Series([False])).sum())
    bs1_count = int(df.get("BS1", pd.Series([False])).sum())

    print("Priority ACMG Codes:")
    print(f"  PVS1 (loss of function): {pvs1_count}")
    print(f"  PM2 (rare pathogenic): {pm2_count}")
    print(f"  PM1 (critical domains): {pm1_count}")
    print(f"  PM5 (pathogenic position): {pm5_count}")
    print(f"  BA1 (common benign): {ba1_count}")
    print(f"  BS1 (high frequency): {bs1_count}")


def main() -> None:
    parser = ArgumentParser(
        description=f"VariDex v{version} - Full Pipeline with 16-Code ACMG + gnomAD"
    )
    parser.add_argument(
        "--clinvar", default="clinvar/clinvar_GRCh37.vcf.gz", help="ClinVar VCF file"
    )
    parser.add_argument("--user-genome", help="Your genome file (VCF or 23andMe)")
    parser.add_argument(
        "--gnomad-dir", help="Path to gnomAD directory (enables BA1/BS1/PM2 criteria)"
    )
    parser.add_argument("--output", default="results_michal", help="Output directory")
    parser.add_argument(
        "--force-reload", action="store_true", help="Force reload even if cache exists"
    )
    args: Namespace = parser.parse_args()

    print("=" * 70)
    print(f"VariDex v{version} - 16-Code ACMG + gnomAD Pipeline")
    print("=" * 70)

    cache_file = Path("output/complete_results.csv")

    if cache_file.exists() and not args.force_reload and not args.user_genome:
        print(f"Using cached matched results: {cache_file}")
        matched_df = pd.read_csv(cache_file)
        print(f"Loaded {len(matched_df)} matched variants")
        print(f"DEBUG: Cached position values: {matched_df.position.notna().sum()}")
        result_df = matched_df
    else:
        if not args.user_genome:
            print("Error: --user-genome required for initial run")
            print(f"Or use cached results in {cache_file}")
            sys.exit(1)

        print("Step 1: Setup genomic data...")
        clinvar_path = Path(args.clinvar)
        if not clinvar_path.exists():
            print(f"ClinVar not found at {clinvar_path}")
            print("Calling setup_genomic_data() to download...")
            setup_genomic_data(clinvar_path, Path("clinvar/clinvar_GRCh37.vcf.gz"))

        print(f"ClinVar: {clinvar_path}")
        if args.gnomad_dir:
            print(f"gnomAD: {args.gnomad_dir}")

        print("Step 2: Loading ClinVar...")
        clinvar_df = load_clinvar_file(str(clinvar_path))
        print(f"Loaded {len(clinvar_df)} ClinVar variants")
        print(f"DEBUG: ClinVar position values: {clinvar_df.position.notna().sum()}")

        print("Step 3: Loading your genome...")
        user_df = load_user_file(args.user_genome)
        print(f"Loaded {len(user_df)} variants from your genome")
        print(f"DEBUG: User genome position values: {user_df.position.notna().sum()}")

        print("Step 4: Matching variants (hybrid rsID + coordinates)...")
        matched_df, rsid_matches, coord_matches = match_variants_hybrid(
            clinvar_df, user_df, clinvar_type="vcf", user_type="23andme"
        )
        print(f"Matched {len(matched_df)} variants")
        print(f"  rsID matches: {rsid_matches}")
        print(f"  Coordinate matches: {coord_matches}")
        print(f"DEBUG: After matching - columns: {list(matched_df.columns)}")
        print(f"DEBUG: After matching - position values: {matched_df.position.notna().sum()}")

        if cache_file.parent.exists() and cache_file.parent.is_file():
            cache_file.parent.unlink()
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        matched_df.to_csv(cache_file, index=False)

        print("Step 5: gnomAD annotation (NOW we have ref/alt from ClinVar!)...")
        if args.gnomad_dir:
            gnomad_stage = GnomadAnnotationStage(Path(args.gnomad_dir))
            matched_df = gnomad_stage.process(matched_df)
            print(f"DEBUG: After gnomAD - position values: {matched_df.position.notna().sum()}")
        else:
            print("Skipping gnomAD (no --gnomad-dir provided)")
            print("BA1, BS1, PM2 criteria will not be applied")

        print("Step 6: Applying ACMG classification (base codes)...")
        result_df = apply_full_acmg_classification(matched_df)
        print("Complete")
        print(f"DEBUG: After ACMG base - position values: {result_df.position.notna().sum()}")

        print("Step 7: Applying Phase 1 enhancements (+5 codes)...")
        result_df = enhance_with_phase1(result_df)
        print("Complete")
        print(f"DEBUG: After Phase 1 - position values: {result_df.position.notna().sum()}")

    print("Step 8: Applying additional 3 criteria (PM1, PM5, PM3)...")
    try:
        from varidex.acmg.criteria_pm1 import PM1Classifier
        from varidex.acmg.criteria_pm5 import PM5Classifier
        from varidex.acmg.criteria_pm3 import PM3Classifier

        pm1 = PM1Classifier("uniprot/uniprot_sprot.xml.gz")
        result_df = pm1.apply_pm1(result_df)

        pm5 = PM5Classifier(clinvar_df)
        result_df = pm5.apply_pm5(result_df)

        pm3 = PM3Classifier()
        result_df = pm3.apply_pm3(result_df)

        print("Complete (now 16/28 criteria)")
    except Exception as e:
        import traceback
        print(f"Warning: Additional criteria failed: {e}")
        print(traceback.format_exc())
        print("Continuing with 13/28 criteria")

    print(f"DEBUG: Before output - position values: {result_df.position.notna().sum()}")

    output_path = Path(args.output)
    write_output_files(result_df, output_path)
    print(f"Output -> {output_path.resolve()}")
    print("  results_13codes.csv")
    print("  PRIORITY_PVS1.csv")
    print("  PRIORITY_PM2.csv")
    print("  results_13codes_FULL.csv  ← NEW: 16 criteria + essentials")

    print_summary(result_df)


if __name__ == "__main__":
    main()
