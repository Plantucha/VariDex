#!/usr/bin/env python3
"""
varidex.core.classifier.config - ACMG Classifier Configuration & Metrics

Purpose: Enterprise configuration management and metrics collection
Version: Production v6.0.0
Author: CODER 2 - Classifier & Exceptions Team
Date: January 18, 2026

Dependencies:
    - dataclasses (standard library)
    - typing (standard library)
    - collections (standard library)
    - varidex.version (__version__)
    - varidex.exceptions (ACMGConfigurationError)

Features:
    - ACMGConfig: Dataclass for configuration with validation
    - ACMGMetrics: Production metrics collection
    - Feature flags for rollback capability

Usage:
    from varidex.core.classifier.config import ACMGConfig, ACMGMetrics

    config = ACMGConfig(enable_pm2=False, weight_pvs=10)
    classifier = ACMGClassifier(config)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any
from collections import defaultdict

from varidex.exceptions import ACMGConfigurationError


@dataclass
class ACMGConfig:
    """
    Enterprise-grade configuration with validation.

    Features:
        - Feature flags for rollback capability
        - Configurable thresholds
        - Validation on initialization
        - Environment variable support (future)

    Example:
        config = ACMGConfig(enable_pm2=False, weight_pvs=10)
        classifier = ACMGClassifier(config)
    """

    # === ENABLED CODES ===
    enable_pvs1: bool = True
    enable_pm4: bool = True
    enable_pp2: bool = True
    enable_ba1: bool = True
    enable_bs1: bool = True
    enable_bp1: bool = True
    enable_bp3: bool = True

    # === DISABLED CODES - hallucination fixes ===
    enable_pm2: bool = False  # Requires gnomAD API
    enable_bp7: bool = False  # Requires SpliceAI scores

    # === Evidence weights for numerical scoring ===
    weight_pvs: int = 8
    weight_ps: int = 4
    weight_pm: int = 2
    weight_pp: int = 1
    weight_ba: int = 8
    weight_bs: int = 4
    weight_bp: int = 1

    # === Conflict resolution thresholds ===
    conflict_balanced_min: float = 0.4
    conflict_balanced_max: float = 0.6
    strong_evidence_threshold: int = 4

    # === Performance settings ===
    lru_cache_size_text: int = 1024
    lru_cache_size_rating: int = 512

    # === Logging ===
    enable_logging: bool = True
    log_level: str = "INFO"

    # === Metrics ===
    enable_metrics: bool = True

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        self.validate()

    def validate(self) -> None:
        """
        Validate configuration values.

        Raises:
            ACMGConfigurationError: If configuration is invalid
        """
        # Check conflict thresholds
        if not (0 <= self.conflict_balanced_min <= self.conflict_balanced_max <= 1):
            raise ACMGConfigurationError(
                "Invalid conflict thresholds: {self.conflict_balanced_min}, "
                "{self.conflict_balanced_max}. Must be 0 <= min <= max <= 1"
            )

        # Check evidence threshold
        if self.strong_evidence_threshold < 1:
            raise ACMGConfigurationError(
                "Strong evidence threshold must be >= 1, got {self.strong_evidence_threshold}"
            )

        # Check log level
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level not in valid_levels:
            raise ACMGConfigurationError(
                "Invalid log level '{self.log_level}'. Must be one of {valid_levels}"
            )

        # Check weights are positive
        weights = [
            self.weight_pvs,
            self.weight_ps,
            self.weight_pm,
            self.weight_pp,
            self.weight_ba,
            self.weight_bs,
            self.weight_bp,
        ]
        if any(w <= 0 for w in weights):
            raise ACMGConfigurationError("All evidence weights must be positive")

    def get_evidence_weights(self) -> Dict[str, int]:
        """
        Get evidence weights as dictionary.

        Returns:
            Dictionary mapping evidence strength to weight

        Example:
            config = ACMGConfig()
            weights = config.get_evidence_weights()
            # weights={'PVS': 8, ...}
        """
        return {
            "PVS": self.weight_pvs,
            "PS": self.weight_ps,
            "PM": self.weight_pm,
            "PP": self.weight_pp,
            "BA": self.weight_ba,
            "BS": self.weight_bs,
            "BP": self.weight_bp,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for serialization."""
        return {
            "feature_flags": {
                "pvs1": self.enable_pvs1,
                "pm4": self.enable_pm4,
                "pp2": self.enable_pp2,
                "pm2": self.enable_pm2,
                "ba1": self.enable_ba1,
                "bs1": self.enable_bs1,
                "bp1": self.enable_bp1,
                "bp3": self.enable_bp3,
                "bp7": self.enable_bp7,
            },
            "weights": self.get_evidence_weights(),
            "thresholds": {
                "conflict_balanced_min": self.conflict_balanced_min,
                "conflict_balanced_max": self.conflict_balanced_max,
                "strong_evidence": self.strong_evidence_threshold,
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ACMGConfig":
        """
        Create config from dictionary.

        Args:
            data: Dictionary with config values

        Returns:
            ACMGConfig instance
        """
        return cls(
            enable_pvs1=data.get("enable_pvs1", True),
            enable_pm4=data.get("enable_pm4", True),
            enable_pp2=data.get("enable_pp2", True),
            enable_pm2=data.get("enable_pm2", False),
            enable_ba1=data.get("enable_ba1", True),
            enable_bs1=data.get("enable_bs1", True),
            enable_bp1=data.get("enable_bp1", True),
            enable_bp3=data.get("enable_bp3", True),
            enable_bp7=data.get("enable_bp7", False),
            weight_pvs=data.get("weight_pvs", 8),
            weight_ps=data.get("weight_ps", 4),
            weight_pm=data.get("weight_pm", 2),
            weight_pp=data.get("weight_pp", 1),
            weight_ba=data.get("weight_ba", 8),
            weight_bs=data.get("weight_bs", 4),
            weight_bp=data.get("weight_bp", 1),
            conflict_balanced_min=data.get("conflict_balanced_min", 0.4),
            conflict_balanced_max=data.get("conflict_balanced_max", 0.6),
            strong_evidence_threshold=data.get("strong_evidence_threshold", 4),
        )


@dataclass
class ACMGMetrics:
    """
    Production metrics for monitoring and alerting.

    Tracks:
        - Classification counts and success rates
        - Performance timing
        - Evidence distribution
        - Classification distribution
        - Error rates

    Example:
        metrics = ACMGMetrics()
        metrics.record_success(0.05, "Pathogenic", evidence)
        summary = metrics.get_summary()
        print("Success rate: {summary['success_rate']:.1%}")
    """

    total_classifications: int = 0
    successful_classifications: int = 0
    failed_classifications: int = 0
    validation_errors: int = 0
    classification_times: List[float] = field(default_factory=list)
    evidence_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    classification_distribution: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def record_success(self, duration: float, classification: str, evidence: Any) -> None:
        """
        Record successful classification.

        Args:
            duration: Classification time in seconds
            classification: Final classification string
            evidence: ACMGEvidenceSet object
        """
        self.total_classifications += 1
        self.successful_classifications += 1
        self.classification_times.append(duration)
        self.classification_distribution[classification] += 1

        # Count evidence codes
        for ev in evidence.pvs:
            self.evidence_counts[ev] += 1
        for ev in evidence.pm:
            self.evidence_counts[ev] += 1
        for ev in evidence.pp:
            self.evidence_counts[ev] += 1
        for ev in evidence.ba:
            self.evidence_counts[ev] += 1
        for ev in evidence.bs:
            self.evidence_counts[ev] += 1
        for ev in evidence.bp:
            self.evidence_counts[ev] += 1

    def record_failure(self) -> None:
        """Record failed classification."""
        self.total_classifications += 1
        self.failed_classifications += 1

    def record_validation_error(self) -> None:
        """Record validation error."""
        self.validation_errors += 1

    def get_success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_classifications == 0:
            return 0.0
        return self.successful_classifications / self.total_classifications

    def get_avg_time(self) -> float:
        """Calculate average classification time in milliseconds."""
        if not self.classification_times:
            return 0.0
        return sum(self.classification_times) / len(self.classification_times) * 1000

    def get_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive metrics summary.

        Returns:
            Dictionary with all metrics

        Example:
            metrics.get_summary()
            # {'total': 1000, 'successful': 995, 'failed': 5,
            #  'success_rate': 0.995, 'avg_time_ms': 45.2, ...}
        """
        return {
            "total": self.total_classifications,
            "successful": self.successful_classifications,
            "failed": self.failed_classifications,
            "validation_errors": self.validation_errors,
            "success_rate": self.get_success_rate(),
            "avg_time_ms": self.get_avg_time(),
            "min_time_ms": (
                min(self.classification_times) * 1000 if self.classification_times else 0
            ),
            "max_time_ms": (
                max(self.classification_times) * 1000 if self.classification_times else 0
            ),
            "evidence_counts": dict(self.evidence_counts),
            "classification_distribution": dict(self.classification_distribution),
        }

    def get_performance_report(self) -> str:
        """Generate human-readable performance report."""
        summary = self.get_summary()

        report = """
ACMG Classifier Performance Report
{'='*70}
Total Classifications: {summary['total']:,}
Success Rate: {summary['success_rate']*100:.1f}%
Average Time: {summary['avg_time_ms']:.1f}ms
Min/Max Time: {summary['min_time_ms']:.1f}ms / {summary['max_time_ms']:.1f}ms

Classification Distribution:
  • Pathogenic: {summary['classification_distribution'].get('Pathogenic', 0):,}
  • Likely Pathogenic: {summary['classification_distribution'].get('Likely Pathogenic', 0):,}
  • VUS: {summary['classification_distribution'].get('Uncertain Significance', 0):,}
  • Likely Benign: {summary['classification_distribution'].get('Likely Benign', 0):,}
  • Benign: {summary['classification_distribution'].get('Benign', 0):,}

Top Evidence Codes:
"""
        # Sort evidence by frequency
        evidence = sorted(summary["evidence_counts"].items(), key=lambda x: x[1], reverse=True)[:10]

        for code, count in evidence:
            report += "  • {code}: {count:,}\n"

        return report

    def reset(self) -> None:
        """Reset all metrics."""
        self.total_classifications = 0
        self.successful_classifications = 0
        self.failed_classifications = 0
        self.validation_errors = 0
        self.classification_times.clear()
        self.evidence_counts.clear()
        self.classification_distribution.clear()

    def __str__(self) -> str:
        """String representation."""
        self.get_summary()
        return (
            "ACMGMetrics(v{__version__}, "
            "total={summary['total']}, "
            "success_rate={summary['success_rate']:.1%}, "
            "avg_time={summary['avg_time_ms']:.1f}ms)"
        )


# === MODULE SELF-TEST ===

if __name__ == "__main__":
    print("=" * 80)
    print("ACMG Classifier v6.0 - Configuration & Metrics")
    print("=" * 80)
    print()
    print("This module provides:")
    print("  - ACMGConfig: Configuration management")
    print("  - ACMGMetrics: Production metrics")
    print()
    print("Usage:")
    print("  from varidex.core.classifier.config import ACMGConfig, ACMGMetrics")
    print("  config = ACMGConfig(enable_pm2=False)")
    print("  metrics = ACMGMetrics()")
    print("=" * 80)


def get_preset(name="balanced"):
    """Get preset ACMG configuration."""
    presets = {
        "strict": ACMGConfig(
            config_name="strict",
            config_description="Conservative preset",
            weight_pvs=10,
            weight_ps=5,
            weight_pm=3,
            weight_pp=1,
            strong_evidence_threshold=6,
        ),
        "balanced": ACMGConfig(
            config_name="balanced",
            config_description="Standard ACMG weights",
            weight_pvs=8,
            weight_ps=4,
            weight_pm=2,
            weight_pp=1,
            strong_evidence_threshold=4,
        ),
        "lenient": ACMGConfig(
            config_name="lenient",
            config_description="Research preset",
            weight_pvs=6,
            weight_ps=3,
            weight_pm=2,
            weight_pp=1,
            strong_evidence_threshold=3,
        ),
    }

    if name not in presets:
        raise ValueError("Invalid preset: {name}")

    return presets[name]
