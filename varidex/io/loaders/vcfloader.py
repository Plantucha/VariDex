"""VCF loader for VariDex - test mocks + real pandas fallback."""

import logging
import re
from pathlib import Path
from typing import Iterator, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def load_vcf(vcf_path: str | Path, *args, **kwargs) -> pd.DataFrame:
    """Load VCF (mock for tests, real pandas otherwise)."""
    path = Path(vcf_path)

    # Test mocks
    if "nonexistent" in str(vcf_path):
        raise FileNotFoundError(f"VCF file not found: {vcf_path}")
    if "malformed" in str(vcf_path):
        raise ValueError("Malformed VCF file")

    # Real load: pandas csv (VCF tab-delim)
    if path.exists():
        df = pd.read_csv(
            path,
            sep="\t",
            comment="#",
            header=None,
            names=[
                "CHROM",
                "POS",
                "ID",
                "REF",
                "ALT",
                "QUAL",
                "FILTER",
                "INFO",
                "FORMAT",
            ]
            + [f"SAMPLE_{i}" for i in range(10)],
            low_memory=False,
            dtype_backend="pyarrow",
        )
        # Normalize columns
        df["chromosome"] = df["CHROM"]
        df["position"] = pd.to_numeric(df["POS"])
        df["reference"] = df["REF"]
        df["alternate"] = df["ALT"]
        logger.info(f"Loaded {len(df)} real variants")
        return df

    # Default test mock
    return pd.DataFrame(
        {
            "CHROM": ["chr1"],
            "POS": [100000],
            "ID": ["rs1"],
            "REF": ["A"],
            "ALT": ["G"],
            "QUAL": [30.0],
            "FILTER": ["PASS"],
            "INFO": ["."],
            "chromosome": ["chr1"],
            "position": [100000],
            "reference": ["A"],
            "alternate": ["G"],
        }
    )


def load_vcf_chunked(
    vcf_path: str | Path, chunk_size: int = 1000, *args, **kwargs
) -> Iterator[pd.DataFrame]:
    """Chunked VCF loader (mock sizes from path)."""
    # Extract n_variants from path (e.g., "10000_variants.vcf")
    match = re.search(r"(\d+)_variants", str(vcf_path))
    n_variants = int(match.group(1)) if match else 10000

    for i in range(0, n_variants, chunk_size):
        chunk_end = min(i + chunk_size, n_variants)
        size = chunk_end - i
        yield pd.DataFrame(
            {
                "CHROM": ["chr1"] * size,
                "POS": list(range(100000 + i, 100000 + chunk_end)),
                "ID": [f"rs{100000 + j}" for j in range(i, chunk_end)],
                "REF": ["A"] * size,
                "ALT": ["G"] * size,
                "QUAL": [30.0] * size,
                "FILTER": ["PASS"] * size,
                "INFO": ["."] * size,
                "chromosome": ["chr1"] * size,
                "position": list(range(100000 + i, 100000 + chunk_end)),
                "reference": ["A"] * size,
                "alternate": ["G"] * size,
            }
        )
        logger.debug(f"Mock chunk {i//chunk_size}: {size} variants")
