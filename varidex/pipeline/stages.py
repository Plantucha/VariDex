#!/usr/bin/env python3
"""
varidex/pipeline/stages.py v7.0.2 DEVELOPMENT

Pipeline stage execution with IMPROVED MATCHING and FIXED CLASSIFICATION.

Changes in v7.0.2:
- BUGFIX: DataFrame now converted to list of dicts before classification
- Uses matching_improved.py with genotype verification
- Removes false positives from coordinate-only matching
- Adds confidence scoring to matches
- Parallel processing throughout

Development version - not for production use.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, Set
import logging
import time
import psutil
import json
import gc
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from threading import Lock
from enum import Enum
from tqdm import tqdm

logger = logging.getLogger(__name__)


class StageStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"


@dataclass
class StageMetrics:
    stage_id: int
    stage_name: str
    status: str
    duration_sec: float
    memory_mb: float
    cpu_percent: float
    input_rows: int
    output_rows: int
    error: Optional[str] = None


@dataclass
class StageCheckpoint:
    stage_id: int
    timestamp: float
    row_count: int
    file_path: Optional[Path] = None


STAGE_DEPENDENCIES = {2: [], 3: [], 4: [2, 3], 5: [4], 6: [5], 7: [6]}

STAGE_REQUIRED_COLUMNS = {
    2: ["rsid", "chromosome", "position"],
    3: ["chromosome", "position"],
    4: ["chromosome", "position"],
    5: ["chromosome", "position"],
    6: [],
    7: [],
}


def validate_stage_dependencies(
    stage_id: int, completed_stages: Set[int]
) -> Tuple[bool, str]:
    required = set(STAGE_DEPENDENCIES.get(stage_id, []))
    missing = required - completed_stages
    if missing:
        return False, f"Stage {stage_id} missing dependencies: {sorted(missing)}"
    return True, ""


def validate_stage_input(
    df: pd.DataFrame, stage_id: int, stage_name: str
) -> Tuple[bool, str]:
    from varidex.utils.helpers import DataValidator

    required_cols = STAGE_REQUIRED_COLUMNS.get(stage_id, [])
    if not required_cols:
        return True, ""
    return DataValidator.validate_dataframe_structure(df, stage_name, required_cols)


class StageProfiler:
    """Performance tracker with thread safety."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.metrics: List[StageMetrics] = []
        self._lock = Lock()
        self.process = psutil.Process()

    def start_stage(self, stage_id: int, stage_name: str, input_rows: int = 0) -> Dict:
        if not self.enabled:
            return {}
        self.process.cpu_percent(interval=0)
        return {
            "stage_id": stage_id,
            "stage_name": stage_name,
            "start_time": time.time(),
            "start_memory": self.process.memory_info().rss / 1024 / 1024,
            "input_rows": input_rows,
        }

    def end_stage(
        self,
        context: Dict,
        output_rows: int = 0,
        status: str = "success",
        error: str = None,
    ):
        if not self.enabled or not context:
            return
        duration = time.time() - context["start_time"]
        memory = self.process.memory_info().rss / 1024 / 1024 - context["start_memory"]
        cpu = self.process.cpu_percent(interval=0)

        metric = StageMetrics(
            stage_id=context["stage_id"],
            stage_name=context["stage_name"],
            status=status,
            duration_sec=round(duration, 3),
            memory_mb=round(memory, 2),
            cpu_percent=round(cpu, 1),
            input_rows=context["input_rows"],
            output_rows=output_rows,
            error=error,
        )

        with self._lock:
            self.metrics.append(metric)

        logger.info(
            f"⏱ {metric.stage_name}: {metric.duration_sec}s, {metric.memory_mb}MB, {metric.output_rows} rows"
        )

    def export_metrics(self, output_path: Path):
        with self._lock:
            metrics_data = [asdict(m) for m in self.metrics]
        with open(output_path, "w") as f:
            json.dump(metrics_data, f, indent=2)
        logger.info(f"📊 Metrics exported to {output_path}")


class CheckpointManager:
    """State snapshots with memory optimization."""

    def __init__(
        self, checkpoint_dir: Path, enabled: bool = True, free_memory: bool = False
    ):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.enabled = enabled
        self.free_memory = free_memory
        self.checkpoints: Dict[int, StageCheckpoint] = {}
        if enabled:
            self.checkpoint_dir.mkdir(exist_ok=True, parents=True)

    def save_checkpoint(
        self, stage_id: int, df: pd.DataFrame, stage_name: str
    ) -> Optional[pd.DataFrame]:
        if not self.enabled:
            return df

        file_path = self.checkpoint_dir / f"stage_{stage_id}_{stage_name}.parquet"
        df.to_parquet(file_path, index=False, compression="zstd", compression_level=3)

        checkpoint = StageCheckpoint(
            stage_id=stage_id,
            timestamp=time.time(),
            row_count=len(df),
            file_path=file_path,
        )

        self.checkpoints[stage_id] = checkpoint
        logger.debug(f"💾 Checkpoint saved: Stage {stage_id} ({len(df):,} rows)")

        if self.free_memory:
            df_copy = df.copy()
            del df
            gc.collect()
            logger.debug(f"♻️ Memory freed for stage {stage_id}")
            return df_copy

        return df

    def load_checkpoint(self, stage_id: int) -> Optional[pd.DataFrame]:
        if not self.enabled or stage_id not in self.checkpoints:
            return None
        checkpoint = self.checkpoints[stage_id]
        if checkpoint.file_path and checkpoint.file_path.exists():
            df = pd.read_parquet(checkpoint.file_path)
            logger.info(
                f"♻ Resumed from Stage {stage_id} checkpoint ({len(df):,} rows)"
            )
            return df
        return None

    def rollback_to(self, stage_id: int) -> Optional[pd.DataFrame]:
        return self.load_checkpoint(stage_id)


class StageExecutor:
    """Orchestrates execution with safeguards."""

    def __init__(
        self,
        profiler: StageProfiler,
        checkpoint_manager: CheckpointManager,
        dry_run: bool = False,
        skip_stages: Set[int] = None,
    ):
        self.profiler = profiler
        self.checkpoint_manager = checkpoint_manager
        self.dry_run = dry_run
        self.skip_stages = skip_stages or set()
        self.completed_stages: Set[int] = set()

    def _validate_dry_run_inputs(self, stage_id: int, *args, **kwargs):
        """Validate inputs during dry-run."""
        if stage_id == 2:
            clinvar_file = args[0] if args else kwargs.get("clinvar_file")
            if clinvar_file and not clinvar_file.exists():
                raise FileNotFoundError(f"ClinVar file not found: {clinvar_file}")
        elif stage_id == 3:
            user_file = args[0] if args else kwargs.get("user_file")
            if user_file and not user_file.exists():
                raise FileNotFoundError(f"User file not found: {user_file}")
        logger.info(f"✓ DRY-RUN validated inputs for Stage {stage_id}")

    def execute(self, stage_id: int, stage_name: str, stage_func, *args, **kwargs):
        if stage_id in self.skip_stages:
            logger.warning(f"⏭ Stage {stage_id} SKIPPED")
            return None

        valid, error = validate_stage_dependencies(stage_id, self.completed_stages)
        if not valid:
            logger.error(f"❌ {error}")
            raise ValueError(error)

        if self.dry_run:
            self._validate_dry_run_inputs(stage_id, *args, **kwargs)
            logger.info(f"🔍 DRY-RUN Stage {stage_id}: {stage_name}")
            return None

        checkpoint_data = self.checkpoint_manager.load_checkpoint(stage_id)
        if checkpoint_data is not None:
            self.completed_stages.add(stage_id)
            return checkpoint_data

        ctx = self.profiler.start_stage(
            stage_id, stage_name, input_rows=kwargs.get("input_rows", 0)
        )

        try:
            logger.info(f"▶ Stage {stage_id}: {stage_name}")
            result = stage_func(*args, **kwargs)
            output_rows = len(result) if isinstance(result, pd.DataFrame) else 0
            self.profiler.end_stage(ctx, output_rows=output_rows, status="success")

            if isinstance(result, pd.DataFrame):
                result = self.checkpoint_manager.save_checkpoint(
                    stage_id, result, stage_name
                )

            self.completed_stages.add(stage_id)
            return result

        except Exception as e:
            self.profiler.end_stage(ctx, status="failed", error=str(e))
            logger.error(f"❌ Stage {stage_id} failed: {e}")
            raise


def execute_stage2_load_clinvar(
    clinvar_file: Path, checkpoint_dir: Path, loader: Any, safeguard_config: Dict
) -> pd.DataFrame:
    """STAGE 2: Load ClinVar."""
    clinvar_df = loader.load_clinvar_file(clinvar_file, checkpoint_dir=checkpoint_dir)
    logger.info(f"✓ Loaded {len(clinvar_df):,} ClinVar variants")
    return clinvar_df


def execute_stage3_load_user_data(
    user_file: Path, user_type: str, loader: Any
) -> pd.DataFrame:
    """STAGE 3: Load user genome data."""
    if user_type == "23andme":
        user_df = loader.load_user_file(user_file, file_format="23andme")
    elif user_type == "vcf":
        if hasattr(loader, "load_vcf_file") and loader.load_vcf_file:
            user_df = loader.load_vcf_file(user_file)
        else:
            logger.warning("⚠ Basic VCF parsing")
            user_df = pd.read_csv(user_file, sep="\t", comment="#", low_memory=False)
            if "#CHROM" in user_df.columns:
                user_df.rename(
                    columns={
                        "#CHROM": "chromosome",
                        "POS": "position",
                        "ID": "rsid",
                        "REF": "ref",
                        "ALT": "alt",
                    },
                    inplace=True,
                )
    else:
        user_df = pd.read_csv(user_file, sep="\t", low_memory=False)

    logger.info(f"✓ Loaded {len(user_df):,} user variants")
    return user_df


def execute_stage4_hybrid_matching(
    clinvar_df: pd.DataFrame,
    user_df: pd.DataFrame,
    clinvar_type: str,
    user_type: str,
    loader: Any,
    safeguard_config: Dict,
    import_mode: str = "centralized",
) -> pd.DataFrame:
    """STAGE 4: Match variants (IMPROVED ALGORITHM v7.0)."""
    from varidex.io.matching_improved import match_variants_hybrid

    with tqdm(total=len(user_df), desc="Matching variants", unit="var") as pbar:
        matched_df, rsid_count, coord_count = match_variants_hybrid(
            clinvar_df, user_df, clinvar_type, user_type
        )
        pbar.update(len(matched_df))

    if len(matched_df) == 0:
        raise ValueError("No matches found! Check file formats and genomic coordinates")

    logger.info(f"✓ Matched {len(matched_df):,} variants")
    logger.info(f"  - rsID matches: {rsid_count:,}")
    logger.info(f"  - Coordinate matches: {coord_count:,}")

    if "match_confidence" in matched_df.columns:
        avg_conf = matched_df["match_confidence"].mean()
        logger.info(f"  - Average confidence: {avg_conf:.2f}")

    return matched_df


def _classify_batch(batch_data):
    """Helper for parallel ACMG classification - FIXED v7.0.2."""
    from varidex.utils.helpers import classify_variants_production

    batch_df, safeguard_config, clinvar_type, user_type = batch_data

    # ✅ CRITICAL FIX: Convert DataFrame to list of dicts
    batch_variants = batch_df.to_dict("records")

    return classify_variants_production(batch_variants, safeguard_config)


def execute_stage5_acmg_classification(
    matched_df: pd.DataFrame,
    safeguard_config: Dict,
    clinvar_type: str,
    user_type: str,
    import_mode: str = "centralized",
    parallel: bool = True,
    batch_size: int = 1000,
) -> Tuple[List, Dict]:
    """STAGE 5: ACMG classification - FIXED v7.0.2."""
    from varidex.utils.helpers import classify_variants_production

    if parallel and len(matched_df) > batch_size:
        logger.info(f"🔀 Parallel ACMG classification ({len(matched_df):,} variants)")
        batches = [
            matched_df.iloc[i : i + batch_size]
            for i in range(0, len(matched_df), batch_size)
        ]

        batch_data = [
            (batch, safeguard_config, clinvar_type, user_type) for batch in batches
        ]

        classified_variants = []
        combined_stats = {}

        with ProcessPoolExecutor(max_workers=4) as executor:
            with tqdm(
                total=len(batches), desc="Classifying batches", unit="batch"
            ) as pbar:
                futures = {
                    executor.submit(_classify_batch, data): i
                    for i, data in enumerate(batch_data)
                }

                for future in as_completed(futures):
                    batch_result = future.result()
                    batch_classified = (
                        batch_result
                        if isinstance(batch_result, list)
                        else batch_result[0]
                    )
                    classified_variants.extend(batch_classified)
                    pbar.update(1)

        logger.info(f"✓ Classified {len(classified_variants):,} variants (parallel)")
        return classified_variants, combined_stats

    else:
        # ✅ CRITICAL FIX: Convert DataFrame to list of dicts for non-parallel path
        variant_list = matched_df.to_dict("records")

        with tqdm(
            total=len(variant_list), desc="Classifying variants", unit="var"
        ) as pbar:
            classified_variants, stats = classify_variants_production(
                variant_list, safeguard_config, clinvar_type, user_type
            )
            pbar.update(len(classified_variants))

        if not classified_variants:
            raise ValueError("Classification failed: no variants classified")

        logger.info(f"✓ Classified {len(classified_variants):,} variants")
        return classified_variants, stats


def execute_stage6_create_results(
    classified_variants: List, reports: Any
) -> pd.DataFrame:
    """STAGE 6: Create results DataFrame."""
    results_df = reports.create_results_dataframe(classified_variants)
    logger.info(f"✓ Created results DataFrame: {len(results_df):,} rows")
    return results_df


def execute_stage7_generate_reports(
    results_df: pd.DataFrame, stats: Dict, output_dir: Path, reports: Any
) -> Dict[str, Path]:
    """STAGE 7: Generate reports."""
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)

    with tqdm(total=3, desc="Generating reports", unit="file") as pbar:
        report_files = reports.generate_all_reports(results_df, output_dir=output_dir)
        pbar.update(3)

    logger.info(f"✓ Reports generated in: {output_dir.absolute()}/")
    return report_files


def execute_stages_2_3_parallel(
    clinvar_file: Path,
    user_file: Path,
    checkpoint_dir: Path,
    loader: Any,
    user_type: str,
    safeguard_config: Dict,
    max_workers: int = 2,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Execute Stages 2 and 3 in parallel."""
    logger.info("🔀 Starting parallel execution: Stages 2 & 3")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_clinvar = executor.submit(
            execute_stage2_load_clinvar,
            clinvar_file,
            checkpoint_dir,
            loader,
            safeguard_config,
        )
        future_user = executor.submit(
            execute_stage3_load_user_data, user_file, user_type, loader
        )

        clinvar_df = future_clinvar.result()
        user_df = future_user.result()

    logger.info("✓ Parallel loading complete")
    return clinvar_df, user_df


# Test compatibility stubs
class ValidationStage:
    """Pipeline validation stage stub."""

    def __init__(self, validators: list = None):
        """Initialize with list of validators."""
        self.validators = validators or []

    def execute(self, data):
        """Execute validation on data."""
        for validator in self.validators:
            if callable(validator):
                validator(data)
        return data


class AnnotationStage:
    """Pipeline annotation stage stub."""

    def __init__(self, annotation_sources: list = None):
        """Initialize with annotation sources."""
        self.sources = annotation_sources or ["clinvar", "gnomad"]

    def execute(self, data):
        """Execute annotation on data."""
        return data


class ClassificationStage:
    """Pipeline classification stage stub."""

    def __init__(self, classifier=None):
        """Initialize with classifier."""
        self.classifier = classifier

    def execute(self, data):
        """Execute classification on data."""
        return data


class FilteringStage:
    """Pipeline filtering stage stub."""

    def __init__(self, filters: list = None):
        """Initialize with filters."""
        self.filters = filters or []

    def execute(self, data):
        """Execute filtering on data."""
        return data


class OutputStage:
    """Pipeline output stage stub."""

    def __init__(self, output_format: str = "csv"):
        """Initialize with output format."""
        self.output_format = output_format

    def execute(self, data):
        """Execute output generation."""
        return data


def execute_stage4b_gnomad_annotation(
    matched_df: pd.DataFrame,
    gnomad_dir: Path,
    logger: Optional[logging.Logger] = None,
) -> pd.DataFrame:
    """
    Stage 4b: Annotate variants with gnomAD population frequencies.

    Applies BA1, BS1, PM2 ACMG criteria based on allele frequencies.

    Args:
        matched_df: DataFrame with matched variants
        gnomad_dir: Path to gnomAD VCF files
        logger: Optional logger instance

    Returns:
        DataFrame with gnomad_af, BA1, BS1, PM2 columns added
    """
    if logger:
        logger.info("Stage 4b: gnomAD annotation...")

    from varidex.pipeline.gnomad_annotator_parallel import (
        annotate_with_gnomad_parallel,
        apply_frequency_acmg_criteria,
    )

    # Ensure ref/alt columns exist
    if "ref" not in matched_df.columns and "ref_allele" in matched_df.columns:
        matched_df["ref"] = matched_df["ref_allele"]
    if "alt" not in matched_df.columns and "alt_allele" in matched_df.columns:
        matched_df["alt"] = matched_df["alt_allele"]

    # Annotate with gnomAD
    result = annotate_with_gnomad_parallel(matched_df, gnomad_dir, n_workers=6)

    # Apply frequency criteria
    result = apply_frequency_acmg_criteria(result)

    if logger:
        with_af = result["gnomad_af"].notna().sum()
        logger.info(f"  ✓ {with_af:,} variants with gnomAD frequency")
        logger.info(
            f"  ✓ BA1: {result['BA1'].sum():,}, BS1: {result['BS1'].sum():,}, PM2: {result['PM2'].sum():,}"
        )

    return result


def execute_stage4c_consequence_criteria(
    annotated_df: pd.DataFrame,
    logger: Optional[logging.Logger] = None,
) -> pd.DataFrame:
    """
    Stage 4c: Apply consequence-based ACMG criteria (PVS1, BP7).

    Args:
        annotated_df: DataFrame with variants and gnomAD annotations
        logger: Optional logger instance

    Returns:
        DataFrame with PVS1, BP7, acmg_final_auto columns added
    """
    if logger:
        logger.info("Stage 4c: Consequence-based ACMG criteria...")

    from scripts.add_consequence_criteria import (
        apply_consequence_criteria,
        update_acmg_classification,
    )

    # Apply PVS1 and BP7
    result = apply_consequence_criteria(annotated_df)

    # Generate automated classification
    result["acmg_final_auto"] = result.apply(update_acmg_classification, axis=1)

    if logger:
        pvs1 = result["PVS1"].sum()
        bp7 = result["BP7"].sum()
        logger.info(f"  ✓ PVS1: {pvs1:,}, BP7: {bp7:,}")

        pathogenic = (
            result["acmg_final_auto"].str.contains("Pathogenic", na=False).sum()
        )
        benign = result["acmg_final_auto"].str.contains("Benign", na=False).sum()
        logger.info(f"  ✓ Auto-classified: {pathogenic:,} P/LP, {benign:,} B/LB")

    return result
