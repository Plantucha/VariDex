#!/usr/bin/env python3
"""varidex/core/classifier/engine.py - ACMG Classifier Engine v6.4.0

Production-grade ACMG 2015 variant classification.

Enabled Evidence (7 codes):
  PVS1, PM4, PP2, BA1, BS1, BP1, BP3

Disabled Evidence (21 codes):
  PM2 (requires gnomAD), BP7 (requires SpliceAI)

Reference: Richards et al. 2015, PMID 25741868

Refactoring v6.4.0:
  - Utilities moved to evidence_utils.py
  - Evidence assignment moved to evidence_assignment.py
  - Core classification logic remains here
  - All files now under 500 lines
"""

from typing import Tuple, Dict, Optional, Any
import logging
import time

from varidex.version import __version__
from varidex.core.models import ACMGEvidenceSet, VariantData
from varidex.core.config import LOF_GENES, MISSENSE_RARE_GENES
from varidex.core.classifier.config import ACMGConfig, ACMGMetrics
from varidex.core.classifier.evidence_assignment import assign_evidence_codes

logger = logging.getLogger(__name__)


class ACMGClassifier:
    """Enterprise-grade ACMG 2015 variant classifier.

    Features:
    - Error handling
    - Configuration management
    - Metrics collection
    - Feature flags
    - Input validation
    - Graceful degradation

    Refactored in v6.4.0 for better modularity.
    """

    def __init__(self, config: Optional[ACMGConfig] = None) -> None:
        """Initialize classifier with configuration."""
        self.config: ACMGConfig = config if config else ACMGConfig()
        self.metrics: Optional[ACMGMetrics] = (
            ACMGMetrics() if self.config.enable_metrics else None
        )

        if self.config.enable_logging:
            logging.basicConfig(
                level=getattr(logging, self.config.log_level),
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )

        logger.info(
            f"ACMGClassifier {__version__} Initialized: "
            f"PVS1={self.config.enable_pvs1}, PM2={self.config.enable_pm2}, "
            f"BP7={self.config.enable_bp7}"
        )

    def assign_evidence(self, variant: VariantData) -> ACMGEvidenceSet:
        """Assign ACMG evidence codes to variant.

        Delegates to evidence_assignment.assign_evidence_codes().

        Args:
            variant: VariantData object

        Returns:
            ACMGEvidenceSet with assigned evidence codes
        """
        return assign_evidence_codes(variant, self.config, self.metrics)

    def calculate_evidence_score(
        self, evidence: ACMGEvidenceSet
    ) -> Tuple[float, float]:
        """Calculate numerical evidence scores.

        Args:
            evidence: ACMGEvidenceSet

        Returns:
            Tuple of (pathogenic_score, benign_score)
        """
        try:
            weights = self.config.get_evidence_weights()

            path_score = (
                len(evidence.pvs) * weights["PVS"]
                + len(evidence.ps) * weights["PS"]
                + len(evidence.pm) * weights["PM"]
                + len(evidence.pp) * weights["PP"]
            )

            benign_score = (
                len(evidence.ba) * weights["BA"]
                + len(evidence.bs) * weights["BS"]
                + len(evidence.bp) * weights["BP"]
            )

            return float(path_score), float(benign_score)

        except Exception as e:
            logger.error(f"Score calculation failed: {e}")
            return 0.0, 0.0

    def combine_evidence(self, evidence: ACMGEvidenceSet) -> Tuple[str, str]:
        """Apply ACMG 2015 combination rules (Richards et al. Table 5).

        Args:
            evidence: ACMGEvidenceSet

        Returns:
            Tuple of (classification, confidence)
        """
        try:
            pvs = len(evidence.pvs)
            ps = len(evidence.ps)
            pm = len(evidence.pm)
            pp = len(evidence.pp)
            ba = len(evidence.ba)
            bs = len(evidence.bs)
            bp = len(evidence.bp)

            # Stand-alone benign (BA1 overrides all)
            if ba > 0:
                if pvs + ps + pm + pp == 0:
                    return "Benign", "Stand-alone BA1 (overrides conflict)"
                return "Benign", "Stand-alone BA1"

            # Conflict resolution
            path_score, benign_score = self.calculate_evidence_score(evidence)
            if path_score > 0 and benign_score > 0:
                total = path_score + benign_score
                path_ratio = path_score / total if total > 0 else 0

                strong_path = path_score >= self.config.strong_evidence_threshold
                strong_benign = benign_score >= self.config.strong_evidence_threshold

                if strong_path and strong_benign:
                    return (
                        "Uncertain Significance",
                        f"Strong conflict ({path_score}v{benign_score})",
                    )
                elif (
                    strong_path and benign_score < self.config.strong_evidence_threshold
                ):
                    pass  # Continue to pathogenic rules
                elif (
                    strong_benign and path_score < self.config.strong_evidence_threshold
                ):
                    pass  # Continue to benign rules
                elif (
                    self.config.conflict_balanced_min
                    <= path_ratio
                    <= self.config.conflict_balanced_max
                ):
                    return (
                        "Uncertain Significance",
                        f"Balanced ({path_score}v{benign_score})",
                    )
                else:
                    return (
                        "Uncertain Significance",
                        f"Conflict ({path_score}v{benign_score})",
                    )

            # === PATHOGENIC RULES ===

            # Rule 1: PVS1 + PS
            if pvs >= 1:
                if ps >= 1:
                    return "Pathogenic", "Very High"
                if pm >= 2:
                    return "Pathogenic", "High"
                if pm >= 1 and pp >= 1:
                    return "Pathogenic", "High"
                if pp >= 2:
                    return "Pathogenic", "Moderate"

            # Rule 5: 2 PS
            if ps >= 2:
                return "Pathogenic", "High"

            # Rules 6-8: PS combinations
            if ps >= 1:
                if pm >= 3:
                    return "Pathogenic", "High"
                if pm >= 2 and pp >= 2:
                    return "Pathogenic", "Moderate"
                if pm >= 1 and pp >= 4:
                    return "Pathogenic", "Moderate"

            # === LIKELY PATHOGENIC RULES ===

            # Rule 1: PVS1 + PM
            if pvs >= 1 and pm >= 1:
                return "Likely Pathogenic", "Moderate"

            # Rule 2: PS + 1-2 PM
            if ps >= 1 and pm >= 1 and pm <= 2:
                return "Likely Pathogenic", "Moderate"

            # Rule 3: PS + 2 PP
            if ps >= 1 and pp >= 2:
                return "Likely Pathogenic", "Moderate"

            # Rule 4: 3 PM
            if pm >= 3:
                return "Likely Pathogenic", "Moderate"

            # Rule 5: 2PM + 2PP
            if pm >= 2 and pp >= 2:
                return "Likely Pathogenic", "Low"

            # Rule 6: PM + 4PP
            if pm >= 1 and pp >= 4:
                return "Likely Pathogenic", "Low"

            # === BENIGN RULES ===

            # Rule 2: 2 BS
            if bs >= 2:
                return "Benign", "High"

            # Rule 3: BS + BP
            if bs >= 1 and bp >= 1:
                return "Benign", "High"

            # === LIKELY BENIGN RULES ===

            # Rule 1: 1 BS
            if bs >= 1:
                return "Likely Benign", "Moderate"

            # Rule 2: ≥2 BP
            if bp >= 2:
                return "Likely Benign", "Low"

            # VUS (default)
            if pvs + ps + pm + pp == 0 or bs + bp == 0:
                return "Uncertain Significance", "Insufficient Evidence"

            return "Uncertain Significance", "No Evidence"

        except Exception as e:
            logger.error(f"Classification failed: {e}", exc_info=True)
            return "Uncertain Significance", f"Error: {str(e)}"

    def classify_variant(
        self, variant: VariantData
    ) -> Tuple[str, str, ACMGEvidenceSet, float]:
        """Complete classification pipeline with metrics.

        Args:
            variant: VariantData object

        Returns:
            Tuple of (classification, confidence, evidence, duration)
        """
        start_time = time.time()

        try:
            # Assign evidence
            evidence = self.assign_evidence(variant)

            # Combine evidence
            classification, confidence = self.combine_evidence(evidence)

            duration = time.time() - start_time

            # Record metrics
            if self.metrics:
                self.metrics.record_success(duration, classification, evidence)

            logger.info(
                f"Classified {variant} → {classification} ({confidence}) "
                f"in {duration:.3f}s"
            )

            return classification, confidence, evidence, duration

        except Exception as e:
            duration = time.time() - start_time
            if self.metrics:
                self.metrics.record_failure()

            logger.error(f"Classification pipeline failed: {e}", exc_info=True)
            return (
                "Uncertain Significance",
                f"Error: {str(e)}",
                ACMGEvidenceSet(),
                duration,
            )

    def health_check(self) -> Dict[str, Any]:
        """Health check endpoint for production monitoring.

        Returns:
            Dictionary with health status and metrics
        """
        try:
            health: Dict[str, Any] = {
                "status": "healthy",
                "version": __version__,
                "config": {
                    "pvs1_enabled": self.config.enable_pvs1,
                    "pm2_enabled": self.config.enable_pm2,
                    "bp7_enabled": self.config.enable_bp7,
                },
                "dependencies": {
                    "lof_genes": len(LOF_GENES),
                    "missense_rare_genes": len(MISSENSE_RARE_GENES),
                },
            }

            if self.metrics:
                health["metrics"] = self.metrics.get_summary()

            return health

        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


if __name__ == "__main__":
    print("=" * 80)
    print(f"ACMG Classifier {__version__} v6.4.0 - Use tests.py for testing")
    print("=" * 80)
    print("\nRefactored for modularity:")
    print("  - evidence_utils.py: Utility functions")
    print("  - evidence_assignment.py: Evidence logic")
    print("  - engine.py: Core classifier (this file)")
    print("\nAll files now under 500-line limit!")
else:
    logger.info(f"ACMGClassifier {__version__} v6.4.0 Production classifier loaded")
    logger.info(
        f" - {len(LOF_GENES)} LOF genes, {len(MISSENSE_RARE_GENES)} missense-rare genes"
    )
    logger.info(" - Enterprise features: Error handling, Metrics, Config management")
    logger.info(
        " - DISABLED: PM2 (gnomAD), BP7 (SpliceAI) - hallucination fixes maintained"
    )
    logger.info(" - Modular: evidence_utils.py + evidence_assignment.py")
