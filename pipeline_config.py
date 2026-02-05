#!/usr/bin/env python3
"""
varidex/pipeline/pipeline_config.py - Configuration Management v1.0.0-dev

Centralized configuration, safeguards, and YAML loading.

Development version - not for production use.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger: logging.Logger = logging.getLogger(__name__)


class FallbackConfig:
    """Default configuration when centralized imports unavailable."""

    MATCH_MODE: str = "hybrid"
    CHECKPOINT_DIR: Path = Path(".varidex_cache")


class SafeguardConfig:
    """ACMG pipeline safety thresholds and validation settings."""

    CLINVAR_MAX_AGE_DAYS: int = 45
    MAX_ERROR_RATE: float = 0.05
    MAX_VALIDATION_ERROR_RATE: float = 0.10
    ABORT_ON_THRESHOLD: bool = True
    ENABLE_VALIDATION: bool = True
    ERROR_LOG_PATH: str = "results/classification_errors.log"


def load_yaml_config(config_path: Path = Path(".varidex.yaml")) -> Dict[str, Any]:
    """Load YAML configuration file with safe parsing."""
    if not config_path.exists():
        logger.debug(f"Config file not found: {config_path}")
        return {}

    try:
        import yaml

        with open(config_path, "r", encoding="utf-8") as f:
            cfg: Any = yaml.safe_load(f)
        logger.info(f"✓ Loaded config: {config_path}")
        return cfg or {}
    except ImportError:
        logger.warning("PyYAML not installed - skipping YAML config")
        return {}
    except Exception as e:
        logger.warning(f"Config load failed: {e}")
        return {}


def get_safeguard_config(yaml_config: Dict[str, Any]) -> Dict[str, Any]:
    """Merge configuration from ENV variables > YAML > defaults."""
    defaults: Dict[str, Any] = {
        "max_error_rate": SafeguardConfig.MAX_ERROR_RATE,
        "max_validation_error_rate": SafeguardConfig.MAX_VALIDATION_ERROR_RATE,
        "abort_on_threshold": SafeguardConfig.ABORT_ON_THRESHOLD,
        "enable_validation": SafeguardConfig.ENABLE_VALIDATION,
        "error_log_path": SafeguardConfig.ERROR_LOG_PATH,
        "clinvar_max_age_days": SafeguardConfig.CLINVAR_MAX_AGE_DAYS,
    }

    cfg: Dict[str, Any] = defaults.copy()
    cfg.update(yaml_config.get("safeguards", {}))

    cfg["max_error_rate"] = float(os.getenv("MAX_ERROR_RATE", cfg["max_error_rate"]))
    cfg["max_validation_error_rate"] = float(
        os.getenv("MAX_VALIDATION_ERROR_RATE", cfg["max_validation_error_rate"])
    )
    cfg["abort_on_threshold"] = os.getenv("GRACEFUL_MODE", "false").lower() != "true"

    _validate_safeguard_config(cfg)
    return cfg


def _validate_safeguard_config(cfg: Dict[str, Any]) -> None:
    """Validate safeguard configuration values."""
    if not 0.0 <= cfg["max_error_rate"] <= 1.0:
        raise ValueError(f"max_error_rate must be 0.0-1.0, got {cfg['max_error_rate']}")

    if not 0.0 <= cfg["max_validation_error_rate"] <= 1.0:
        raise ValueError(
            f"max_validation_error_rate must be 0.0-1.0, "
            f"got {cfg['max_validation_error_rate']}"
        )

    if cfg["clinvar_max_age_days"] < 0:
        raise ValueError(
            f"clinvar_max_age_days must be positive, "
            f"got {cfg['clinvar_max_age_days']}"
        )


def get_config_value(config_obj: Any, name: str, default: Any = None) -> Any:
    """Safely retrieve configuration value from config object."""
    try:
        return getattr(config_obj, name, default)
    except (AttributeError, TypeError):
        return default
