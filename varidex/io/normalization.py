import pandas as pd


def normalize_alleles(df: pd.DataFrame) -> pd.DataFrame:
    """VCF normalization - trim common prefix, keep 1 base min."""
    df = df.copy()
    ref_col = "ref" if "ref" in df.columns else "reference"
    alt_col = "alt" if "alt" in df.columns else "alternate"

    def _norm(row):
        ref, alt = str(row[ref_col]), str(row[alt_col])
        # Trim common prefix but keep at least 1 char OR go empty
        min_len = min(len(ref), len(alt))
        trim = 0
        for i in range(min_len):
            if ref[i] != alt[i]:
                break
            trim = i + 1

        # Trim all common chars (can go empty)
        if trim == min_len:
            ref, alt = ref[trim:], alt[trim:]
        else:
            # Trim matching prefix
            ref, alt = ref[trim:], alt[trim:]

        return pd.Series({ref_col: ref, alt_col: alt})

    norm_df = df.apply(_norm, axis=1)
    df[ref_col] = norm_df[ref_col]
    df[alt_col] = norm_df[alt_col]
    return df


def create_coord_key(chrom: str, pos: int, ref: str, alt: str) -> str:
    """Create standardized coordinate key for variant matching."""
    return f"{chrom}:{pos}:{ref}:{alt}"


def normalize_dataframe_coordinates(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize coordinate columns in DataFrame for consistent matching."""
    if "chrom" in df.columns:
        df["chrom"] = df["chrom"].str.upper()
    if "pos" in df.columns:
        df["pos"] = pd.to_numeric(df["pos"], errors="coerce")
    return df
