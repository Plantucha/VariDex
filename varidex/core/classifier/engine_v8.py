#!/usr/bin/env python3
"""varidex/core/classifier/engine_v8.py - ACMG Classifier with Computational Predictions

Production ACMG 2015 variant classifier with gnomAD + computational predictions.

Enabled Evidence (12 codes):
  Pathogenic:
    - PVS1: LOF in LOF-intolerant genes
    - PM2: Absent/rare in population databases (gnomAD)
    - PM4: Protein length changes
    - PP2: Missense in missense-rare genes
    - PP3: Computational evidence supporting pathogenic (NEW)

  Benign:
    - BA1: Common polymorphism >5% (gnomAD)
    - BS1: Allele frequency too high >1% (gnomAD)
    - BP1: Missense in LOF genes
    - BP3: In-frame indel in repetitive region
    - BP4: Computational evidence supporting benign (NEW)

Disabled Evidence (16 codes):
  PS1-4, PM1, PM3, PM5-6, PP1, PP4-5, BS2-4, BP2, BP5-7

Reference: Richards et al. 2015, PMID 25741868
"""

from typing import Tuple, Optional, Dict, Any
import logging
import time

from varidex.core.models import ACMGEvidenceSet, VariantData
from varidex.core.classifier.engine_v7 import ACMGClassifierV7
from varidex.core.classifier.config import ACMGConfig
from varidex.core.services.computational_prediction import (
    ComputationalPredictionService,
    PredictionThresholds,
)
from varidex.integrations.dbnsfp_client import DbNSFPClient

logger = logging.getLogger(__name__)


class ACMGClassifierV8(ACMGClassifierV7):
    """Enhanced ACMG classifier with gnomAD + computational predictions.

    Extends ACMGClassifierV7 with:
    - PP3: Computational evidence supporting pathogenic
    - BP4: Computational evidence supporting benign

    Uses multiple prediction algorithms (SIFT, PolyPhen, CADD, REVEL, MetaSVM)
    to establish consensus for deleterious or benign effect.

    Maintains backward compatibility and graceful degradation.
    """

    VERSION = "8.0.1"

    def __init__(
        self,
        config: Optional[ACMGConfig] = None,
        enable_gnomad: bool = True,
        enable_predictions: bool = True,
        gnomad_client: Optional[Any] = None,
        dbnsfp_client: Optional[DbNSFPClient] = None,
        prediction_thresholds: Optional[PredictionThresholds] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize enhanced classifier with computational predictions.

        Args:
            config: ACMG configuration
            enable_gnomad: Enable gnomAD queries (from v7)
            enable_predictions: Enable computational predictions (new)
            gnomad_client: Custom GnomadClient instance
            dbnsfp_client: Custom DbNSFPClient instance
            prediction_thresholds: Custom prediction thresholds
            **kwargs: Additional args for parent class
        """
        # Initialize parent (v7 with gnomAD)
        super().__init__(
            config=config,
            enable_gnomad=enable_gnomad,
            gnomad_client=gnomad_client,
            **kwargs,
        )

        # Initialize prediction service
        self.enable_predictions: bool = enable_predictions
        self.prediction_service: Optional[ComputationalPredictionService] = None

        if enable_predictions:
            try:
                self.prediction_service = ComputationalPredictionService(
                    dbnsfp_client=dbnsfp_client,
                    thresholds=prediction_thresholds,
                    enable_predictions=True,
                )
                logger.info(
                    f"ACMGClassifierV8 {self.VERSION} initialized with computational predictions"
                )
            except Exception as e:
                logger.error(f"Failed to initialize prediction service: {e}")
                logger.warning("Continuing without computational predictions")
                self.enable_predictions = False
                self.prediction_service = None
        else:
            logger.info(
                f"ACMGClassifierV8 {self.VERSION} initialized without computational predictions"
            )

    def assign_evidence(self, variant: VariantData) -> ACMGEvidenceSet:
        """Assign ACMG evidence codes including computational predictions.

        Extends v7 classifier with PP3 and BP4 from computational predictions.

        Args:
            variant: VariantData object

        Returns:
            ACMGEvidenceSet with evidence codes
        """
        # Get base evidence from parent (PVS1, PM2, PM4, PP2, BA1, BS1, BP1, BP3)
        evidence = super().assign_evidence(variant)

        # V8 TRIPLE MATCHING ENGINE (ClinVar + dbNSFP + gnomAD)
        try:
            from varidex.io.matching import VariantMatcherV8
            from pathlib import Path

	# PM1 SpliceAI (ACMG Phase 1)
            from varidex.acmg.splice import SpliceACMG
            splice = SpliceACMG()
            result = splice.score(variant.chrom, variant.pos, variant.ref, variant.alt)
            if result["pm1"]:
                evidence.pm.add(result["pm1"])
                logger.info(f"PM1 {result['pm1']}: delta={result['delta']:.3f}")
        except Exception as e:
            logger.debug(f"PM1 unavailable: {e}")


            matcher = VariantMatcherV8(Path("./clinvar"))
            match_key = f"{variant.chrom}:{variant.pos}:{variant.ref}:{variant.alt}"
            variant.match_data = matcher.match_triple_sources(match_key)
            logger.debug(
                f"V8 matching OK: {variant.match_data.get('match_strength', 0)} sources"
            )
        except Exception as e:
            logger.debug(f"V8 matching unavailable: {e}")

        # PM1 SpliceAI (ACMG Phase 1: 12 → 15/28 codes)
        try:
            from varidex.acmg.splice import SpliceACMG

            splice = SpliceACMG()
            result = splice.score(
                variant.chrom, int(variant.pos), variant.ref, variant.alt
            )
            if result["pm1"]:
                evidence.pm.add(result["pm1"])
                logger.info(f"PM1 {result['pm1']}: delta={result['delta']:.3f}")
        except Exception as e:
            logger.debug(f"PM1 SpliceAI unavailable: {e}")

        # Add computational prediction evidence if enabled
        if self.enable_predictions and self.prediction_service:
            try:
                # Extract coordinates
                coords = self._extract_variant_coordinates(variant)

                if coords is None:
                    logger.debug(
                        "No coordinates for prediction query, skipping computational analysis"
                    )
                    evidence.conflicts.add("Missing coordinates for predictions")
                    return evidence

                # Query computational predictions
                pred_evidence = self.prediction_service.analyze_predictions(
                    chromosome=coords["chromosome"],
                    position=coords["position"],
                    ref=coords["ref"],  # FIXED: was coords["re"]
                    alt=coords["alt"],
                    gene=coords.get("gene"),
                )

                # Add evidence codes
                if pred_evidence.pp3:
                    evidence.pp.add("PP3")
                    logger.info(f"PP3: {pred_evidence.reasoning}")

                if pred_evidence.bp4:
                    evidence.bp.add("BP4")
                    logger.info(f"BP4: {pred_evidence.reasoning}")

                # Store prediction info for reference
                if hasattr(evidence, "metadata"):
                    evidence.metadata["predictions"] = {
                        "deleterious_count": pred_evidence.deleterious_count,
                        "benign_count": pred_evidence.benign_count,
                        "strength": pred_evidence.strength.value,
                        "algorithms": {
                            "sift": pred_evidence.sift_result,
                            "polyphen": pred_evidence.polyphen_result,
                            "cadd": pred_evidence.cadd_result,
                        },
                    }

                logger.debug(f"Prediction analysis: {pred_evidence.summary()}")

            except Exception as e:
                logger.error(f"Computational prediction analysis failed: {e}")
                evidence.conflicts.add(f"Prediction error: {str(e)}")

        # Convert sets to lists (inherited from parent)
        for attr in ["pvs", "ps", "pm", "pp", "ba", "bs", "bp"]:
            setattr(evidence, attr, list(getattr(evidence, attr)))

        return evidence

    def classify_variant(
        self, variant: VariantData
    ) -> Tuple[str, str, ACMGEvidenceSet, float]:
        """Complete classification pipeline with computational predictions.

        Args:
            variant: VariantData object

        Returns:
            Tuple of (classification, confidence, evidence, duration)
        """
        start_time = time.time()

        try:
            # Assign evidence (includes gnomAD + predictions)
            evidence = self.assign_evidence(variant)

            # Combine evidence using parent logic
            classification, confidence = self.combine_evidence(evidence)

            duration = time.time() - start_time

            # Record metrics
            if self.metrics:
                self.metrics.record_success(duration, classification, evidence)

            logger.info(
                f"Classified {variant} → {classification} ({confidence}) "
                f"in {duration:.3f}s [gnomAD: {self.enable_gnomad}, "
                f"predictions: {self.enable_predictions}]"
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
        """Health check with gnomAD and prediction service status.

        Returns:
            Dictionary with health status
        """
        health = super().health_check()

        # Add prediction service status
        health["predictions"] = {
            "enabled": self.enable_predictions,
            "service_initialized": self.prediction_service is not None,
        }

        if self.prediction_service:
            try:
                health["predictions"][
                    "statistics"
                ] = self.prediction_service.get_statistics()
            except Exception as e:
                health["predictions"]["error"] = str(e)

        health["version"] = self.VERSION

        return health

    def get_enabled_codes(self) -> Dict[str, list]:
        """Get list of enabled evidence codes.

        Returns:
            Dictionary with pathogenic and benign evidence codes
        """
        # Get codes from parent (includes gnomAD codes if enabled)
        codes = super().get_enabled_codes()

        # Add prediction codes if enabled
        if self.enable_predictions:
            if "PP3" not in codes["pathogenic"]:
                codes["pathogenic"].append("PP3")
            if "BP4" not in codes["benign"]:
                codes["benign"].append("BP4")

        return codes

    def get_evidence_summary(self, variant: VariantData) -> Dict[str, Any]:
        """Get detailed evidence summary for a variant.

        Args:
            variant: VariantData object

        Returns:
            Dictionary with detailed evidence breakdown
        """
        classification, confidence, evidence, duration = self.classify_variant(variant)

        summary: Dict[str, Any] = {
            "variant": {
                "rsid": getattr(variant, "rsid", None),
                "gene": getattr(variant, "gene", None),
                "consequence": getattr(variant, "molecular_consequence", None),
            },
            "classification": classification,
            "confidence": confidence,
            "duration_seconds": duration,
            "evidence": {
                "pathogenic": {
                    "PVS": evidence.pvs,
                    "PS": evidence.ps,
                    "PM": evidence.pm,
                    "PP": evidence.pp,
                },
                "benign": {
                    "BA": evidence.ba,
                    "BS": evidence.bs,
                    "BP": evidence.bp,
                },
                "conflicts": list(evidence.conflicts),
            },
            "features_used": {
                "gnomad": self.enable_gnomad,
                "computational_predictions": self.enable_predictions,
            },
        }

        # Add metadata if available
        if hasattr(evidence, "metadata"):
            summary["metadata"] = evidence.metadata

        return summary


if __name__ == "__main__":
    print("=" * 80)
    print(f"ACMG Classifier V8 {ACMGClassifierV8.VERSION} - Full Integration")
    print("=" * 80)
    print("\nEnabled Evidence Codes:")

    # Show without features
    classifier_basic = ACMGClassifierV8(enable_gnomad=False, enable_predictions=False)
    codes_basic = classifier_basic.get_enabled_codes()
    print("\nBasic (no external data):")
    print(f"  Pathogenic: {', '.join(codes_basic['pathogenic'])}")
    print(f"  Benign: {', '.join(codes_basic['benign'])}")
    total_basic = len(codes_basic["pathogenic"]) + len(codes_basic["benign"])
    print(f"  Total: {total_basic} codes")

    # Show with gnomAD
    print("\nWith gnomAD (+PM2, +BA1, +BS1):")
    print("  Total: 10 codes")

    # Show with all features
    print("\nWith gnomAD + Predictions (+PP3, +BP4):")
    print("  Total: 12 codes (43% ACMG coverage)")

    print("\nNew in V8:")
    print("  • PP3: Computational evidence supporting pathogenic")
    print("      → Requires ≥3 concordant deleterious predictions")
    print("      → Algorithms: SIFT, PolyPhen-2, CADD, REVEL, MetaSVM")
    print("  • BP4: Computational evidence supporting benign")
    print("      → Requires ≥3 concordant benign predictions")
    print("      → Same algorithms as PP3")

    print("\nBackward Compatibility:")
    print("  ✅ Works without computational predictions (falls back to v7)")
    print("  ✅ Works without gnomAD (falls back to v6)")
    print("  ✅ Works without any external data (basic v6 functionality)")

    print("=" * 80)
else:
    logger.info(f"ACMGClassifierV8 {ACMGClassifierV8.VERSION} loaded")
    logger.info("  Enhanced with computational predictions (PP3, BP4)")
    logger.info("  Includes gnomAD integration (PM2, BA1, BS1)")
    logger.info("  Backward compatible with v7 and v6, graceful degradation")
