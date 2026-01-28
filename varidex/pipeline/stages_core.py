#!/usr/bin/env python3
"""
varidex/pipeline/stages_core.py v6.3.1 DEVELOPMENT - Core Components

SPLIT FROM stages.py to meet 500-line limit.
Contains: StageProfiler, CheckpointManager, StageExecutor, validators.

CRITICAL FIXES APPLIED:
✓ ALL 20+ f-string prefixes added
✓ Column consistency (ref_allele/alt_allele)
✓ Full error handling added
✓ Documentation corrected
✓ Black-formatted, mypy-ready
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
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from enum import Enum
from tqdm import tqdm
from varidex.utils.helpers import DataValidator

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


STAGE_DEPENDENCIES: Dict[int, List[int]] = {
    2: [],
    3: [],
    4: [2, 3],
    5: [4],
    6: [5],
    7: [6],
}
STAGE_REQUIRED_COLUMNS: Dict[int, List[str]] = {
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
    """Validate if stage dependencies are met."""
    required = set(STAGE_DEPENDENCIES.get(stage_id, []))
    missing = required - completed_stages
    if missing:
        return False, f"Stage {stage_id} missing dependencies: {sorted(missing)}"
    return True, ""


def validate_stage_input(
    df: pd.DataFrame, stage_id: int, stage_name: str
) -> Tuple[bool, str]:
    """Validate DataFrame structure for stage."""

    required_cols = STAGE_REQUIRED_COLUMNS.get(stage_id, [])
    if not required_cols:
        return True, ""
    return DataValidator.validate_dataframe_structure(df, stage_name, required_cols)


class StageProfiler:
    """Performance tracker with thread safety."""

    def __init__(self, enabled: bool = True) -> None:
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
    ) -> None:
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
            f"⏱ {metric.stage_name}: {metric.duration_sec}s, "
            f"{metric.memory_mb}MB, {metric.output_rows} rows"
        )

    def export_metrics(self, output_path: Path) -> None:
        with self._lock:
            metrics_data = [asdict(m) for m in self.metrics]
        with open(output_path, "w") as f:
            json.dump(metrics_data, f, indent=2)
        logger.info(f"📊 Metrics exported to {output_path}")


class CheckpointManager:
    """State snapshots with memory optimization."""

    def __init__(
        self, checkpoint_dir: Path, enabled: bool = True, free_memory: bool = False
    ) -> None:
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
        skip_stages: Optional[Set[int]] = None,
    ) -> None:
        self.profiler = profiler
        self.checkpoint_manager = checkpoint_manager
        self.dry_run = dry_run
        self.skip_stages = skip_stages or set()
        self.completed_stages: Set[int] = set()

    def _validate_dry_run_inputs(self, stage_id: int, *args, **kwargs) -> None:
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
