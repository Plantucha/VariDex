#!/usr/bin/env python3
"""
annotate_clinvar_with_gnomad.py - VariDex Pipeline Integration Example

Complete pipeline that:
1. Loads user genome variants
2. Matches against ClinVar database
3. Annotates with gnomAD population frequencies
4. Identifies rare and novel pathogenic variants
5. Generates summary reports

Usage:
    python examples/annotate_clinvar_with_gnomad.py \
        --user-variants user_data/my_genome.csv \
        --clinvar clinvar/clinvar_GRCh37.vcf.gz \
        --gnomad-dir gnomad \
        --output results/annotated_variants.csv

Author: VariDex Team
Version: 1.0.0 DEVELOPMENT
Date: 2026-01-28
"""

import sys
import argparse
import logging
from pathlib import Path
import pandas as pd
from typing import Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# VariDex imports
try:
    from varidex.io.loaders.clinvar import load_clinvar_file
    from varidex.io.matching import match_variants_hybrid
    from varidex.integrations import GnomADAnnotator, AnnotationConfig
except ImportError as e:
    logger.error(f"Failed to import VariDex modules: {e}")
    logger.error("Make sure you're in the VariDex directory with venv activated")
    sys.exit(1)


def load_user_variants(filepath: Path) -> pd.DataFrame:
    """
    Load user genome variants from file.

    Supports: CSV, TSV, VCF
    Required columns: chromosome, position, ref_allele, alt_allele
    """
    logger.info(f"📖 Loading user variants from {filepath}")

    if not filepath.exists():
        raise FileNotFoundError(f"User variants file not found: {filepath}")

    # Detect file type and load
    suffix = filepath.suffix.lower()

    if suffix == ".csv":
        df = pd.read_csv(filepath)
    elif suffix in [".tsv", ".txt"]:
        df = pd.read_csv(filepath, sep="\t")
    elif suffix in [".vcf", ".gz"]:
        # Basic VCF parsing (use proper VCF parser for production)
        logger.warning("Basic VCF parsing - consider using cyvcf2 for production")
        df = pd.read_csv(
            filepath,
            sep="\t",
            comment="#",
            header=None,
            names=[
                "chromosome",
                "position",
                "id",
                "ref_allele",
                "alt_allele",
                "qual",
                "filter",
                "info",
            ],
        )
    else:
        raise ValueError(f"Unsupported file format: {suffix}")

    # Validate required columns
    required = ["chromosome", "position", "ref_allele", "alt_allele"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Normalize chromosome names (remove 'chr' prefix)
    df["chromosome"] = df["chromosome"].astype(str).str.replace("chr", "", regex=False)

    logger.info(f"   Loaded {len(df):,} variants")
    logger.info(
        f"   Chromosomes: {sorted(df['chromosome'].unique(), key=lambda x: (not x.isdigit(), x))}"
    )

    return df


def match_with_clinvar(user_df: pd.DataFrame, clinvar_file: Path) -> pd.DataFrame:
    """
    Match user variants against ClinVar database.
    """
    logger.info(f"\n🔍 Matching variants with ClinVar database...")
    logger.info(f"   ClinVar file: {clinvar_file}")

    # Load ClinVar
    clinvar_df = load_clinvar_file(clinvar_file)
    logger.info(f"   Loaded {len(clinvar_df):,} ClinVar variants")

    # Match variants (hybrid: rsID + coordinates)
    matched, rsid_count, coord_count = match_variants_hybrid(
        clinvar_df=clinvar_df, user_df=user_df
    )

    logger.info(f"\n✅ Matching complete:")
    logger.info(f"   Total matches: {len(matched):,}")
    logger.info(f"   rsID matches: {rsid_count:,}")
    logger.info(f"   Coordinate matches: {coord_count:,}")
    logger.info(f"   Coverage: {100*len(matched)/len(user_df):.2f}%")

    return matched


def annotate_with_gnomad(
    variants_df: pd.DataFrame, gnomad_dir: Path, max_af: float = None
) -> pd.DataFrame:
    """
    Annotate variants with gnomAD population frequencies.
    """
    logger.info(f"\n🧬 Annotating with gnomAD frequencies...")
    logger.info(f"   gnomAD directory: {gnomad_dir}")

    # Configure annotator
    config = AnnotationConfig(
        use_local=True,
        gnomad_dir=gnomad_dir,
        dataset="exomes",
        version="r2.1.1",
        max_af=max_af,
        show_progress=True,
    )

    # Annotate
    with GnomADAnnotator(config) as annotator:
        annotated = annotator.annotate(variants_df)

        # Generate summary
        stats = annotator.summarize_frequencies(annotated)

        logger.info(f"\n✅ gnomAD annotation complete:")
        logger.info(
            f"   Found in gnomAD: {stats['found_in_gnomad']:,}/{stats['total_variants']:,}"
        )
        logger.info(f"   Coverage: {stats['coverage']:.1f}%")
        logger.info(f"   Novel variants: {stats['novel_variants']:,}")

        if stats["af_statistics"]["mean"] is not None:
            logger.info(f"   Mean AF: {stats['af_statistics']['mean']:.6f}")
            logger.info(f"   Median AF: {stats['af_statistics']['median']:.6f}")

        logger.info(f"\n   Frequency categories:")
        for category, count in stats["frequency_categories"].items():
            logger.info(f"      {category}: {count:,}")

    return annotated


def analyze_pathogenic_variants(annotated_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    Analyze pathogenic and likely pathogenic variants.
    """
    logger.info(f"\n🔬 Analyzing pathogenic variants...")

    results = {}

    # Check if clinical_significance column exists
    if "clinical_significance" not in annotated_df.columns:
        logger.warning("   No clinical_significance column found")
        return results

    # Filter pathogenic variants
    pathogenic_mask = annotated_df["clinical_significance"].str.contains(
        "Pathogenic", case=False, na=False
    )
    pathogenic = annotated_df[pathogenic_mask]

    logger.info(f"   Total pathogenic: {len(pathogenic):,}")

    # Categorize by gnomAD frequency
    if "gnomad_af" in pathogenic.columns:
        # Novel (not in gnomAD)
        novel = pathogenic[pathogenic["gnomad_af"].isna()]
        results["novel_pathogenic"] = novel
        logger.info(f"   Novel (not in gnomAD): {len(novel):,}")

        # Rare (AF < 0.1%)
        rare = pathogenic[
            pathogenic["gnomad_af"].notna() & (pathogenic["gnomad_af"] < 0.001)
        ]
        results["rare_pathogenic"] = rare
        logger.info(f"   Rare (AF < 0.1%): {len(rare):,}")

        # Common (AF > 1%)
        common = pathogenic[
            pathogenic["gnomad_af"].notna() & (pathogenic["gnomad_af"] > 0.01)
        ]
        results["common_pathogenic"] = common
        logger.info(f"   Common (AF > 1%): {len(common):,}")

    results["all_pathogenic"] = pathogenic

    return results


def generate_report(
    annotated_df: pd.DataFrame,
    pathogenic_analysis: Dict[str, pd.DataFrame],
    output_dir: Path,
):
    """
    Generate summary reports and export results.
    """
    logger.info(f"\n📊 Generating reports...")

    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Full annotated results
    full_output = output_dir / "all_variants_annotated.csv"
    annotated_df.to_csv(full_output, index=False)
    logger.info(f"   ✓ Full results: {full_output}")

    # 2. Pathogenic variants by category
    for category, df in pathogenic_analysis.items():
        if len(df) > 0:
            output_file = output_dir / f"{category}.csv"
            df.to_csv(output_file, index=False)
            logger.info(f"   ✓ {category}: {output_file} ({len(df)} variants)")

    # 3. Summary statistics
    summary_file = output_dir / "summary_statistics.txt"
    with open(summary_file, "w") as f:
        f.write("=" * 70 + "\n")
        f.write("VariDex Pipeline Analysis Summary\n")
        f.write("=" * 70 + "\n\n")

        f.write(f"Total variants analyzed: {len(annotated_df):,}\n\n")

        # ClinVar matches
        if "clinical_significance" in annotated_df.columns:
            clinvar_matches = annotated_df["clinical_significance"].notna().sum()
            f.write(f"ClinVar Matches:\n")
            f.write(f"   Total: {clinvar_matches:,}\n")
            f.write(f"   Coverage: {100*clinvar_matches/len(annotated_df):.2f}%\n\n")

        # gnomAD annotation
        if "gnomad_af" in annotated_df.columns:
            gnomad_found = annotated_df["gnomad_af"].notna().sum()
            f.write(f"gnomAD Annotation:\n")
            f.write(f"   Found: {gnomad_found:,}\n")
            f.write(f"   Novel: {annotated_df['gnomad_af'].isna().sum():,}\n")
            f.write(f"   Coverage: {100*gnomad_found/len(annotated_df):.2f}%\n\n")

        # Pathogenic variants
        f.write(f"Pathogenic Variants:\n")
        for category, df in pathogenic_analysis.items():
            f.write(f"   {category}: {len(df):,}\n")

    logger.info(f"   ✓ Summary: {summary_file}")


def main():
    parser = argparse.ArgumentParser(
        description="VariDex Pipeline: ClinVar + gnomAD Integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--user-variants",
        type=Path,
        required=True,
        help="User genome variants file (CSV/TSV/VCF)",
    )

    parser.add_argument(
        "--clinvar",
        type=Path,
        required=True,
        help="ClinVar VCF file (e.g., clinvar_GRCh37.vcf.gz)",
    )

    parser.add_argument(
        "--gnomad-dir",
        type=Path,
        default=Path("gnomad"),
        help="Directory with gnomAD chromosome files (default: gnomad)",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results"),
        help="Output directory for results (default: results)",
    )

    parser.add_argument(
        "--max-af",
        type=float,
        default=None,
        help="Maximum allele frequency threshold (e.g., 0.01 for 1%%)",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("🧬 VariDex Pipeline: ClinVar + gnomAD Integration")
    print("=" * 70)
    print()

    try:
        # Step 1: Load user variants
        user_df = load_user_variants(args.user_variants)

        # Step 2: Match with ClinVar
        matched = match_with_clinvar(user_df, args.clinvar)

        # Step 3: Annotate with gnomAD
        annotated = annotate_with_gnomad(matched, args.gnomad_dir, max_af=args.max_af)

        # Step 4: Analyze pathogenic variants
        pathogenic = analyze_pathogenic_variants(annotated)

        # Step 5: Generate reports
        generate_report(annotated, pathogenic, args.output_dir)

        print("\n" + "=" * 70)
        print("✅ Pipeline Complete!")
        print("=" * 70)
        print(f"\nResults saved to: {args.output_dir.absolute()}")
        print()

    except Exception as e:
        logger.error(f"\n❌ Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
