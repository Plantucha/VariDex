#!/usr/bin/env python3
"""
varidex/io/loaders/clinvar.py - ClinVar Data Loader v6.1.0 DEVELOPMENT
Load ClinVar VCF, TSV, variant_summary with auto-detection.
Returns DataFrame: rsid, chromosome, position, ref/alt_allele, gene, clinical_sig, coord_key

v6.1.0 Changes:
- Added tqdm progress bars for visual feedback
- Chunked reading for better memory efficiency
- Stage-by-stage progress indicators
- Optimized multiallelic splitting
"""

import pandas as pd
import gzip
import re
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable
from tqdm import tqdm
from varidex.version import __version__
from varidex.exceptions import DataLoadError, ValidationError, FileProcessingError
from varidex.io.normalization import normalize_dataframe_coordinates

logger: logging.Logger = logging.getLogger(__name__)

CLINVAR_FILE_TYPES: List[str] = ["vcf", "vcf_tsv", "variant_summary"]
REQUIRED_COORD_COLUMNS: List[str] = [
    "chromosome",
    "position",
    "ref_allele",
    "alt_allele",
]
VALID_CHROMOSOMES: List[str] = [str(i) for i in range(1, 23)] + ["X", "Y", "MT"]
CHROMOSOME_MAX_POSITIONS: Dict[str, int] = {
    "1": 250_000_000,
    "2": 243_000_000,
    "3": 198_000_000,
    "4": 191_000_000,
    "5": 181_000_000,
    "6": 171_000_000,
    "7": 160_000_000,
    "8": 146_000_000,
    "9": 142_000_000,
    "10": 136_000_000,
    "11": 135_000_000,
    "12": 134_000_000,
    "13": 115_000_000,
    "14": 107_000_000,
    "15": 103_000_000,
    "16": 90_500_000,
    "17": 84_000_000,
    "18": 80_500_000,
    "19": 59_000_000,
    "20": 64_500_000,
    "21": 48_000_000,
    "22": 52_000_000,
    "X": 156_000_000,
    "Y": 57_000_000,
    "MT": 17_000,
}
CLINVAR_COLUMNS: Dict[str, List[str]] = {
    "rsid": ["#AlleleID", "RS# (dbSNP)", "rsid"],
    "gene": ["GeneSymbol", "Gene(s)", "gene"],
    "clinical_sig": ["ClinicalSignificance", "clinical_significance"],
    "review_status": ["ReviewStatus", "review_status"],
    "variant_type": ["Type", "VariantType", "variant_type"],
    "chromosome": ["Chromosome", "chromosome", "chr"],
    "position": ["Start", "PositionVCF", "position", "pos"],
}


def count_file_lines(filepath: Path) -> int:
    """Count total lines in file (fast for progress bar)."""
    try:
        opener = (
            gzip.open(filepath, "rt")
            if str(filepath).endswith(".gz")
            else open(filepath, "r")
        )
        with opener as f:
            # Fast line counting
            lines = sum(1 for _ in f if not _.startswith("#"))
        return lines
    except Exception:
        return 0


def detect_clinvar_file_type(filepath: Path) -> str:
    """Auto-detect: vcf|vcf_tsv|variant_summary."""
    try:
        opener: Any = (
            gzip.open(filepath, "rt")
            if str(filepath).endswith(".gz")
            else open(filepath, "r")
        )
        with opener as f:
            lines: List[str] = [f.readline() for _ in range(5)]
        if not lines or not lines[0]:
            raise ValidationError("Empty file", context={"file": str(filepath)})
        first_line: str = lines[0].strip()
        if first_line.startswith("##fileformat=VCF") or first_line.startswith("#CHROM"):
            return "vcf"
        header_lower: str = first_line.lower()
        vcf_markers: int = sum(
            [
                "chrom" in header_lower,
                "pos" in header_lower or "position" in header_lower,
                "ref" in header_lower,
                "alt" in header_lower,
            ]
        )
        return "vcf_tsv" if vcf_markers >= 3 else "variant_summary"
    except Exception as e:
        raise FileProcessingError(
            "Failed to detect file type",
            context={"file": str(filepath), "error": str(e)},
        )


def validate_chromosome_consistency(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize chr naming (chr1→1, M→MT, NC_000001→1)."""
    if "chromosome" not in df.columns:
        return df
    df = df.copy()
    df["chromosome"] = df["chromosome"].str.replace("^chr", "", regex=True, case=False)
    nc_pattern: re.Pattern[str] = re.compile(r"^NC_0000(0[1-9]|1[0-9]|2[0-2])")

    def map_nc(c: Any) -> Any:
        if pd.isna(c):
            return c
        m: Optional[re.Match[str]] = nc_pattern.match(str(c))
        return str(int(m.group(1))) if m else c

    df["chromosome"] = (
        df["chromosome"]
        .apply(map_nc)
        .replace({"23": "X", "24": "Y", "M": "MT"})
        .str.upper()
    )
    return df


def validate_position_ranges(df: pd.DataFrame) -> pd.DataFrame:
    """VECTORIZED: Validate positions within chr bounds."""
    if "chromosome" not in df.columns or "position" not in df.columns:
        return df
    orig_len: int = len(df)
    invalid_mask: pd.Series = (df["position"] < 1) | df["position"].isna()
    for chrom, max_pos in CHROMOSOME_MAX_POSITIONS.items():
        chrom_mask: pd.Series = (df["chromosome"] == chrom) & (df["position"] > max_pos)
        if chrom_mask.any():
            logger.warning(
                f"{chrom_mask.sum()} variants on {chrom} exceed max {max_pos}"
            )
        invalid_mask |= chrom_mask
    df = df[~invalid_mask].reset_index(drop=True)
    if orig_len > len(df):
        logger.info(f"Filtered {orig_len - len(df)} invalid positions")
    return df


def split_multiallelic_vcf(df: pd.DataFrame) -> pd.DataFrame:
    """Split ALT=A,G → 2 rows with progress bar."""
    if df is None or len(df) == 0 or "ALT" not in df.columns:
        return df
    try:
        multiallelic: pd.DataFrame = df[df["ALT"].str.contains(",", na=False)]
        if len(multiallelic) == 0:
            return df

        print(f"  📊 Splitting {len(multiallelic):,} multiallelic variants...")

        biallelic: pd.DataFrame = df[~df["ALT"].str.contains(",", na=False)].copy()
        split_rows: List[pd.Series] = []
        failed: int = 0

        # Progress bar for splitting
        for idx, row in tqdm(
            multiallelic.iterrows(),
            total=len(multiallelic),
            desc="  Splitting",
            unit="var",
            leave=False,
        ):
            try:
                for alt in [a.strip() for a in str(row["ALT"]).split(",") if a.strip()]:
                    new_row: pd.Series = row.copy()
                    new_row["ALT"] = alt
                    new_row["alt_allele"] = alt.upper()
                    split_rows.append(new_row)
            except Exception as e:
                failed += 1
                logger.error(f"Split failed row {idx}: {e}")

        if failed > 0:
            logger.warning(f"{failed}/{len(multiallelic)} splits failed")

        if split_rows:
            result: pd.DataFrame = pd.concat(
                [biallelic, pd.DataFrame(split_rows)], ignore_index=True
            )
            print(
                f"  ✓ Split {len(multiallelic):,} → {len(split_rows):,} biallelic "
                f"({failed} fails)"
            )
            return result
        return df
    except Exception as e:
        raise FileProcessingError(
            "Multiallelic split failed", context={"error": str(e)}
        )


def extract_rsid_from_info(info_str: Any) -> Optional[str]:
    """Extract rsID from INFO field (RS=123456 -> rs123456)."""
    if pd.isna(info_str) or str(info_str) == "nan":
        return None
    match: Optional[re.Match[str]] = re.search(r"RS=([0-9,]+)", str(info_str))
    if match:
        rsid_num: str = match.group(1).split(",")[0]
        return "rs" + rsid_num
    return None


def load_clinvar_vcf(
    filepath: Path, checkpoint_dir: Optional[Path] = None
) -> pd.DataFrame:
    """Load full ClinVar VCF with progress visualization."""
    print(f"\n{'='*70}")
    print(f"📁 LOADING VCF: {filepath.name}")
    print(f"{'='*70}")

    try:
        # Count lines for progress bar
        print("📊 Counting lines...")
        total_lines = count_file_lines(filepath)
        print(f"  ✓ Found {total_lines:,} data lines\n")

        # Read VCF in chunks with progress bar
        print("📖 Reading VCF data...")
        chunks: List[pd.DataFrame] = []
        chunk_size = 50000

        with tqdm(
            total=total_lines, desc="  Loading", unit="lines", unit_scale=True
        ) as pbar:
            for chunk in pd.read_csv(
                filepath,
                sep="\t",
                comment="#",
                names=["CHROM", "POS", "ID", "REF", "ALT", "QUAL", "FILTER", "INFO"],
                dtype={
                    "CHROM": str,
                    "POS": "Int64",
                    "ID": str,
                    "REF": str,
                    "ALT": str,
                },
                chunksize=chunk_size,
                low_memory=False,
                on_bad_lines="skip",
            ):
                chunks.append(chunk)
                pbar.update(len(chunk))

        df: pd.DataFrame = pd.concat(chunks, ignore_index=True)
        print(f"  ✓ Loaded {len(df):,} variants\n")

        if len(df) == 0:
            raise ValidationError("VCF empty", context={"file": str(filepath)})

        # Parse INFO field with progress
        print("🔍 Parsing INFO fields...")

        def parse_info(info: Any) -> Dict[str, str]:
            result: Dict[str, str] = {"CLNSIG": "", "CLNREVSTAT": ""}
            if pd.isna(info):
                return result
            for item in str(info).split(";"):
                if "=" in item:
                    k, v = item.split("=", 1)
                    if k in result:
                        result[k] = v
            return result

        tqdm.pandas(desc="  Parsing", leave=False)
        info_parsed: pd.Series = df["INFO"].apply(parse_info)
        df["clinical_sig"] = info_parsed.apply(lambda x: x["CLNSIG"])
        df["review_status"] = info_parsed.apply(lambda x: x["CLNREVSTAT"])
        print("  ✓ INFO fields parsed\n")

        # Extract basic fields
        print("🧬 Extracting coordinates and alleles...")
        df["chromosome"] = df["CHROM"].str.replace("chr", "").str.upper()
        df["position"] = df["POS"]
        df["ref_allele"] = df["REF"].str.upper()
        df["alt_allele"] = df["ALT"].str.upper()
        print("  ✓ Extracted\n")

        # Split multiallelic variants
        df = split_multiallelic_vcf(df)
        print()

        # Validate and normalize
        print("✅ Validating chromosomes and positions...")
        df = validate_chromosome_consistency(df)
        df = validate_position_ranges(df)
        df = normalize_dataframe_coordinates(df)
        print("  ✓ Validated\n")

        # Filter valid chromosomes
        orig_len: int = len(df)
        df = df[df["chromosome"].isin(VALID_CHROMOSOMES)]
        print(f"🔬 Filtered to valid chromosomes: {orig_len:,} → {len(df):,}\n")

        # Extract rsIDs from INFO field
        if "INFO" in df.columns:
            print("🆔 Extracting rsIDs from INFO field...")
            tqdm.pandas(desc="  Extracting", leave=False)
            df["rsid"] = df["INFO"].apply(extract_rsid_from_info)
            rsid_count: int = df["rsid"].notna().sum()
            print(
                f"  ✓ Extracted {rsid_count:,} rsIDs "
                f"({100*rsid_count/len(df):.1f}%)\n"
            )

        print(f"{'='*70}")
        print(f"✅ COMPLETE: {len(df):,} variants loaded")
        print(f"{'='*70}\n")

        return df
    except Exception as e:
        raise DataLoadError(
            "VCF load failed", context={"file": str(filepath), "error": str(e)}
        )


def load_clinvar_vcf_tsv(
    filepath: Path, checkpoint_dir: Optional[Path] = None
) -> pd.DataFrame:
    """Load VCF-style TSV with progress."""
    print(f"\n{'='*70}")
    print(f"📁 LOADING VCF-TSV: {filepath.name}")
    print(f"{'='*70}\n")

    try:
        print("📖 Reading TSV data...")
        df: pd.DataFrame = pd.read_csv(
            filepath, sep="\t", low_memory=True, on_bad_lines="skip"
        )
        print(f"  ✓ Loaded {len(df):,} rows\n")

        if len(df) == 0:
            raise ValidationError("TSV empty", context={"file": str(filepath)})

        print("🔄 Mapping columns...")
        col_map: Dict[str, str] = {}
        target_candidates: Dict[str, List[str]] = {
            "chromosome": ["chromosome", "chrom", "chr"],
            "position": ["position", "pos"],
            "ref_allele": ["ref", "ref_allele", "reference"],
            "alt_allele": ["alt", "alt_allele", "alternate"],
            "gene": ["gene", "gene_symbol"],
            "clinical_sig": [
                "clinical_significance",
                "clin_sig",
                "significance",
            ],
        }
        for target, candidates in target_candidates.items():
            for col in df.columns:
                if col in candidates or any(cand in col.lower() for cand in candidates):
                    col_map[col] = target
                    break

        df = df.rename(columns=col_map)
        print(f"  ✓ Mapped {len(col_map)} columns\n")

        print("✅ Validating and normalizing...")
        df = validate_chromosome_consistency(df)
        df = validate_position_ranges(df)
        df = normalize_dataframe_coordinates(df)

        orig_len: int = len(df)
        df = df.reset_index(drop=True)
        if orig_len > len(df):
            print(f"  Deduped: {orig_len:,} → {len(df):,}")
        print(f"  ✓ {len(df):,} variants\n")

        print(f"{'='*70}")
        print(f"✅ COMPLETE: {len(df):,} variants loaded")
        print(f"{'='*70}\n")

        return df
    except Exception as e:
        raise DataLoadError(
            "VCF-TSV load failed",
            context={"file": str(filepath), "error": str(e)},
        )


def load_variant_summary(
    filepath: Path, checkpoint_dir: Optional[Path] = None
) -> pd.DataFrame:
    """Load variant_summary.txt with progress."""
    print(f"\n{'='*70}")
    print(f"📁 LOADING VARIANT_SUMMARY: {filepath.name}")
    print(f"{'='*70}\n")

    try:
        print("🔍 Detecting separator...")
        sep: Optional[str] = None
        for test_sep in ["\t", ",", "|"]:
            try:
                test_df: pd.DataFrame = pd.read_csv(
                    filepath, sep=test_sep, low_memory=False, nrows=5
                )
                if len(test_df.columns) > 10:
                    sep = test_sep
                    print(f"  ✓ Detected: '{test_sep}'\n")
                    break
            except Exception:
                continue

        if sep is None:
            raise ValidationError("Unknown separator", context={"file": str(filepath)})

        print("📖 Reading summary data...")
        df: pd.DataFrame = pd.read_csv(filepath, sep=sep, low_memory=False)
        print(f"  ✓ Loaded {len(df):,} rows\n")

        if len(df) == 0:
            raise ValidationError("Summary empty", context={"file": str(filepath)})

        print("🔄 Mapping columns...")
        col_map: Dict[str, str] = {}
        for target, candidates in CLINVAR_COLUMNS.items():
            for col in df.columns:
                if col in candidates or any(
                    cand.lower() in col.lower() for cand in candidates
                ):
                    col_map[col] = target
                    break

        df = df.rename(columns=col_map)
        print(f"  ✓ Mapped {len(col_map)} columns\n")

        if "rsid" in df.columns:
            print("🆔 Filtering rsIDs...")
            df["rsid"] = df["rsid"].astype(str)
            rsid_pattern: re.Pattern[str] = re.compile(r"^rs\d+$")
            orig_len: int = len(df)
            df = df[df["rsid"].str.match(rsid_pattern, na=False)]
            if orig_len > len(df):
                print(f"  Filtered: {orig_len:,} → {len(df):,}\n")

        if "clinical_sig" in df.columns:
            print("⚠️  Checking for conflicts...")
            df["has_conflict"] = df["clinical_sig"].apply(
                lambda x: any(
                    kw in str(x).lower() for kw in ["conflict", "conflicting", "|"]
                )
            )
            conflicts = df["has_conflict"].sum()
            print(f"  Found {conflicts:,} conflicting entries\n")

        if "rsid" in df.columns and df["rsid"].duplicated().any():
            print("🔗 Aggregating duplicate rsIDs...")
            agg_dict: Dict[str, Callable[..., str]] = {
                "clinical_sig": lambda x: " | ".join(x.dropna().astype(str).unique()),
                "gene": lambda x: ";".join(x.dropna().astype(str).unique()),
            }
            for col in ["review_status", "variant_type"]:
                if col in df.columns:
                    agg_dict[col] = lambda x: " | ".join(
                        x.dropna().astype(str).unique()
                    )
            df = df.groupby("rsid", as_index=False).agg(agg_dict)
            print(f"  ✓ Aggregated to {len(df):,} unique rsIDs\n")

        if all(col in df.columns for col in REQUIRED_COORD_COLUMNS):
            print("✅ Validating coordinates...")
            df = validate_chromosome_consistency(df)
            df = validate_position_ranges(df)
            df = normalize_dataframe_coordinates(df)
            print("  ✓ Validated\n")

        print(f"{'='*70}")
        print(f"✅ COMPLETE: {len(df):,} variants loaded")
        print(f"{'='*70}\n")

        return df
    except Exception as e:
        raise DataLoadError(
            "variant_summary load failed",
            context={"file": str(filepath), "error": str(e)},
        )


def load_clinvar_file(filepath: Any, **kwargs: Any) -> pd.DataFrame:
    """
    Auto-detect and load ClinVar file (main entry).
    Supports: VCF, VCF-TSV, variant_summary.txt
    Returns DataFrame with coord_key and rsid.
    """
    filepath = Path(filepath)
    try:
        file_type: str = detect_clinvar_file_type(filepath)

        loaders: Dict[str, Callable[..., pd.DataFrame]] = {
            "vcf": load_clinvar_vcf,
            "vcf_tsv": load_clinvar_vcf_tsv,
            "variant_summary": load_variant_summary,
        }

        loader: Optional[Callable[..., pd.DataFrame]] = loaders.get(file_type)
        if loader is None:
            raise ValueError(f"Unknown file type: {file_type}")

        return loader(filepath, **kwargs)
    except Exception as e:
        raise DataLoadError(
            "ClinVar load failed",
            context={"file": str(filepath), "error": str(e)},
        )
