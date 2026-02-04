from pathlib import Path

import pandas as pd


def write_vcf(df: pd.DataFrame, output_path: str | Path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Simple CSV for roundtrip test
    df[["CHROM", "POS", "REF", "ALT"]].to_csv(
        output_path.with_suffix(".tsv"), sep="	", index=False, header=False
    )
    print(f"Wrote {len(df)} variants")
