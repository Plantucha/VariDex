#!/usr/bin/env python3
"""
varidex/pipeline/gnomad_stage.py - gnomAD Pipeline Integration v1.0.0-dev
==========================================================================

Pipeline stage for gnomAD frequency annotation.
Integrates gnomAD data into the variant classification workflow.

Features:
- Automatic gnomAD API or local VCF annotation
- Batch processing for large datasets
- PM2/BA1/BS1 evidence code support
- Configurable thresholds
- Progress tracking
- Error handling and graceful fallback

Author: VariDex Team
Version: 1.0.0-dev
Date: 2026-01-31
"""

import logging
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    from varidex.integrations.gnomad_client import GnomadClient
    from varidex.integrations.gnomad_annotator import (
        GnomADAnnotator,
        AnnotationConfig,
    )

    GNOMAD_AVAILABLE = True
except ImportError:
    GNOMAD_AVAILABLE = False
    logger.warning(
        "gnomAD integration not available. Install with: pip install pyliftover"
    )


@dataclass
class GnomADStageConfig:
    """Configuration for gnomAD pipeline stage."""

    # Mode selection
    enabled: bool = True
    mode: str = "api"  # "api" or "local"

    # API settings
    api_url: str = "https://gnomad.broadinstitute.org/api"
    api_dataset: str = "gnomad_r4"
    api_timeout: int = 30
    api_retry: int = 3

    # Local VCF settings
    gnomad_dir: Optional[Path] = None
    gnomad_dataset: str = "exomes"
    gnomad_version: str = "r2.1.1"

    # ACMG thresholds
    pm2_threshold: float = 0.0001  # PM2: AF < 0.01%
    ba1_threshold: float = 0.05  # BA1: AF > 5%
    bs1_threshold: float = 0.01  # BS1: AF > 1%

    # Performance
    batch_size: int = 1000
    show_progress: bool = True
    enable_cache: bool = True

    # Filtering
    filter_common: bool = False  # Filter variants with AF > ba1_threshold
    require_rare: bool = False  # Require AF < pm2_threshold


class GnomADPipelineStage:
    """
    Pipeline stage for gnomAD frequency annotation.

    Integrates into the main VariDex workflow between
    Stage 3 (Matching) and Stage 5 (Classification).
    """

    def __init__(self, config: Optional[GnomADStageConfig] = None):
        """
        Initialize gnomAD pipeline stage.

        Args:
            config: Stage configuration
        """
        self.config = config or GnomADStageConfig()

        if not self.config.enabled:
            logger.info("gnomAD stage disabled in config")
            self.annotator = None
            return

        if not GNOMAD_AVAILABLE:
            logger.error(
                "gnomAD dependencies not installed. "
                "Install with: pip install pyliftover"
            )
            self.annotator = None
            return

        # Initialize annotator based on mode
        try:
            if self.config.mode == "api":
                logger.info("Initializing gnomAD API mode...")
                ann_config = AnnotationConfig(
                    use_local=False,
                    use_api=True,
                    api_dataset=self.config.api_dataset,
                    batch_size=self.config.batch_size,
                    show_progress=self.config.show_progress,
                )
            else:  # local mode
                logger.info("Initializing gnomAD local VCF mode...")
                if not self.config.gnomad_dir:
                    raise ValueError(
                        "gnomad_dir required for local mode. "
                        "Download gnomAD VCFs or use API mode."
                    )
                ann_config = AnnotationConfig(
                    use_local=True,
                    gnomad_dir=self.config.gnomad_dir,
                    dataset=self.config.gnomad_dataset,
                    version=self.config.gnomad_version,
                    use_api=False,
                    batch_size=self.config.batch_size,
                    show_progress=self.config.show_progress,
                )

            self.annotator = GnomADAnnotator(ann_config)
            logger.info(f"✓ gnomAD stage initialized ({self.config.mode} mode)")

        except Exception as e:
            logger.error(f"Failed to initialize gnomAD annotator: {e}")
            self.annotator = None

    def annotate_variants(
        self, variants_df: pd.DataFrame
    ) -> tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Annotate variants with gnomAD frequencies.

        Args:
            variants_df: DataFrame with variant data
                Required columns: chromosome, position, ref_allele, alt_allele

        Returns:
            Tuple of (annotated_df, stats_dict)
        """
        if not self.config.enabled or self.annotator is None:
            logger.warning("gnomAD annotation skipped (disabled or unavailable)")
            return variants_df, {"skipped": True}

        logger.info(
            f"\n{'='*65}\n"
            f"🧬 STAGE 4: gnomAD FREQUENCY ANNOTATION\n"
            f"{'='*65}"
        )
        logger.info(f"Mode: {self.config.mode.upper()}")
        logger.info(f"Variants: {len(variants_df):,}")

        try:
            # Validate required columns
            required_cols = ["chromosome", "position"]
            missing = [col for col in required_cols if col not in variants_df.columns]

            if missing:
                logger.error(f"Missing required columns: {missing}")
                return variants_df, {"error": f"Missing columns: {missing}"}

            # Prepare columns for gnomAD (handle different naming)
            df = variants_df.copy()

            # Map column names if needed
            if "ref_allele" not in df.columns and "ref" in df.columns:
                df["ref_allele"] = df["ref"]
            if "alt_allele" not in df.columns and "alt" in df.columns:
                df["alt_allele"] = df["alt"]

            # Fill missing alleles with empty strings (for coordinate-only variants)
            if "ref_allele" not in df.columns:
                df["ref_allele"] = ""
            if "alt_allele" not in df.columns:
                df["alt_allele"] = ""

            # Annotate with gnomAD
            df = self.annotator.annotate(df, in_place=False)

            # Calculate statistics
            stats = self._calculate_stats(df)

            # Apply filters if configured
            if self.config.filter_common or self.config.require_rare:
                df, filter_stats = self._apply_filters(df)
                stats.update(filter_stats)

            # Add ACMG evidence flags
            df = self._add_acmg_flags(df)

            logger.info(f"\n✓ gnomAD annotation complete")
            logger.info(f"  Found in gnomAD: {stats['found_count']:,} "
                       f"({stats['coverage']:.1f}%)")
            logger.info(f"  Novel variants: {stats['novel_count']:,}")
            logger.info(f"  PM2 eligible (rare): {stats['pm2_eligible']:,}")
            logger.info(f"  BA1 eligible (common): {stats['ba1_eligible']:,}")

            return df, stats

        except Exception as e:
            logger.error(f"gnomAD annotation failed: {e}", exc_info=True)
            return variants_df, {"error": str(e)}

    def _calculate_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate annotation statistics."""
        total = len(df)
        found = df["gnomad_af"].notna().sum() if "gnomad_af" in df.columns else 0
        novel = total - found

        # Count by ACMG evidence thresholds
        if "gnomad_af" in df.columns:
            af_series = df["gnomad_af"].dropna()
            pm2_eligible = (af_series < self.config.pm2_threshold).sum()
            bs1_eligible = (
                (af_series >= self.config.bs1_threshold)
                & (af_series < self.config.ba1_threshold)
            ).sum()
            ba1_eligible = (af_series >= self.config.ba1_threshold).sum()
        else:
            pm2_eligible = 0
            bs1_eligible = 0
            ba1_eligible = 0

        return {
            "total_variants": total,
            "found_count": int(found),
            "novel_count": int(novel),
            "coverage": (found / total * 100) if total > 0 else 0,
            "pm2_eligible": int(pm2_eligible),
            "bs1_eligible": int(bs1_eligible),
            "ba1_eligible": int(ba1_eligible),
        }

    def _apply_filters(self, df: pd.DataFrame) -> tuple[pd.DataFrame, Dict[str, Any]]:
        """Apply frequency-based filters."""
        original_count = len(df)
        filtered_df = df.copy()

        if "gnomad_af" not in df.columns:
            return df, {"filtered_count": 0}

        # Filter common variants (BA1 threshold)
        if self.config.filter_common:
            filtered_df = filtered_df[
                filtered_df["gnomad_af"].isna()
                | (filtered_df["gnomad_af"] < self.config.ba1_threshold)
            ]

        # Require rare variants (PM2 threshold)
        if self.config.require_rare:
            filtered_df = filtered_df[
                filtered_df["gnomad_af"].isna()
                | (filtered_df["gnomad_af"] < self.config.pm2_threshold)
            ]

        filtered_count = original_count - len(filtered_df)

        if filtered_count > 0:
            logger.info(
                f"  Filtered: {filtered_count:,} variants "
                f"({100*filtered_count/original_count:.1f}%)"
            )

        return filtered_df, {"filtered_count": int(filtered_count)}

    def _add_acmg_flags(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add boolean flags for ACMG evidence codes."""
        if "gnomad_af" not in df.columns:
            return df

        # PM2: Absent or extremely rare (< 0.01%)
        df["gnomad_pm2_eligible"] = (
            df["gnomad_af"].isna() | (df["gnomad_af"] < self.config.pm2_threshold)
        )

        # BS1: Greater than expected for disorder (> 1%)
        df["gnomad_bs1_eligible"] = (
            df["gnomad_af"] >= self.config.bs1_threshold
        ) & (df["gnomad_af"] < self.config.ba1_threshold)

        # BA1: Stand-alone benign (> 5%)
        df["gnomad_ba1_eligible"] = df["gnomad_af"] >= self.config.ba1_threshold

        return df

    def close(self):
        """Clean up resources."""
        if self.annotator:
            self.annotator.close()
            logger.info("gnomAD stage closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


if __name__ == "__main__":
    # Test the stage with sample data
    print("=" * 70)
    print("🧬 gnomAD Pipeline Stage v1.0.0-dev")
    print("=" * 70)

    # Create sample data
    test_df = pd.DataFrame(
        {
            "chromosome": ["17", "13", "1"],
            "position": [43094692, 32315508, 100000],
            "ref_allele": ["G", "C", "A"],
            "alt_allele": ["A", "T", "G"],
            "rsid": ["rs80357906", "rs80357914", "rs0000001"],
        }
    )

    print(f"\nTest data: {len(test_df)} variants")
    print(test_df[["chromosome", "position", "rsid"]].to_string(index=False))

    # Test with API mode
    config = GnomADStageConfig(enabled=True, mode="api", show_progress=True)

    try:
        with GnomADPipelineStage(config) as stage:
            annotated_df, stats = stage.annotate_variants(test_df)

            print(f"\n{'='*70}")
            print("Results:")
            print(f"  Total: {stats['total_variants']}")
            print(f"  Found: {stats['found_count']} ({stats['coverage']:.1f}%)")
            print(f"  PM2 eligible: {stats['pm2_eligible']}")
            print(f"  BA1 eligible: {stats['ba1_eligible']}")

            print(f"\n{'='*70}")
            print("Sample annotations:")
            cols = ["rsid", "gnomad_af", "gnomad_pm2_eligible", "gnomad_ba1_eligible"]
            available_cols = [c for c in cols if c in annotated_df.columns]
            print(annotated_df[available_cols].head().to_string(index=False))

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        print("  Make sure gnomAD dependencies are installed")
        print("  Install with: pip install pyliftover")
