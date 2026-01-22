#!/usr/bin/env python3
"""varidex/core/services/computational_prediction.py - Computational Prediction Service

Service for determining PP3 and BP4 ACMG evidence codes based on
computational predictions from multiple algorithms.

Evidence Codes:
  - PP3: Multiple lines of computational evidence support deleterious effect
  - BP4: Multiple lines of computational evidence support benign effect

Algorithm Consensus:
  - Requires ≥3 concordant predictions for PP3
  - Requires ≥3 concordant predictions for BP4
  - PP3 and BP4 are mutually exclusive (PP3 takes precedence)

Offline Mode:
  This service requires internet connectivity via DbNSFPClient.
  For offline use, initialize with enable_predictions=False.
  The classifier will gracefully degrade to engine_v7 (gnomAD only)
  or engine_v6 (base functionality).

Algorithm Availability:
  VEP may not return all algorithms for every variant.
  Missing algorithms are handled gracefully and do not count toward consensus.
  A warning is logged if fewer than 3 algorithms are available.

Reference: Richards et al. 2015, PMID 25741868
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
from enum import Enum
import logging

from varidex.integrations.dbnsfp_client import DbNSFPClient, PredictionScore

logger = logging.getLogger(__name__)


class PredictionStrength(Enum):
    """Strength of computational evidence."""

    STRONG_DELETERIOUS = "strong_deleterious"
    MODERATE_DELETERIOUS = "moderate_deleterious"
    WEAK_DELETERIOUS = "weak_deleterious"
    NEUTRAL = "neutral"
    WEAK_BENIGN = "weak_benign"
    MODERATE_BENIGN = "moderate_benign"
    STRONG_BENIGN = "strong_benign"


@dataclass
class PredictionThresholds:
    """Configurable thresholds for computational predictions.

    These thresholds determine when algorithms vote for deleterious or benign.
    """

    # SIFT thresholds (0-1, lower = more deleterious)
    sift_deleterious: float = 0.05
    sift_benign: float = 0.05

    # PolyPhen-2 thresholds (0-1, higher = more deleterious)
    polyphen_deleterious: float = 0.5  # "possibly damaging" cutoff
    polyphen_benign: float = 0.3

    # CADD thresholds (1-99, higher = more deleterious)
    cadd_deleterious: float = 20.0  # Top 1% of variants
    cadd_benign: float = 15.0

    # REVEL thresholds (0-1, higher = more deleterious)
    revel_deleterious: float = 0.5
    revel_benign: float = 0.3

    # Consensus thresholds
    pp3_min_concordant: int = 3  # Min algorithms for PP3
    bp4_min_concordant: int = 3  # Min algorithms for BP4

    # Conflict resolution
    conflict_ratio_threshold: float = 0.4  # If deleterious ratio < 0.4 or > 0.6, resolve


@dataclass
class ComputationalEvidence:
    """Result of computational prediction analysis."""

    pp3: bool = False  # PP3 applies
    bp4: bool = False  # BP4 applies

    deleterious_count: int = 0
    benign_count: int = 0
    total_predictions: int = 0

    strength: PredictionStrength = PredictionStrength.NEUTRAL
    reasoning: str = ""

    # Individual algorithm results
    sift_result: Optional[str] = None
    polyphen_result: Optional[str] = None
    cadd_result: Optional[str] = None
    revel_result: Optional[str] = None
    metasvm_result: Optional[str] = None

    # Algorithm availability tracking
    algorithms_available: int = 0
    algorithms_missing: list = None

    def __post_init__(self):
        """Initialize mutable defaults."""
        if self.algorithms_missing is None:
            self.algorithms_missing = []

    def summary(self) -> str:
        """Generate human-readable summary."""
        if self.pp3:
            return "PP3: {self.deleterious_count}/{self.total_predictions} deleterious"
        elif self.bp4:
            return "BP4: {self.benign_count}/{self.total_predictions} benign"
        else:
            return "Neither PP3 nor BP4: {self.deleterious_count}D/{self.benign_count}B"


class ComputationalPredictionService:
    """Service for analyzing computational predictions and determining PP3/BP4.

    Uses multiple prediction algorithms to establish consensus for
    deleterious (PP3) or benign (BP4) effect.

    Gracefully handles:
      - Missing algorithms (logs warning if < 3 available)
      - Offline mode (returns no evidence)
      - API failures (returns no evidence)
      - Incomplete data (uses available algorithms)
    """

    def __init__(
        self,
        dbnsfp_client: Optional[DbNSFPClient] = None,
        thresholds: Optional[PredictionThresholds] = None,
        enable_predictions: bool = True,
    ):
        """Initialize computational prediction service.

        Args:
            dbnsfp_client: DbNSFP/VEP client instance
            thresholds: Custom prediction thresholds
            enable_predictions: Enable prediction queries (False for testing/offline)
        """
        self.enable_predictions = enable_predictions
        self.thresholds = thresholds if thresholds else PredictionThresholds()

        if enable_predictions:
            self.client = dbnsfp_client if dbnsfp_client else DbNSFPClient()
            logger.info("ComputationalPredictionService initialized with VEP client")
        else:
            self.client = None
            logger.info("ComputationalPredictionService initialized in offline mode")

    def _analyze_sift(self, score: PredictionScore) -> Optional[str]:
        """Analyze SIFT prediction.

        Returns:
            'deleterious', 'benign', or None
        """
        if score.sift_prediction:
            pred = score.sift_prediction.lower()
            if "deleterious" in pred:
                return "deleterious"
            elif "tolerated" in pred:
                return "benign"

        if score.sift_score is not None:
            if score.sift_score < self.thresholds.sift_deleterious:
                return "deleterious"
            elif score.sift_score > self.thresholds.sift_benign:
                return "benign"

        return None

    def _analyze_polyphen(self, score: PredictionScore) -> Optional[str]:
        """Analyze PolyPhen-2 prediction.

        Returns:
            'deleterious', 'benign', or None
        """
        if score.polyphen_prediction:
            pred = score.polyphen_prediction.lower()
            if "damaging" in pred:  # probably_damaging or possibly_damaging
                return "deleterious"
            elif "benign" in pred:
                return "benign"

        if score.polyphen_score is not None:
            if score.polyphen_score > self.thresholds.polyphen_deleterious:
                return "deleterious"
            elif score.polyphen_score < self.thresholds.polyphen_benign:
                return "benign"

        return None

    def _analyze_cadd(self, score: PredictionScore) -> Optional[str]:
        """Analyze CADD prediction.

        Returns:
            'deleterious', 'benign', or None
        """
        if score.cadd_phred is not None:
            if score.cadd_phred >= self.thresholds.cadd_deleterious:
                return "deleterious"
            elif score.cadd_phred < self.thresholds.cadd_benign:
                return "benign"

        return None

    def _analyze_revel(self, score: PredictionScore) -> Optional[str]:
        """Analyze REVEL prediction.

        Returns:
            'deleterious', 'benign', or None
        """
        if score.revel_score is not None:
            if score.revel_score >= self.thresholds.revel_deleterious:
                return "deleterious"
            elif score.revel_score < self.thresholds.revel_benign:
                return "benign"

        return None

    def _analyze_metasvm(self, score: PredictionScore) -> Optional[str]:
        """Analyze MetaSVM prediction.

        Returns:
            'deleterious', 'benign', or None
        """
        if score.metasvm_prediction:
            if score.metasvm_prediction == "D":
                return "deleterious"
            elif score.metasvm_prediction == "T":
                return "benign"

        return None

    def _check_pp3(self, evidence: ComputationalEvidence) -> Tuple[bool, str]:
        """Check if PP3 (computational evidence supporting pathogenic) applies.

        Args:
            evidence: ComputationalEvidence with counts

        Returns:
            Tuple of (applies, reasoning)
        """
        min_concordant = self.thresholds.pp3_min_concordant

        if evidence.deleterious_count >= min_concordant:
            if evidence.benign_count == 0:
                reason = (
                    "PP3: {evidence.deleterious_count} concordant deleterious predictions "
                    "(SIFT={evidence.sift_result}, PolyPhen={evidence.polyphen_result}, "
                    "CADD={evidence.cadd_result})"
                )
                return True, reason
            elif evidence.deleterious_count > evidence.benign_count * 2:
                reason = (
                    "PP3: {evidence.deleterious_count} deleterious vs "
                    "{evidence.benign_count} benign predictions (strong consensus)"
                )
                return True, reason

        return False, "PP3 not met: insufficient concordant deleterious predictions"

    def _check_bp4(self, evidence: ComputationalEvidence) -> Tuple[bool, str]:
        """Check if BP4 (computational evidence supporting benign) applies.

        Args:
            evidence: ComputationalEvidence with counts

        Returns:
            Tuple of (applies, reasoning)
        """
        min_concordant = self.thresholds.bp4_min_concordant

        # BP4 cannot apply if PP3 already applies
        if evidence.pp3:
            return False, "BP4 deferred to PP3 (conflicting evidence)"

        if evidence.benign_count >= min_concordant:
            if evidence.deleterious_count == 0:
                reason = (
                    "BP4: {evidence.benign_count} concordant benign predictions "
                    "(SIFT={evidence.sift_result}, PolyPhen={evidence.polyphen_result}, "
                    "CADD={evidence.cadd_result})"
                )
                return True, reason
            elif evidence.benign_count > evidence.deleterious_count * 2:
                reason = (
                    "BP4: {evidence.benign_count} benign vs "
                    "{evidence.deleterious_count} deleterious predictions (strong consensus)"
                )
                return True, reason

        return False, "BP4 not met: insufficient concordant benign predictions"

    def analyze_predictions(
        self, chromosome: str, position: int, ref: str, alt: str, gene: Optional[str] = None
    ) -> ComputationalEvidence:
        """Analyze computational predictions and determine PP3/BP4.

        Args:
            chromosome: Chromosome
            position: Genomic position
            ref: Reference allele
            alt: Alternate allele
            gene: Gene symbol (optional, for logging)

        Returns:
            ComputationalEvidence with PP3/BP4 determination
        """
        evidence = ComputationalEvidence()

        try:
            # Get predictions
            if not self.enable_predictions or not self.client:
                evidence.reasoning = "Predictions disabled (offline mode)"
                logger.info(
                    "Predictions disabled - use enable_predictions=True or check connectivity"
                )
                return evidence

            predictions = self.client.get_predictions(chromosome, position, ref, alt)

            if predictions is None or not predictions.has_scores:
                evidence.reasoning = "No prediction scores available from VEP"
                logger.debug("No predictions for {chromosome}:{position} {ref}>{alt}")
                return evidence

            # Analyze each algorithm
            evidence.sift_result = self._analyze_sift(predictions)
            evidence.polyphen_result = self._analyze_polyphen(predictions)
            evidence.cadd_result = self._analyze_cadd(predictions)
            evidence.revel_result = self._analyze_revel(predictions)
            evidence.metasvm_result = self._analyze_metasvm(predictions)

            # Track algorithm availability
            all_algorithms = ["SIFT", "PolyPhen-2", "CADD", "REVEL", "MetaSVM"]
            all_results = [
                evidence.sift_result,
                evidence.polyphen_result,
                evidence.cadd_result,
                evidence.revel_result,
                evidence.metasvm_result,
            ]

            evidence.algorithms_available = sum(1 for r in all_results if r is not None)
            evidence.algorithms_missing = [
                algo for algo, result in zip(all_algorithms, all_results) if result is None
            ]

            # Warn if limited algorithm coverage
            if evidence.algorithms_available < 3:
                logger.warning(
                    "Limited algorithm coverage for {chromosome}:{position} - "
                    "only {evidence.algorithms_available}/5 algorithms available. "
                    "Missing: {', '.join(evidence.algorithms_missing)}. "
                    "PP3/BP4 requires ≥3 algorithms."
                )

            # Count votes
            for result in all_results:
                if result == "deleterious":
                    evidence.deleterious_count += 1
                    evidence.total_predictions += 1
                elif result == "benign":
                    evidence.benign_count += 1
                    evidence.total_predictions += 1

            logger.info(
                "Predictions for {chromosome}:{position}: "
                "{evidence.deleterious_count}D/{evidence.benign_count}B "
                "of {evidence.total_predictions} ({evidence.algorithms_available} algorithms)"
            )

            # Check PP3 first (pathogenic takes precedence)
            pp3_applies, pp3_reason = self._check_pp3(evidence)
            evidence.pp3 = pp3_applies

            if pp3_applies:
                evidence.reasoning = pp3_reason
                evidence.strength = PredictionStrength.STRONG_DELETERIOUS
                logger.info("PP3 applies: {pp3_reason}")
            else:
                # Check BP4 only if PP3 doesn't apply
                bp4_applies, bp4_reason = self._check_bp4(evidence)
                evidence.bp4 = bp4_applies

                if bp4_applies:
                    evidence.reasoning = bp4_reason
                    evidence.strength = PredictionStrength.STRONG_BENIGN
                    logger.info("BP4 applies: {bp4_reason}")
                else:
                    # Neither applies
                    if evidence.total_predictions == 0:
                        evidence.reasoning = "No predictions available"
                    elif evidence.algorithms_available < 3:
                        evidence.reasoning = (
                            "Insufficient algorithms ({evidence.algorithms_available}/5) "
                            "for PP3/BP4 determination"
                        )
                    elif evidence.deleterious_count > 0 and evidence.benign_count > 0:
                        evidence.reasoning = "Conflicting predictions: {evidence.deleterious_count}D/{evidence.benign_count}B"
                        evidence.strength = PredictionStrength.NEUTRAL
                    else:
                        evidence.reasoning = "Insufficient concordant predictions for PP3 or BP4"

                    logger.debug("Neither PP3 nor BP4: {evidence.reasoning}")

            return evidence

        except Exception:
            logger.error("Prediction analysis failed for {chromosome}:{position}: {e}")
            evidence.reasoning = "Analysis error: {str(e)}"
            return evidence

    def get_statistics(self) -> Dict[str, Any]:
        """Get service statistics.

        Returns:
            Dictionary with service statistics
        """
        stats = {
            "enabled": self.enable_predictions,
            "offline_mode": not self.enable_predictions,
            "thresholds": {
                "pp3_min_concordant": self.thresholds.pp3_min_concordant,
                "bp4_min_concordant": self.thresholds.bp4_min_concordant,
            },
        }

        if self.client:
            stats["client"] = self.client.get_statistics()

        return stats


if __name__ == "__main__":
    print("=" * 80)
    print("Computational Prediction Service - PP3/BP4 Evidence")
    print("=" * 80)
    print("\nEvidence Codes:")
    print("  PP3: Multiple computational evidence supporting pathogenic")
    print("      Requires ≥3 concordant deleterious predictions")
    print("\n  BP4: Multiple computational evidence supporting benign")
    print("      Requires ≥3 concordant benign predictions")
    print("\nSupported Algorithms:")
    print("  • SIFT (score < 0.05 = deleterious)")
    print("  • PolyPhen-2 (score > 0.5 = deleterious)")
    print("  • CADD (phred ≥ 20 = deleterious)")
    print("  • REVEL (score ≥ 0.5 = deleterious)")
    print("  • MetaSVM (D = deleterious, T = tolerated)")
    print("\nAlgorithm Availability:")
    print("  ⚠️  VEP may not return all algorithms for every variant")
    print("  • Missing algorithms are handled gracefully")
    print("  • Warning logged if < 3 algorithms available")
    print("  • PP3/BP4 requires ≥3 algorithms minimum")
    print("\nOffline Mode:")
    print("  • Set enable_predictions=False for offline use")
    print("  • Service will return no evidence gracefully")
    print("  • Classifier degrades to engine_v7 or v6")
    print("=" * 80)
else:
    logger.info("ComputationalPredictionService loaded - PP3/BP4 determination")
