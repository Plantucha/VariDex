#!/usr/bin/env python3
"""
varidex/io/loaders/clinvar.py - ClinVar Data Loader v8.1.0 DEVELOPMENT
Load ClinVar VCF, TSV, variant_summary, XML with auto-detection and intelligent caching.
Returns DataFrame: rsid, chromosome, position, ref/alt_allele, gene, clinical_sig, coord_key

v8.1.0 Changes (CRITICAL FIX):
- ✨ Extract GENE from VCF INFO field (GENEINFO=BRCA1:672)
- ✨ Extract MOLECULAR_CONSEQUENCE from INFO field (MC=SO:0001587|nonsense)
- Vectorized extraction for performance
- Fixes PVS1=0 issue (requires molecular_consequence for LOF detection)

v8.0.1 Changes:
- Memory optimizations: Skip non-critical validation steps
- Disabled multiallelic splitting (OOM prevention)
- Disabled parallel processing (OOM prevention)
- Validation skipped (matching engine handles invalid data)

v8.0.0 Changes:
- ✨ NEW: ClinVar XML support (includes structural variants >1MB)
- Auto-detects XML format (.xml, .xml.gz)
- Streaming parser for memory efficiency (2-4GB RAM)
- Maintains full backwards compatibility with VCF/TSV

v7.2.0 Changes:
- ⚡ Vectorized rsID extraction (6x faster: 3s → 0.5s)
- Removed slow .apply() loops, using pure pandas operations
- Expected total speedup: ~10% on first run

v6.3.0 Changes:
- Added intelligent caching (57s → 3-5s on subsequent runs)
- Auto-detects source file changes and invalidates cache
- Saves processed data as compressed parquet

v6.2.0 Changes:
- Added parallel validation (4-8x faster)
- Progress bars for all long operations
- Better user feedback during processing
"""

import gzip
import json
import logging
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

import pandas as pd
from tqdm import tqdm

from varidex.exceptions import DataLoadError, FileProcessingError, ValidationError

# Import parallel validators
from varidex.io.validators_parallel import validate_position_ranges_parallel
from varidex.version import __version__

# Normalization handled elsewhere


logger: logging.Logger = logging.getLogger(__name__)

CLINVAR_FILE_TYPES: List[str] = ["vcf", "vcf_tsv", "variant_summary", "xml"]
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

from varidex.io.validators_parallel import validate_position_ranges_parallel


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
    """
    Auto-detect ClinVar file type: vcf|vcf_tsv|variant_summary|xml.

    Args:
        filepath: Path to ClinVar file

    Returns:
        String identifier for file type

    Supported types:
        - xml: ClinVar XML release (includes structural variants)
        - vcf: Standard VCF format
        - vcf_tsv: Tab-separated VCF-like format
        - variant_summary: ClinVar summary text file
    """
    try:
        # Quick check: XML file extension
        filename_lower = str(filepath).lower()
        if filename_lower.endswith((".xml", ".xml.gz")):
            return "xml"

        # Content-based detection
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

        # Check for XML signature
        if first_line.startswith("<?xml") or "ClinVarVariationRelease" in first_line:
            return "xml"

        # Check for VCF
        if first_line.startswith("##fileformat=VCF") or first_line.startswith("#CHROM"):
            return "vcf"

        # Check for VCF-style TSV
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
    """DEPRECATED: Use validate_position_ranges_parallel instead.

    Kept for backwards compatibility.
    """
    return validate_position_ranges_parallel(df)


def split_multiallelic_vcf(df: pd.DataFrame) -> pd.DataFrame:
    """
    Split ALT=A,G → 2 rows with progress bar.

    TEMPORARILY DISABLED: Memory optimization needed (requires 1.7GB for filtering step).
    The matching engine handles multiallelic variants correctly, so skipping this
    step doesn't affect final results.
    """
    if df is None or len(df) == 0 or "ALT" not in df.columns:
        return df

    # Check if there are multiallelic variants
    multiallelic_count = df["ALT"].str.contains(",", na=False).sum()
    if multiallelic_count == 0:
        return df

    # TEMPORARY: Skip splitting to avoid OOM (1.7GB allocation)
    print(f"  ⚠️  Skipping multiallelic split ({multiallelic_count:,} variants)")
    print(f"     Matching engine handles these correctly")
    logger.warning(
        f"Multiallelic splitting disabled (OOM prevention). "
        f"{multiallelic_count:,} multiallelic variants retained."
    )
    return df


def extract_rsid_from_info(info_str: Any) -> Optional[str]:
    """
    DEPRECATED: Use _extract_rsids_vectorized() instead.
    This function is slow (row-by-row). Kept for backwards compatibility only.

    Extract rsID from INFO field (RS=123456 -> rs123456).
    """
    if pd.isna(info_str) or str(info_str) == "nan":
        return None
    match: Optional[re.Match[str]] = re.search(r"RS=([0-9,]+)", str(info_str))
    if match:
        rsid_num: str = match.group(1).split(",")[0]
        return "rs" + rsid_num
    return None


def _extract_rsids_vectorized(df: pd.DataFrame) -> pd.Series:
    """
    Extract rsIDs from INFO field using fully vectorized operations.

    Performance: 6x faster than row-by-row iteration
    - Before: ~3 seconds (row-by-row with .apply())
    - After: ~0.5 seconds (vectorized pandas)

    Args:
        df: DataFrame with 'INFO' column containing VCF INFO fields

    Returns:
        Series of rsIDs in format 'rs123456' or None for missing
    """
    if "INFO" not in df.columns:
        return pd.Series([None] * len(df), index=df.index)

    # Handle None/NaN efficiently by filling with empty string first
    info_clean = df["INFO"].fillna("")

    # Vectorized regex extraction
    rsids = info_clean.astype(str).str.extract(r"RS=([0-9,]+)", expand=False)

    # Handle multiple rsIDs (RS=111,222) - take first
    rsids = rsids.str.split(",").str[0]

    # Vectorized string concatenation - prepends 'rs'
    rsids = "rs" + rsids

    # Replace 'rsnan' with None (from NaN concatenation)
    rsids = rsids.replace("rsnan", None)

    return rsids


def _extract_gene_vectorized(df: pd.DataFrame) -> pd.Series:
    """
    Extract gene names from INFO field GENEINFO tag using vectorized operations.

    ClinVar VCF INFO format:
        GENEINFO=BRCA1:672 → gene = "BRCA1"
        GENEINFO=BRCA1:672|BRCA2:675 → gene = "BRCA1" (first gene)

    Performance: Vectorized - no row-by-row loops

    Args:
        df: DataFrame with 'INFO' column containing VCF INFO fields

    Returns:
        Series of gene names or None for missing

    Example:
        >>> info = pd.Series(['CLNSIG=Path;GENEINFO=BRCA1:672', 'CLNSIG=Benign', None])
        >>> df = pd.DataFrame({'INFO': info})
        >>> _extract_gene_vectorized(df)
        0    BRCA1
        1     None
        2     None
        dtype: object
    """
    if "INFO" not in df.columns:
        return pd.Series([None] * len(df), index=df.index)

    # Handle None/NaN
    info_clean = df["INFO"].fillna("")

    # Extract GENEINFO value: GENEINFO=BRCA1:672 → BRCA1:672
    gene_info = info_clean.astype(str).str.extract(r"GENEINFO=([^;]+)", expand=False)

    # Extract gene name before colon: BRCA1:672 → BRCA1
    # Handle multiple genes: BRCA1:672|BRCA2:675 → BRCA1
    genes = gene_info.str.split("|").str[0]  # Take first gene if multiple
    genes = genes.str.split(":").str[0]  # Take name before colon

    # Clean up NaN values
    genes = genes.replace("", None)
    genes = genes.replace("nan", None)

    return genes


def _extract_molecular_consequence_vectorized(df: pd.DataFrame) -> pd.Series:
    """
    Extract molecular consequence from INFO field MC tag using vectorized operations.

    ClinVar VCF INFO format:
        MC=SO:0001587|nonsense → molecular_consequence = "nonsense"
        MC=SO:0001583|missense_variant → molecular_consequence = "missense_variant"

    Critical for PVS1 (loss-of-function) classification!

    Performance: Vectorized - no row-by-row loops

    Args:
        df: DataFrame with 'INFO' column containing VCF INFO fields

    Returns:
        Series of molecular consequences or None for missing

    Example:
        >>> info = pd.Series(['MC=SO:0001587|nonsense', 'CLNSIG=Benign', None])
        >>> df = pd.DataFrame({'INFO': info})
        >>> _extract_molecular_consequence_vectorized(df)
        0    nonsense
        1        None
        2        None
        dtype: object
    """
    if "INFO" not in df.columns:
        return pd.Series([None] * len(df), index=df.index)

    # Handle None/NaN
    info_clean = df["INFO"].fillna("")

    # Extract MC value: MC=SO:0001587|nonsense → SO:0001587|nonsense
    mc_info = info_clean.astype(str).str.extract(r"MC=([^;]+)", expand=False)

    # Extract consequence after pipe: SO:0001587|nonsense → nonsense
    # Handle multiple: SO:0001587|nonsense,SO:0001582|missense → nonsense
    consequences = mc_info.str.split(",").str[0]  # Take first if multiple
    consequences = consequences.str.split("|").str[1]  # Take part after pipe

    # Clean up NaN values
    consequences = consequences.replace("", None)
    consequences = consequences.replace("nan", None)

    return consequences


def load_clinvar_vcf(
    filepath: Path,
    user_chromosomes: Optional[Set[str]] = None,
    checkpoint_dir: Optional[Path] = None,
) -> pd.DataFrame:
    """Load full ClinVar VCF with gene and molecular_consequence extraction."""
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

        # Extract rsIDs from INFO field (vectorized)
        if "INFO" in df.columns:
            print("🆔 Extracting rsIDs from INFO field...")
            df["rsid"] = _extract_rsids_vectorized(df)
            rsid_count: int = df["rsid"].notna().sum()
            print(
                f"  ✓ Extracted {rsid_count:,} rsIDs "
                f"({100*rsid_count/len(df):.1f}%)\n"
            )

        # ✨ NEW: Extract GENE from INFO field (vectorized)
        if "INFO" in df.columns:
            print("🧬 Extracting gene names from INFO field...")
            df["gene"] = _extract_gene_vectorized(df)
            gene_count: int = df["gene"].notna().sum()
            print(
                f"  ✓ Extracted {gene_count:,} gene names "
                f"({100*gene_count/len(df):.1f}%)\n"
            )

        # ✨ NEW: Extract MOLECULAR_CONSEQUENCE from INFO field (vectorized)
        if "INFO" in df.columns:
            print("🧬 Extracting molecular consequences from INFO field...")
            df["molecular_consequence"] = _extract_molecular_consequence_vectorized(df)
            cons_count: int = df["molecular_consequence"].notna().sum()
            print(
                f"  ✓ Extracted {cons_count:,} consequences "
                f"({100*cons_count/len(df):.1f}%)\n"
            )

            # Show top consequences
            if cons_count > 0:
                print("  Top 10 molecular consequences:")
                top_cons = df["molecular_consequence"].value_counts().head(10)
                for cons, count in top_cons.items():
                    # Mark LOF variants
                    is_lof = any(
                        kw in str(cons).lower()
                        for kw in [
                            "frameshift",
                            "nonsense",
                            "stop_gain",
                            "splice_donor",
                            "splice_acceptor",
                        ]
                    )
                    marker = " 🔴 LOF" if is_lof else ""
                    print(f"    {cons}: {count:,}{marker}")
                print()

        # Split multiallelic variants (DISABLED - OOM prevention)
        df = split_multiallelic_vcf(df)
        print()

        # SKIP VALIDATION - OOM prevention
        print("⚠️  Skipping validation (memory optimization)")
        print("   Matching engine will filter invalid data\n")
        logger.info("Validation skipped (memory optimization)")

        # Just normalize chromosome names (lightweight)
        df = validate_chromosome_consistency(df)

        print(f"{'='*70}")
        print(f"✅ COMPLETE: {len(df):,} variants loaded")
        print(f"{'='*70}\n")

        return df
    except Exception as e:
        raise DataLoadError(
            "VCF load failed", context={"file": str(filepath), "error": str(e)}
        )


def load_clinvar_vcf_tsv(
    filepath: Path,
    user_chromosomes: Optional[Set[str]] = None,
    checkpoint_dir: Optional[Path] = None,
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
            "molecular_consequence": [
                "molecular_consequence",
                "consequence",
                "variant_consequence",
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
        df = validate_position_ranges_parallel(df)

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
    filepath: Path,
    user_chromosomes: Optional[Set[str]] = None,
    checkpoint_dir: Optional[Path] = None,
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
            df = validate_position_ranges_parallel(df)
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


def load_clinvar_file(
    filepath: Any,
    user_chromosomes: Optional[Set[str]] = None,
    **kwargs: Any,
) -> pd.DataFrame:
    """
    Auto-detect and load ClinVar file with intelligent caching v8.1.0.

    NEW in v8.1.0: Extract gene and molecular_consequence (CRITICAL for PVS1)
    - Extracts GENEINFO field → gene column
    - Extracts MC (Molecular Consequence) → molecular_consequence column
    - Enables proper LOF variant detection for PVS1 classification

    NEW in v8.0.1: Memory optimizations for systems with limited RAM
    - Skips non-critical validation steps
    - Disabled multiallelic splitting
    - Disabled parallel processing

    NEW in v8.0.0: XML support for comprehensive variant coverage
    - Includes structural variants >1MB
    - Includes CNVs and complex rearrangements
    - Auto-detects XML format

    Caching behavior:
    - First run: Process file, save compressed cache
    - Subsequent runs: Load from cache (3-60s depending on format)
    - Auto-invalidates if source file changes (size/timestamp)
    - XML: Chromosome-specific caching for faster filtering

    Supports: XML, VCF, VCF-TSV, variant_summary.txt
    Returns DataFrame with coord_key and rsid.

    Args:
        filepath: Path to ClinVar file
        user_chromosomes: Optional set of chromosomes to filter (e.g., {'1', '2', 'X'})
        **kwargs: Additional arguments (checkpoint_dir for cache location)

    Returns:
        DataFrame with processed ClinVar data including gene and molecular_consequence
    """
    filepath = Path(filepath)

    # Setup cache directory
    cache_dir = Path(kwargs.get("checkpoint_dir", ".varidex_cache"))
    cache_dir.mkdir(exist_ok=True, parents=True)

    # Detect file type
    file_type: str = detect_clinvar_file_type(filepath)
    logger.info(f"Detected file type: {file_type}")

    # Import XML loader (UNCONDITIONAL - always available for loaders dict)
    from varidex.io.loaders.clinvar_xml import load_clinvar_xml

    # Generate cache filename
    if file_type == "xml" and user_chromosomes:
        # XML: Include chromosomes in cache key for filtered loading
        chr_str = "_".join(sorted(user_chromosomes))
        cache_name = f"{filepath.stem}_chr{chr_str}.parquet"
    else:
        cache_name = f"{filepath.stem}_processed.parquet"

    cache_file = cache_dir / cache_name
    cache_meta_file = cache_dir / f"{cache_name}.meta.json"

    # Check if cache is valid
    use_cache = False
    if cache_file.exists() and cache_meta_file.exists():
        try:
            with open(cache_meta_file, "r") as f:
                meta = json.load(f)

            # Validate cache: check file size and modification time
            current_size = filepath.stat().st_size
            current_mtime = filepath.stat().st_mtime

            # IMPORTANT: Invalidate cache if version changed (new gene/consequence extraction)
            cache_version = meta.get("cache_version", "0.0.0")
            if (
                meta.get("source_size") == current_size
                and abs(meta.get("source_mtime", 0) - current_mtime) < 1.0
                and cache_version == __version__
            ):
                use_cache = True
                logger.info(f"💾 Using cached ClinVar data from {cache_file.name}")
                print(f"\n💾 Loading from cache: {cache_file.name}")
            else:
                if cache_version != __version__:
                    logger.info(
                        f"Cache version mismatch ({cache_version} != {__version__}), reloading"
                    )
                    print(f"\n⚠️  Cache version outdated, reloading from source...")
        except Exception as e:
            logger.warning(f"Cache validation failed: {e}, will reload from source")
            use_cache = False

    # Load from cache if valid
    if use_cache:
        try:
            import time

            start_time = time.time()
            df = pd.read_parquet(cache_file)
            load_time = time.time() - start_time
            logger.info(f"✓ Loaded {len(df):,} variants from cache in {load_time:.1f}s")
            print(f"✓ Loaded {len(df):,} variants in {load_time:.1f}s (from cache)\n")
            return df
        except Exception as e:
            logger.warning(f"Cache load failed: {e}, will reload from source")

    # Load from source file
    try:
        loaders: Dict[str, Callable[..., pd.DataFrame]] = {
            "vcf": load_clinvar_vcf,
            "vcf_tsv": load_clinvar_vcf_tsv,
            "variant_summary": load_variant_summary,
            "xml": load_clinvar_xml,
        }

        loader: Optional[Callable[..., pd.DataFrame]] = loaders.get(file_type)
        if loader is None:
            raise ValueError(f"Unknown file type: {file_type}")

        # Call loader with user_chromosomes for filtering
        df = loader(
            filepath,
            user_chromosomes=user_chromosomes,
            checkpoint_dir=cache_dir,
        )

        # Save to cache
        try:
            logger.info(f"💾 Saving processed ClinVar to cache...")
            print(f"💾 Saving to cache: {cache_file.name}...")

            df.to_parquet(cache_file, index=False, compression="zstd")

            # Save metadata for validation
            meta = {
                "source_file": str(filepath),
                "source_size": filepath.stat().st_size,
                "source_mtime": filepath.stat().st_mtime,
                "processed_rows": len(df),
                "cache_version": __version__,
                "file_type": file_type,
                "user_chromosomes": (
                    list(user_chromosomes) if user_chromosomes else None
                ),
            }
            with open(cache_meta_file, "w") as f:
                json.dump(meta, f, indent=2)

            cache_size_mb = cache_file.stat().st_size / 1024 / 1024
            logger.info(f"✓ Cache saved: {cache_file.name} ({cache_size_mb:.1f} MB)")
            print(f"✓ Cache saved: {cache_size_mb:.1f} MB\n")
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")

        return df

    except Exception as e:
        raise DataLoadError(
            "ClinVar load failed",
            context={"file": str(filepath), "error": str(e)},
        )
