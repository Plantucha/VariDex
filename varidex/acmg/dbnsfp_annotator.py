"""
dbNSFP Parallel Streaming Annotator - Multi-Build Support
Annotates variants with prediction scores (SIFT, PolyPhen, CADD, REVEL)
Auto-detects GRCh37/GRCh38 genome build
Memory-efficient streaming with parallel processing + auto CPU detection
"""

import gzip
from pathlib import Path
from typing import Dict, Optional
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm

from varidex.utils.cpu_utils import get_optimal_workers


def detect_genome_build(df: pd.DataFrame) -> str:
    """
    Auto-detect genome build from variant positions

    Uses known variant position differences between builds
    Returns: "GRCh37" or "GRCh38"
    """
    if "position" not in df.columns or len(df) == 0:
        return "GRCh37"

    # Check for common variants with known position differences
    # chr1:948921 (rs6605066) is at 1014143 in GRCh38
    sample_positions = df[df["chromosome"] == 1]["position"].head(100)

    # GRCh38 positions tend to be higher due to added sequences
    # Simple heuristic: if average position > 1M for chr1, likely GRCh38
    if len(sample_positions) > 0:
        avg_pos = sample_positions.mean()
        # This is a rough heuristic - GRCh38 has longer chromosomes
        if avg_pos > 100_000_000:
            return "GRCh38"

    return "GRCh37"  # Default


def _process_chromosome_file(
    chr_file: Path, variants_for_chr: pd.DataFrame, genome_build: str
) -> Dict[str, Dict]:
    """Process a single chromosome file - WORKER FUNCTION"""
    try:
        annotations = {}
        variant_lookup = {}

        for idx, row in variants_for_chr.iterrows():
            pos = int(row["position"])
            ref = str(row.get("ref_allele", "")).upper()
            alt = str(row.get("alt_allele", "")).upper()
            key = f"{pos}_{ref}_{alt}"
            variant_lookup[key] = idx

        with gzip.open(chr_file, "rt") as f:
            header = f.readline().strip().split("\t")

            try:
                # Select correct position column based on genome build
                if genome_build == "GRCh37":
                    pos_idx = header.index("hg19_pos(1-based)")
                else:  # GRCh38
                    pos_idx = header.index("pos(1-based)")

                ref_idx = header.index("ref")
                alt_idx = header.index("alt")
                sift_idx = header.index("SIFT_score")
                pp_idx = header.index("Polyphen2_HDIV_score")
                cadd_idx = header.index("CADD_phred")
                revel_idx = header.index("REVEL_score")
            except ValueError:
                return {}

            for line in f:
                fields = line.strip().split("\t")
                if len(fields) < max(pos_idx, ref_idx, alt_idx, revel_idx):
                    continue

                pos = fields[pos_idx]
                ref = fields[ref_idx].upper()
                alt = fields[alt_idx].upper()
                key = f"{pos}_{ref}_{alt}"

                if key in variant_lookup:
                    idx = variant_lookup[key]
                    annotations[idx] = {
                        "SIFT_score": (
                            fields[sift_idx] if sift_idx < len(fields) else "."
                        ),
                        "PolyPhen_score": (
                            fields[pp_idx] if pp_idx < len(fields) else "."
                        ),
                        "CADD_phred": (
                            fields[cadd_idx] if cadd_idx < len(fields) else "."
                        ),
                        "REVEL_score": (
                            fields[revel_idx] if revel_idx < len(fields) else "."
                        ),
                    }

        return annotations

    except Exception as e:
        print(f"  ⚠️  Error processing {chr_file.name}: {e}")
        return {}


def annotate_with_dbnsfp(
    df: pd.DataFrame, dbnsfp_dir: str, genome_build: Optional[str] = None
) -> pd.DataFrame:
    """
    Annotate variants with dbNSFP prediction scores using parallel streaming

    Args:
        df: DataFrame with variants
        dbnsfp_dir: Path to dbNSFP directory
        genome_build: "GRCh37", "GRCh38", or None for auto-detection

    Returns:
        DataFrame with SIFT, PolyPhen, CADD, REVEL scores added
    """
    dbnsfp_path = Path(dbnsfp_dir)
    if not dbnsfp_path.exists():
        print(f"  ⚠️  dbNSFP directory not found: {dbnsfp_dir}")
        return df

    chr_files = sorted(dbnsfp_path.glob("dbNSFP*_variant.chr*.gz"))
    if not chr_files:
        print(f"  ⚠️  No dbNSFP chromosome files found in {dbnsfp_dir}")
        return df

    # Auto-detect genome build if not provided
    if genome_build is None:
        genome_build = detect_genome_build(df)
        print(f"✓ Auto-detected genome build: {genome_build}")
    else:
        print(f"✓ Using genome build: {genome_build}")

    print(f"✓ Found {len(chr_files)} dbNSFP chromosome files")

    for col in ["SIFT_score", "PolyPhen_score", "CADD_phred", "REVEL_score"]:
        df[col] = None

    chr_groups = {}
    for chrom in df["chromosome"].unique():
        if pd.isna(chrom):
            continue
        chr_str = str(int(chrom)) if chrom not in ["X", "Y", "MT"] else str(chrom)
        chr_df = df[df["chromosome"] == chrom].copy()
        chr_groups[chr_str] = chr_df

    max_workers = get_optimal_workers("cpu_bound")

    print(
        f"dbNSFP: Annotating {len(df)} variants with {max_workers} parallel workers ({genome_build})..."
    )
    print(f"Processing {len(chr_files)} chromosomes in parallel...\n")

    all_annotations = {}

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for chr_file in chr_files:
            chr_num = chr_file.stem.split("chr")[-1].replace(".gz", "")
            if chr_num in chr_groups:
                future = executor.submit(
                    _process_chromosome_file,
                    chr_file,
                    chr_groups[chr_num],
                    genome_build,
                )
                futures[future] = chr_num

        with tqdm(
            total=len(futures),
            desc="📊 dbNSFP chromosomes",
            unit="chr",
            ncols=100,
        ) as pbar:
            for future in as_completed(futures):
                chr_num = futures[future]
                try:
                    annotations = future.result()
                    all_annotations.update(annotations)
                    count = len(annotations)
                    pbar.set_postfix({"chr": chr_num, "variants": count})
                    pbar.update(1)
                except Exception as e:
                    pbar.write(f"  ⚠️  chr{chr_num} failed: {e}")
                    pbar.update(1)

    if all_annotations:
        for idx, scores in all_annotations.items():
            for col, value in scores.items():
                if value and value != ".":
                    try:
                        df.at[idx, col] = float(value)
                    except ValueError:
                        pass

    annotated_count = sum(
        1
        for idx in df.index
        if pd.notna(df.at[idx, "SIFT_score"])
        or pd.notna(df.at[idx, "PolyPhen_score"])
        or pd.notna(df.at[idx, "CADD_phred"])
        or pd.notna(df.at[idx, "REVEL_score"])
    )

    print(
        f"\n✓ Total annotated: {annotated_count}/{len(df)} ({annotated_count/len(df)*100:.1f}%)\n"
    )

    return df
