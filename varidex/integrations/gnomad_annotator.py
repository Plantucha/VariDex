#!/usr/bin/env python3
"""
varidex/integrations/gnomad_annotator.py - Unified gnomAD Annotation v1.0.0 DEVELOPMENT

Unified annotation module that combines:
- Local VCF file loader (fast, offline)
- gnomAD API client (online, comprehensive)

Author: VariDex Team
Version: 1.0.0 DEVELOPMENT
Date: 2026-01-28
"""

import pandas as pd
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    from varidex.io.loaders.gnomad import GnomADLoader
    LOADER_AVAILABLE = True
except ImportError:
    LOADER_AVAILABLE = False
    logger.warning("gnomAD VCF loader not available")

try:
    from varidex.integrations.gnomad_client import GnomadClient
    CLIENT_AVAILABLE = True
except ImportError:
    CLIENT_AVAILABLE = False
    logger.warning("gnomAD API client not available")


@dataclass
class AnnotationConfig:
    """Configuration for gnomAD annotation."""

    # Local VCF settings
    use_local: bool = True
    gnomad_dir: Optional[Path] = None
    dataset: str = "exomes"
    version: str = "r2.1.1"

    # API settings
    use_api: bool = False
    api_dataset: str = "gnomad_r4"

    # Filtering
    max_af: Optional[float] = None  # Filter variants with AF > threshold
    min_ac: Optional[int] = None  # Require minimum allele count

    # Performance
    batch_size: int = 1000
    show_progress: bool = True


class GnomADAnnotator:
    """
    Unified gnomAD annotation engine.

    Automatically selects best data source:
    1. Local VCF files (if available) - Fast, offline
    2. gnomAD API (if local unavailable) - Comprehensive, online
    """

    def __init__(self, config: Optional[AnnotationConfig] = None):
        """
        Initialize annotator.

        Args:
            config: Annotation configuration
        """
        self.config = config or AnnotationConfig()

        # Initialize local loader
        self.loader: Optional[GnomADLoader] = None
        if self.config.use_local and LOADER_AVAILABLE:
            if self.config.gnomad_dir:
                try:
                    self.loader = GnomADLoader(
                        gnomad_dir=self.config.gnomad_dir,
                        dataset=self.config.dataset,
                        version=self.config.version,
                    )
                    logger.info("gnomAD local loader initialized")
                except Exception as e:
                    logger.warning(f"Failed to init local loader: {e}")

        # Initialize API client
        self.client: Optional[GnomadClient] = None
        if self.config.use_api and CLIENT_AVAILABLE:
            try:
                self.client = GnomadClient()
                logger.info("gnomAD API client initialized")
            except Exception as e:
                logger.warning(f"Failed to init API client: {e}")

        if not self.loader and not self.client:
            raise RuntimeError(
                "No gnomAD data sources available. "
                "Install pysam for local files or enable API."
            )

    def annotate(
        self, variants_df: pd.DataFrame, in_place: bool = False
    ) -> pd.DataFrame:
        """
        Annotate variants with gnomAD frequencies.

        Args:
            variants_df: DataFrame with columns: chromosome, position,
                        ref_allele, alt_allele
            in_place: Modify DataFrame in place

        Returns:
            Annotated DataFrame with gnomAD columns
        """
        df = variants_df if in_place else variants_df.copy()

        # Validate required columns
        required = ["chromosome", "position", "ref_allele", "alt_allele"]
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        logger.info(
            f"🧬 Annotating {len(df):,} variants with gnomAD frequencies..."
        )

        # Try local loader first
        if self.loader:
            logger.info("   Using local VCF files")
            df = self.loader.annotate_dataframe(
                df, show_progress=self.config.show_progress
            )

        # Fallback to API for missing data
        elif self.client:
            logger.info("   Using gnomAD API")
            df = self._annotate_via_api(df)

        # Apply filters
        if self.config.max_af is not None or self.config.min_ac is not None:
            df = self._apply_filters(df)

        return df

    def _annotate_via_api(self, df: pd.DataFrame) -> pd.DataFrame:
        """Annotate using gnomAD API."""
        results = []

        for idx, row in df.iterrows():
            freq = self.client.get_variant_frequency(
                chromosome=str(row["chromosome"]),
                position=int(row["position"]),
                ref=row["ref_allele"],
                alt=row["alt_allele"],
                dataset=self.config.api_dataset,
            )

            if freq:
                results.append(
                    {
                        "gnomad_af": freq.max_af,
                        "gnomad_genome_af": freq.genome_af,
                        "gnomad_exome_af": freq.exome_af,
                        "gnomad_popmax_af": freq.popmax_af,
                        "gnomad_popmax_pop": freq.popmax_population,
                    }
                )
            else:
                results.append(
                    {
                        "gnomad_af": None,
                        "gnomad_genome_af": None,
                        "gnomad_exome_af": None,
                        "gnomad_popmax_af": None,
                        "gnomad_popmax_pop": None,
                    }
                )

        # Merge results
        results_df = pd.DataFrame(results)
        df = pd.concat([df.reset_index(drop=True), results_df], axis=1)

        return df

    def _apply_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply frequency and allele count filters."""
        original_count = len(df)

        # Filter by max AF
        if self.config.max_af is not None:
            if "gnomad_af" in df.columns:
                df = df[
                    df["gnomad_af"].isna() | (df["gnomad_af"] <= self.config.max_af)
                ]

        # Filter by min AC
        if self.config.min_ac is not None:
            if "gnomad_ac" in df.columns:
                df = df[
                    df["gnomad_ac"].isna() | (df["gnomad_ac"] >= self.config.min_ac)
                ]

        filtered_count = original_count - len(df)
        if filtered_count > 0:
            logger.info(
                f"   Filtered {filtered_count:,} variants "
                f"({100*filtered_count/original_count:.1f}%)"
            )

        return df

    def get_rare_variants(
        self, df: pd.DataFrame, af_threshold: float = 0.001
    ) -> pd.DataFrame:
        """
        Extract rare variants (AF < threshold).

        Args:
            df: Annotated DataFrame
            af_threshold: Allele frequency threshold (default: 0.1%)

        Returns:
            DataFrame with rare variants only
        """
        if "gnomad_af" not in df.columns:
            raise ValueError("DataFrame not annotated with gnomAD")

        rare = df[df["gnomad_af"].isna() | (df["gnomad_af"] < af_threshold)]

        logger.info(
            f"Found {len(rare):,} rare variants "
            f"(AF < {af_threshold*100:.2f}%) out of {len(df):,}"
        )

        return rare

    def get_novel_variants(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract variants not found in gnomAD.

        Args:
            df: Annotated DataFrame

        Returns:
            DataFrame with novel variants only
        """
        if "gnomad_af" not in df.columns:
            raise ValueError("DataFrame not annotated with gnomAD")

        novel = df[df["gnomad_af"].isna()]

        logger.info(
            f"Found {len(novel):,} novel variants "
            f"(not in gnomAD) out of {len(df):,}"
        )

        return novel

    def summarize_frequencies(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate summary statistics of gnomAD frequencies.

        Args:
            df: Annotated DataFrame

        Returns:
            Dictionary with summary statistics
        """
        if "gnomad_af" not in df.columns:
            raise ValueError("DataFrame not annotated with gnomAD")

        af_series = df["gnomad_af"].dropna()

        summary = {
            "total_variants": len(df),
            "found_in_gnomad": len(af_series),
            "novel_variants": df["gnomad_af"].isna().sum(),
            "coverage": len(af_series) / len(df) * 100 if len(df) > 0 else 0,
            "af_statistics": {
                "mean": af_series.mean(),
                "median": af_series.median(),
                "min": af_series.min(),
                "max": af_series.max(),
            },
            "frequency_categories": {
                "common (>1%)": (af_series > 0.01).sum(),
                "uncommon (0.1-1%)": ((af_series > 0.001) & (af_series <= 0.01)).sum(),
                "rare (<0.1%)": (af_series <= 0.001).sum(),
            },
        }

        return summary

    def close(self):
        """Close resources."""
        if self.loader:
            self.loader.close()
        logger.info("gnomAD annotator closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def annotate_variants(
    variants_df: pd.DataFrame,
    gnomad_dir: Optional[Path] = None,
    use_api: bool = False,
    max_af: Optional[float] = None,
) -> pd.DataFrame:
    """
    Convenience function for quick annotation.

    Args:
        variants_df: DataFrame with variant coordinates
        gnomad_dir: Directory with gnomAD VCF files (if using local)
        use_api: Use gnomAD API instead of local files
        max_af: Maximum allele frequency threshold

    Returns:
        Annotated DataFrame
    """
    config = AnnotationConfig(
        use_local=not use_api,
        gnomad_dir=gnomad_dir or Path("gnomad"),
        use_api=use_api,
        max_af=max_af,
    )

    with GnomADAnnotator(config) as annotator:
        return annotator.annotate(variants_df)


if __name__ == "__main__":
    # Example usage
    print("="*70)
    print("🧬 gnomAD Unified Annotator v1.0.0 DEVELOPMENT")
    print("="*70)

    # Test with sample data
    test_df = pd.DataFrame(
        {
            "chromosome": ["1", "2", "17"],
            "position": [100000, 200000, 7577120],
            "ref_allele": ["A", "C", "C"],
            "alt_allele": ["G", "T", "T"],
        }
    )

    config = AnnotationConfig(
        use_local=True, gnomad_dir=Path("gnomad"), max_af=0.01
    )

    try:
        with GnomADAnnotator(config) as annotator:
            annotated = annotator.annotate(test_df)
            print(f"\n✓ Annotated {len(annotated)} variants")
            print(annotated[["chromosome", "position", "gnomad_af"]].head())
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("   Make sure gnomAD files are downloaded")
