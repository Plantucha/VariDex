#!/usr/bin/env python3
"""
varidex/pipeline/orchestrator.py - Pipeline Orchestrator v7.0.1-dev

Main 7-stage pipeline coordinator (coordination only).

Development version - not for production use.

Changes v7.0.1:
- Added PipelineOrchestrator class wrapper for test compatibility
- Maintains functional main() implementation
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List, Any, Callable

import pandas as pd


def configure_logging(log_path: Path = Path("pipeline.log")) -> logging.Logger:
    """Configure logging for pipeline."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(str(log_path), encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger(__name__)


logger: logging.Logger = configure_logging()

from varidex.pipeline.pipeline_config import (
    FallbackConfig,
    load_yaml_config,
    get_safeguard_config,
    get_config_value,
)
from varidex.pipeline.file_utils import (
    FileTypeDetectionError,
    validate_input_path,
    detect_data_file_type,
    check_clinvar_freshness,
)
from varidex.pipeline.cli_helpers import (
    print_pipeline_header,
    print_stage_header,
    print_mode_flags,
    print_completion_summary,
    print_usage,
)

try:
    from varidex import _imports

    config = _imports.get_config()
    models = _imports.get_models()
    loader = _imports.get_loader()
    reports = _imports.get_reports()
    PipelineState = models.PipelineState
    logger.info("✓ Centralized imports loaded")
    _IMPORT_MODE: str = "centralized"

except ImportError as e:
    logger.warning(f"Import manager unavailable: {e}")
    logger.info("✓ Falling back to direct imports")

    from varidex.core.models import PipelineState
    from varidex.io.loaders import (
        load_clinvar_file,
        load_23andme_file,
        load_vcf_file,
        detect_clinvar_file_type,
        match_variants_hybrid,
    )
    from varidex.reports.generator import create_results_dataframe, generate_all_reports

    config = FallbackConfig()

    class _LoaderWrapper:
        load_clinvar_file = staticmethod(load_clinvar_file)
        load_23andme_file = staticmethod(load_23andme_file)
        load_vcf_file = staticmethod(load_vcf_file)
        detect_clinvar_file_type = staticmethod(detect_clinvar_file_type)
        match_variants_hybrid = staticmethod(match_variants_hybrid)

    class _ReportsWrapper:
        create_results_dataframe = staticmethod(create_results_dataframe)
        generate_all_reports = staticmethod(generate_all_reports)

    loader = _LoaderWrapper()
    reports = _ReportsWrapper()
    _IMPORT_MODE = "fallback"

from varidex.pipeline.stages import (
    execute_stage2_load_clinvar,
    execute_stage3_load_user_data,
    execute_stage4_hybrid_matching,
    execute_stage5_acmg_classification,
    execute_stage6_create_results,
    execute_stage7_generate_reports,
)


class PipelineOrchestrator:
    """
    Object-oriented wrapper for the 7-stage ClinVar variant classification pipeline.

    This class provides a test-compatible interface while maintaining the existing
    functional implementation. For production use, call main() directly.

    Development version - not production tested.
    """

    def __init__(self, config: Any) -> None:
        """
        Initialize pipeline orchestrator.

        Args:
            config: PipelineConfig object with pipeline settings
        """
        from varidex.core.config import PipelineConfig
        from varidex.exceptions import ValidationError

        if config is None:
            raise ValidationError("Configuration cannot be None")

        if not isinstance(config, PipelineConfig):
            raise ValidationError(
                f"Expected PipelineConfig, got {type(config).__name__}"
            )

        self.config = config
        self._completed_stages: set = set()
        self._progress_callback: Optional[Callable[[str, float], None]] = None

        # Create output directory if it doesn't exist
        output_path = Path(self.config.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

    def run(self, stages: Optional[List[str]] = None) -> bool:
        """
        Execute the pipeline.

        Args:
            stages: Optional list of specific stages to run

        Returns:
            True if successful, False otherwise
        """
        try:
            return self._execute_stages(stages)
        except Exception as e:
            from varidex.exceptions import PipelineError

            logger.error(f"Pipeline execution failed: {e}")
            raise PipelineError(str(e))

    def _execute_stages(self, stages: Optional[List[str]] = None) -> bool:
        """
        Internal method to execute pipeline stages.

        This is a wrapper around the functional main() implementation.
        """
        # For now, delegate to the functional main() implementation
        # In a full implementation, this would execute specific stages

        # Convert config to parameters for main()
        clinvar_path = self.config.clinvar_file or "clinvar.vcf"
        user_data_path = self.config.input_vcf or self.config.input_file or "input.vcf"
        output_dir = Path(self.config.output_dir)

        # Call the functional implementation
        result = main(
            clinvar_path=clinvar_path,
            user_data_path=user_data_path,
            force=False,
            interactive=False,
            user_format=None,
            yaml_config_path=None,
            log_path=Path("pipeline.log"),
            output_dir=output_dir,
        )

        return result

    def set_progress_callback(self, callback: Callable[[str, float], None]) -> None:
        """
        Set a callback function for progress updates.

        Args:
            callback: Function that takes (stage_name: str, percent: float)
        """
        self._progress_callback = callback

    def cleanup(self) -> None:
        """Clean up resources after pipeline execution."""
        # Placeholder for resource cleanup
        pass

    def __enter__(self) -> "PipelineOrchestrator":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit with cleanup."""
        self.cleanup()


def main(
    clinvar_path: str,
    user_data_path: str,
    force: bool = False,
    interactive: bool = True,
    user_format: Optional[str] = None,
    yaml_config_path: Optional[Path] = None,
    log_path: Path = Path("pipeline.log"),
    output_dir: Path = Path("results"),
) -> bool:
    """Execute 7-stage ClinVar variant classification pipeline."""
    print_pipeline_header()
    print(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    yaml_cfg: Dict[str, Any] = load_yaml_config(
        yaml_config_path or Path(".varidex.yaml")
    )
    safeguard_config: Dict[str, Any] = get_safeguard_config(yaml_cfg)
    print_mode_flags(safeguard_config, force, interactive)

    state: PipelineState = PipelineState()

    try:
        # STAGE 1: FILE ANALYSIS
        print_stage_header(1, 7, "📋 FILE ANALYSIS")

        clinvar_file: Path = validate_input_path(Path(clinvar_path), "ClinVar")
        user_file: Path = validate_input_path(Path(user_data_path), "User data")

        if not check_clinvar_freshness(
            clinvar_file,
            max_age_days=safeguard_config["clinvar_max_age_days"],
            force=force,
            interactive=interactive,
        ):
            logger.info("User declined to continue")
            return False

        clinvar_type: str = loader.detect_clinvar_file_type(clinvar_file)
        user_type: str = user_format or detect_data_file_type(
            user_file, strict=not force
        )
        match_mode: str = get_config_value(config, "MATCH_MODE", "hybrid")

        print(f"  ClinVar format: {clinvar_type}")
        print(f"  User data format: {user_type}")
        print(f"  Matching mode: {match_mode}")
        state.file_types = f"{clinvar_type}/{user_type}"

        # STAGE 2: LOAD CLINVAR
        print_stage_header(2, 7, "📥 LOADING CLINVAR DATABASE")

        checkpoint_dir: Path = Path(
            get_config_value(config, "CHECKPOINT_DIR", Path(".varidex_cache"))
        )

        clinvar_df: pd.DataFrame = execute_stage2_load_clinvar(
            clinvar_file, checkpoint_dir, loader, safeguard_config, _IMPORT_MODE
        )

        state.variants_loaded = len(clinvar_df)
        logger.info(f"✓ Loaded {state.variants_loaded:,} ClinVar variants")
        print(f"  ✓ Loaded: {state.variants_loaded:,} variants")

        # STAGE 3: LOAD USER DATA
        print_stage_header(3, 7, "📥 LOADING USER GENOMIC DATA")

        user_df: pd.DataFrame = execute_stage3_load_user_data(
            user_file, user_type, loader
        )

        state.user_variants = len(user_df)
        logger.info(f"✓ Loaded {state.user_variants:,} user variants")
        print(f"  ✓ Loaded: {state.user_variants:,} variants")

        # STAGE 4: HYBRID MATCHING
        print_stage_header(4, 7, "🔗 MATCHING VARIANTS")

        matched_df: pd.DataFrame = execute_stage4_hybrid_matching(
            clinvar_df,
            user_df,
            clinvar_type,
            user_type,
            loader,
            safeguard_config,
            _IMPORT_MODE,
        )

        state.matches = len(matched_df)
        if state.matches == 0:
            raise ValueError(
                f"No matches between ClinVar ({clinvar_type}) and user data ({user_type}).\n"
                f"Check genome builds (GRCh37/38) or try: --format vcf|23andme|tsv"
            )

        match_rate: float = (
            (state.matches / state.user_variants * 100)
            if state.user_variants > 0
            else 0.0
        )
        logger.info(f"✓ Matched {state.matches:,} variants ({match_rate:.1f}%)")
        print(f"  ✓ Matched: {state.matches:,} ({match_rate:.1f}%)")

        # STAGE 5: ACMG CLASSIFICATION
        print_stage_header(5, 7, "🧬 ACMG CLASSIFICATION")

        classified_variants: List[Dict[str, Any]]
        classification_stats: Dict[str, int]

        classified_variants, classification_stats = execute_stage5_acmg_classification(
            matched_df, safeguard_config, clinvar_type, user_type, _IMPORT_MODE
        )

        if not classified_variants:
            raise ValueError("Classification failed - check logs")

        logger.info(f"✓ Classified {len(classified_variants):,} variants")
        print(f"  ✓ Classified: {len(classified_variants):,} variants")
        print(f"    • Pathogenic: {classification_stats.get('pathogenic', 0):,}")
        print(
            f"    • Likely Pathogenic: {classification_stats.get('likely_pathogenic', 0):,}"
        )
        print(f"    • VUS: {classification_stats.get('vus', 0):,}")
        print(f"    • Likely Benign: {classification_stats.get('likely_benign', 0):,}")
        print(f"    • Benign: {classification_stats.get('benign', 0):,}")

        if classification_stats.get("conflicts", 0) > 0:
            print(f"    ⚠️  Conflicts: {classification_stats['conflicts']:,}")

        # STAGE 6: CREATE RESULTS
        print_stage_header(6, 7, "📊 CREATING RESULTS")

        results_df: pd.DataFrame = execute_stage6_create_results(
            classified_variants, reports
        )

        logger.info(f"✓ Results DataFrame: {len(results_df):,} rows")
        print(f"  ✓ DataFrame: {len(results_df):,} variants")

        # STAGE 7: GENERATE REPORTS
        print_stage_header(7, 7, "📄 GENERATING REPORTS")

        output_dir.mkdir(exist_ok=True, parents=True)

        report_files: Dict[str, Path] = execute_stage7_generate_reports(
            results_df, classification_stats, output_dir, reports
        )

        print()
        print(f"  ✓ Reports saved to: {output_dir.absolute()}/")
        for report_type, file_path in report_files.items():
            size_kb: float = file_path.stat().st_size / 1024
            print(f"    • {report_type.upper()}: {file_path.name} ({size_kb:.1f} KB)")

        # COMPLETION
        print_completion_summary(state, match_rate, classification_stats, report_files)
        logger.info("Pipeline completed successfully")
        return True

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        print(f"\n❌ ERROR: File not found\n   {e}")
        return False

    except FileTypeDetectionError as e:
        logger.error(f"Detection failed: {e}")
        print(f"\n❌ ERROR: Cannot determine file format\n   {e}")
        return False

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        print(f"\n❌ ERROR: Validation failed\n   {e}")
        return False

    except ImportError as e:
        logger.error(f"Import error: {e}")
        print(f"\n❌ ERROR: Missing dependency\n   {e}")
        print("   Install: pip install -r requirements.txt")
        return False

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        print(f"\n❌ UNEXPECTED ERROR: {e}\n   Check {log_path}")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="ClinVar-WGS ACMG Pipeline v7.0.1-dev", add_help=False
    )
    parser.add_argument("clinvar_file", nargs="?")
    parser.add_argument("user_data", nargs="?")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--non-interactive", action="store_true")
    parser.add_argument("--format", choices=["vcf", "23andme", "tsv"])
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    parser.add_argument("--log-file", type=Path, default=Path("pipeline.log"))
    parser.add_argument("--help", action="store_true")

    args = parser.parse_args()

    if args.help or not args.clinvar_file or not args.user_data:
        print_usage()
        sys.exit(0 if args.help else 1)

    logger = configure_logging(args.log_file)

    success: bool = main(
        args.clinvar_file,
        args.user_data,
        force=args.force,
        interactive=not args.non_interactive,
        user_format=args.format,
        yaml_config_path=args.config,
        log_path=args.log_file,
        output_dir=args.output_dir,
    )

    sys.exit(0 if success else 1)
