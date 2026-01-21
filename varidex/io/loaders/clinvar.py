#!/usr/bin/env python3
"""
varidex/io/loaders/clinvar.py - ClinVar Data Loader v6.0.0
Load ClinVar VCF, TSV, variant_summary with auto-detection.
Returns DataFrame: rsid, chromosome, position, ref/alt_allele, gene, clinical_sig, coord_key
"""
import pandas as pd
import gzip
import re
import logging
from pathlib import Path
from typing import Optional
from varidex.version import __version__
from varidex.exceptions import DataLoadError, ValidationError, FileProcessingError
from varidex.io.normalization import normalize_dataframe_coordinates

logger = logging.getLogger(__name__)

CLINVAR_FILE_TYPES = ['vcf', 'vcf_tsv', 'variant_summary']
REQUIRED_COORD_COLUMNS = ['chromosome', 'position', 'ref_allele', 'alt_allele']
VALID_CHROMOSOMES = [str(i) for i in range(1, 23)] + ['X', 'Y', 'MT']
CHROMOSOME_MAX_POSITIONS = {
    '1': 250_000_000, '2': 243_000_000, '3': 198_000_000, '4': 191_000_000,
    '5': 181_000_000, '6': 171_000_000, '7': 160_000_000, '8': 146_000_000,
    '9': 142_000_000, '10': 136_000_000, '11': 135_000_000, '12': 134_000_000,
    '13': 115_000_000, '14': 107_000_000, '15': 103_000_000, '16': 90_500_000,
    '17': 84_000_000, '18': 80_500_000, '19': 59_000_000, '20': 64_500_000,
    '21': 48_000_000, '22': 52_000_000, 'X': 156_000_000, 'Y': 57_000_000, 'MT': 17_000
}
CLINVAR_COLUMNS = {
    'rsid': ['#AlleleID', 'RS# (dbSNP)', 'rsid'],
    'gene': ['GeneSymbol', 'Gene(s)', 'gene'],
    'clinical_sig': ['ClinicalSignificance', 'clinical_significance'],
    'review_status': ['ReviewStatus', 'review_status'],
    'variant_type': ['Type', 'VariantType', 'variant_type'],
    'chromosome': ['Chromosome', 'chromosome', 'chr'],
    'position': ['Start', 'PositionVCF', 'position', 'pos']
}


def detect_clinvar_file_type(filepath: Path) -> str:
    """Auto-detect: vcf|vcf_tsv|variant_summary."""
    try:
        opener = gzip.open(filepath, 'rt') if str(filepath).endswith('.gz') else open(filepath, 'r')
        with opener as f:
            lines = [f.readline() for _ in range(5)]
        if not lines or not lines[0]:
            raise ValidationError("Empty file", context={'file': str(filepath)})
        first_line = lines[0].strip()
        if first_line.startswith('##fileformat=VCF') or first_line.startswith('#CHROM'):
            return 'vcf'
        header_lower = first_line.lower()
        vcf_markers = sum([
            'chrom' in header_lower,
            'pos' in header_lower or 'position' in header_lower,
            'ref' in header_lower,
            'alt' in header_lower
        ])
        return 'vcf_tsv' if vcf_markers >= 3 else 'variant_summary'
    except Exception as e:
        raise FileProcessingError(
            f"Failed to detect file type",
            context={'file': str(filepath), 'error': str(e)}
        )


def validate_chromosome_consistency(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize chr naming (chr1→1, M→MT, NC_000001→1)."""
    if 'chromosome' not in df.columns:
        return df
    df = df.copy()
    df['chromosome'] = df['chromosome'].str.replace('^chr', '', regex=True, case=False)
    nc_pattern = re.compile(r'^NC_0000(0[1-9]|1[0-9]|2[0-2])')

    def map_nc(c):
        if pd.isna(c):
            return c
        m = nc_pattern.match(str(c))
        return str(int(m.group(1))) if m else c

    df['chromosome'] = df['chromosome'].apply(map_nc).replace({
        '23': 'X', '24': 'Y', 'M': 'MT'
    }).str.upper()
    return df


def validate_position_ranges(df: pd.DataFrame) -> pd.DataFrame:
    """VECTORIZED: Validate positions within chr bounds."""
    if 'chromosome' not in df.columns or 'position' not in df.columns:
        return df
    orig_len = len(df)
    invalid_mask = (df['position'] < 1) | df['position'].isna()
    for chrom, max_pos in CHROMOSOME_MAX_POSITIONS.items():
        chrom_mask = (df['chromosome'] == chrom) & (df['position'] > max_pos)
        if chrom_mask.any():
            logger.warning(f"{chrom_mask.sum()} variants on {chrom} exceed max {max_pos}")
        invalid_mask |= chrom_mask
    df = df[~invalid_mask].reset_index(drop=True)
    if orig_len > len(df):
        logger.info(f"Filtered {orig_len - len(df)} invalid positions")
    return df


def split_multiallelic_vcf(df: pd.DataFrame) -> pd.DataFrame:
    """Split ALT=A,G → 2 rows."""
    if df is None or len(df) == 0 or 'ALT' not in df.columns:
        return df
    try:
        multiallelic = df[df['ALT'].str.contains(',', na=False)]
        if len(multiallelic) == 0:
            return df
        biallelic = df[~df['ALT'].str.contains(',', na=False)].copy()
        split_rows, failed = [], 0
        for idx, row in multiallelic.iterrows():
            try:
                for alt in [a.strip() for a in str(row['ALT']).split(',') if a.strip()]:
                    new_row = row.copy()
                    new_row['ALT'] = alt
                    new_row['alt_allele'] = alt.upper()
                    split_rows.append(new_row)
            except Exception as e:
                failed += 1
                logger.error(f"Split failed row {idx}: {e}")
        if failed > 0:
            logger.warning(f"{failed}/{len(multiallelic)} splits failed")
        if split_rows:
            result = pd.concat([biallelic, pd.DataFrame(split_rows)], ignore_index=True)
            print(f"  ✓ Split {len(multiallelic):,} → {len(split_rows):,} biallelic ({failed} fails)")
            return result
        return df
    except Exception as e:
        raise FileProcessingError(f"Multiallelic split failed", context={'error': str(e)})


def extract_rsid_from_info(info_str):
    """Extract rsID from INFO field (RS=123456 -> rs123456)."""
    if pd.isna(info_str) or str(info_str) == 'nan':
        return None
    match = re.search(r'RS=([0-9,]+)', str(info_str))
    if match:
        rsid_num = match.group(1).split(',')[0]
        return 'rs' + rsid_num
    return None


def load_clinvar_vcf(filepath: Path, checkpoint_dir: Optional[Path] = None) -> pd.DataFrame:
    """Load full ClinVar VCF."""
    filepath = Path(filepath)
    print(f"\n[VCF] {filepath.name}")
    try:
        df = pd.read_csv(
            filepath, sep='\t', comment='#',
            names=['CHROM', 'POS', 'ID', 'REF', 'ALT', 'QUAL', 'FILTER', 'INFO'],
            dtype={'CHROM': str, 'POS': 'Int64', 'ID': str, 'REF': str, 'ALT': str},
            low_memory=False, on_bad_lines='skip'
        )
        if len(df) == 0:
            raise ValidationError("VCF empty", context={'file': str(filepath)})

        def parse_info(info):
            result = {'CLNSIG': '', 'CLNREVSTAT': ''}
            if pd.isna(info):
                return result
            for item in str(info).split(';'):
                if '=' in item:
                    k, v = item.split('=', 1)
                    if k in result:
                        result[k] = v
            return result

        info_parsed = df['INFO'].apply(parse_info)
        df['clinical_sig'] = info_parsed.apply(lambda x: x['CLNSIG'])
        df['review_status'] = info_parsed.apply(lambda x: x['CLNREVSTAT'])
        df['chromosome'] = df['CHROM'].str.replace('chr', '').str.upper()
        df['position'] = df['POS']
        df['ref_allele'] = df['REF'].str.upper()
        df['alt_allele'] = df['ALT'].str.upper()

        df = split_multiallelic_vcf(df)
        df = validate_chromosome_consistency(df)
        df = validate_position_ranges(df)
        df = normalize_dataframe_coordinates(df)

        orig_len = len(df)
        df = df[df['chromosome'].isin(VALID_CHROMOSOMES)]

        # Extract rsIDs from INFO field
        if 'INFO' in df.columns:
            df['rsid'] = df['INFO'].apply(extract_rsid_from_info)
            rsid_count = df['rsid'].notna().sum()
            print(f"  Extracted {rsid_count:,} rsIDs from INFO field ({100*rsid_count/len(df):.1f}%)")

        print(f"  Filtered: {orig_len:,} → {len(df):,}\n  ✓ {len(df):,} variants")
        return df
    except Exception as e:
        raise DataLoadError(f"VCF load failed", context={'file': str(filepath), 'error': str(e)})


def load_clinvar_vcf_tsv(filepath: Path, checkpoint_dir: Optional[Path] = None) -> pd.DataFrame:
    """Load VCF-style TSV."""
    filepath = Path(filepath)
    print(f"\n[VCF-TSV] {filepath.name}")
    try:
        df = pd.read_csv(filepath, sep='\t', low_memory=True, on_bad_lines='skip')
        if len(df) == 0:
            raise ValidationError("TSV empty", context={'file': str(filepath)})

        col_map = {}
        for target, candidates in {
            'chromosome': ['chromosome', 'chrom', 'chr'],
            'position': ['position', 'pos'],
            'ref_allele': ['ref', 'ref_allele', 'reference'],
            'alt_allele': ['alt', 'alt_allele', 'alternate'],
            'gene': ['gene', 'gene_symbol'],
            'clinical_sig': ['clinical_significance', 'clin_sig', 'significance']
        }.items():
            for col in df.columns:
                if any(cand in col.lower() for cand in candidates):
                    col_map[col] = target
                    break

        df = df.rename(columns=col_map)
        df = validate_chromosome_consistency(df)
        df = validate_position_ranges(df)
        df = normalize_dataframe_coordinates(df)

        orig_len = len(df)
        df = df.reset_index(drop=True)
        if orig_len > len(df):
            print(f"  Deduped: {orig_len:,} → {len(df):,}")
        print(f"  ✓ {len(df):,} variants")
        return df
    except Exception as e:
        raise DataLoadError(f"VCF-TSV load failed", context={'file': str(filepath), 'error': str(e)})


def load_variant_summary(filepath: Path, checkpoint_dir: Optional[Path] = None) -> pd.DataFrame:
    """Load variant_summary.txt."""
    filepath = Path(filepath)
    print(f"\n[VARIANT_SUMMARY] {filepath.name}")
    try:
        sep = None
        for test_sep in ['\t', ',', '|']:
            try:
                test_df = pd.read_csv(filepath, sep=test_sep, low_memory=False, nrows=5)
                if len(test_df.columns) > 10:
                    sep = test_sep
                    break
            except:
                continue

        if sep is None:
            raise ValidationError("Unknown separator", context={'file': str(filepath)})

        df = pd.read_csv(filepath, sep=sep, low_memory=False)
        if len(df) == 0:
            raise ValidationError("Summary empty", context={'file': str(filepath)})

        col_map = {}
        for target, candidates in CLINVAR_COLUMNS.items():
            for col in df.columns:
                if col in candidates or any(cand.lower() in col.lower() for cand in candidates):
                    col_map[col] = target
                    break

        df = df.rename(columns=col_map)

        if 'rsid' in df.columns:
            df['rsid'] = df['rsid'].astype(str)
            rsid_pattern = re.compile(r'^rs\d+$')
            orig_len = len(df)
            df = df[df['rsid'].str.match(rsid_pattern, na=False)]
            if orig_len > len(df):
                print(f"  Filtered rsIDs: {orig_len:,} → {len(df):,}")

        if 'clinical_sig' in df.columns:
            df['has_conflict'] = df['clinical_sig'].apply(
                lambda x: any(kw in str(x).lower() for kw in ['conflict', 'conflicting', '|'])
            )

        if 'rsid' in df.columns and df['rsid'].duplicated().any():
            agg_dict = {
                'clinical_sig': lambda x: ' | '.join(x.dropna().astype(str).unique()),
                'gene': lambda x: ';'.join(x.dropna().astype(str).unique())
            }
            for col in ['review_status', 'variant_type']:
                if col in df.columns:
                    agg_dict[col] = lambda x: ' | '.join(x.dropna().astype(str).unique())
            df = df.groupby('rsid', as_index=False).agg(agg_dict)

        if all(col in df.columns for col in REQUIRED_COORD_COLUMNS):
            df = validate_chromosome_consistency(df)
            df = validate_position_ranges(df)
            df = normalize_dataframe_coordinates(df)

        print(f"  ✓ {len(df):,} variants")
        return df
    except Exception as e:
        raise DataLoadError(f"variant_summary load failed", context={'file': str(filepath), 'error': str(e)})


def load_clinvar_file(filepath, **kwargs) -> pd.DataFrame:
    """
    Auto-detect and load ClinVar file (main entry).
    Supports: VCF, VCF-TSV, variant_summary.txt
    Returns DataFrame with coord_key and rsid.
    """
    filepath = Path(filepath)
    try:
        file_type = detect_clinvar_file_type(filepath)
        print(f"\n{'='*70}\nLOADING {file_type.upper()}: {filepath.name}\n{'='*70}")

        loaders = {
            'vcf': load_clinvar_vcf,
            'vcf_tsv': load_clinvar_vcf_tsv,
            'variant_summary': load_variant_summary
        }

        loader = loaders.get(file_type)
        if loader is None:
            raise ValueError(f"Unknown file type: {file_type}")

        return loader(filepath, **kwargs)
    except Exception as e:
        raise DataLoadError(f"ClinVar load failed", context={'file': str(filepath), 'error': str(e)})
