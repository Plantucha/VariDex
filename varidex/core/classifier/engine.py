#!/usr/bin/env python3
"""
varidex/core/classifier/engine.py - ACMG Classifier Engine v6.0.0

Production-grade ACMG 2015 variant classification.

Enabled Evidence (7 codes):
  PVS1, PM4, PP2, BA1, BS1, BP1, BP3

Disabled Evidence (21 codes):
  PM2 (requires gnomAD), BP7 (requires SpliceAI)

Reference: Richards et al. 2015, PMID 25741868
"""

from typing import Tuple, List, Dict, Optional, Set, Any
from functools import lru_cache, wraps
import pandas as pd
import logging
import time

from varidex.version import __version__
from varidex.core.models import ACMGEvidenceSet, VariantData
from varidex.core.config import LOF_GENES, MISSENSE_RARE_GENES, CLINVAR_STAR_RATINGS
from varidex.core.classifier.text_utils import normalize_text, split_delimited_value
from varidex.core.classifier.config import ACMGConfig, ACMGMetrics
from varidex.exceptions import ACMGValidationError, ACMGClassificationError

logger = logging.getLogger(__name__)

# LOF indicators
LOF_INDICATORS = frozenset([
    'frameshift', 'nonsense', 'stop-gain', 'stop-gained',
    'canonical-splice', 'splice-donor', 'splice-acceptor',
    'start-lost', 'stop-lost', 'initiator-codon'
])

SORTED_STAR_RATINGS = sorted(CLINVAR_STAR_RATINGS.items(), key=lambda x: -len(x[0]))


@lru_cache(maxsize=1024)

class ACMGClassifier:
    """Enterprise-grade ACMG 2015 variant classifier.

    Features:
    - Error handling
    - Configuration management
    - Metrics collection
    - Feature flags
    - Input validation
    - Graceful degradation
    """

    def __init__(self, config: Optional[ACMGConfig] = None) -> None:
        """Initialize classifier with configuration."""
        self.config = config if config else ACMGConfig()
        self.metrics = ACMGMetrics() if self.config.enable_metrics else None

        if self.config.enable_logging:
            logging.basicConfig(
                level=getattr(logging, self.config.log_level),
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )

        logger.info(f"ACMGClassifier {__version__} Initialized: "
                   f"PVS1={self.config.enable_pvs1}, PM2={self.config.enable_pm2}, "
                   f"BP7={self.config.enable_bp7}")

    @staticmethod
    @lru_cache(maxsize=512)
    def get_star_rating(review_status: str) -> int:
        """Convert ClinVar review status to star rating (0-4) CACHED."""
        try:
            if pd.isna(review_status):
                return 0

            review_lower = normalize_text(review_status)

            if review_lower in CLINVAR_STAR_RATINGS:
                return CLINVAR_STAR_RATINGS[review_lower]

            for key, stars in SORTED_STAR_RATINGS:
                if key in review_lower:
                    return stars

            return 0

        except Exception as e:
            logger.warning(f"Failed to get star rating for '{review_status}': {e}")
            return 0

    @staticmethod
    def validate_variant(variant: VariantData) -> Tuple[bool, List[str]]:
        """Enhanced validation with detailed error reporting."""
        errors: List[str] = []

        try:
            if not variant:
                errors.append("Variant object is None")
                return False, errors

            required_fields = {
                'clinical_sig': 'Clinical significance',
                'gene': 'Gene annotation',
                'variant_type': 'Variant type',
                'molecular_consequence': 'Molecular consequence'
            }

            for field, description in required_fields.items():
                if not hasattr(variant, field):
                    errors.append(f"Missing {field}: {description}")
                elif pd.isna(getattr(variant, field)) or not getattr(variant, field):
                    errors.append(f"Empty {field}: {description}")

            if hasattr(variant, 'star_rating'):
                if variant.star_rating < 0 or variant.star_rating > 4:
                    errors.append(f"Star rating out of bounds: {variant.star_rating}")

            return len(errors) == 0, errors

        except Exception as e:
            logger.error(f"Validation exception: {e}")
            errors.append(f"Validation exception: {str(e)}")
            return False, errors

    @staticmethod
    def extract_genes(gene_field: str) -> Set[str]:
        """Extract unique gene symbols from multi-gene field."""
        try:
            if pd.isna(gene_field):
                return set()

            return set(split_delimited_value(str(gene_field)))

        except Exception as e:
            logger.warning(f"Gene extraction failed for '{gene_field}': {e}")
            return set()

    @staticmethod
    def check_lof(variant_consequence: str, sig: str) -> bool:
        """Check if variant is loss-of-function."""
        try:
            cons_lower = normalize_text(variant_consequence)
            sig_lower = normalize_text(sig)

            return any(ind in cons_lower or ind in sig_lower for ind in LOF_INDICATORS)

        except Exception as e:
            logger.warning(f"LOF check failed: {e}")
            return False

    def assign_evidence(self, variant: VariantData) -> ACMGEvidenceSet:
        """Assign ACMG evidence codes to variant.

        Enabled codes:
        - PVS1: LOF in LOF-intolerant genes (e.g., BRCA1 frameshift)
        - PM4: Protein length changes (e.g., 3-bp deletion in CFTR)
        - PP2: Missense in missense-rare genes (e.g., HBB missense)
        - BA1: Common polymorphism (e.g., MAF > 5%)
        - BS1: High population frequency (e.g., MAF > 1%)
        - BP1: Missense in LOF genes (e.g., TP53 missense)
        - BP3: In-frame indel in repetitive region

        Disabled codes (metadata preserved):
        - PM2: Absent/rare in population databases (requires gnomAD API)
        - BP7: Synonymous variant (requires SpliceAI scores)
        """
        evidence = ACMGEvidenceSet()

        try:
            # Validate variant
            is_valid, errors = self.validate_variant(variant)
            if not is_valid:
                if self.metrics:
                    self.metrics.record_validation_error()
                for error in errors:
                    evidence.conflicts.add(f"Validation error: {error}")  # FIXED: append -> add
                logger.warning(f"Validation failed: {errors}")
                return evidence

            # Extract fields
            sig_lower = normalize_text(variant.clinical_sig)
            genes = self.extract_genes(variant.gene)
            consequence = normalize_text(variant.molecular_consequence)

            # Check for conflicting interpretations
            if 'conflict' in sig_lower or '/' in variant.clinical_sig:
                evidence.conflicts.add("ClinVar conflicting interpretations")  # FIXED: append -> add

            # === PATHOGENIC EVIDENCE ===

            # PVS1: LOF in LOF-intolerant genes
            if self.config.enable_pvs1:
                try:
                    if self.check_lof(consequence, sig_lower):
                        matching_genes = genes.intersection(LOF_GENES)
                        if matching_genes:
                            evidence.pvs.add("PVS1")
                            logger.debug(f"PVS1: LOF in {matching_genes}")
                except Exception as e:
                    logger.error(f"PVS1 assignment failed: {e}")

            # PM4: Protein length changes
            if self.config.enable_pm4:
                try:
                    if 'inframe' in consequence or 'in-frame' in consequence or 'stop-lost' in consequence:
                        if 'deletion' in consequence or 'insertion' in consequence:
                            evidence.pm.add("PM4")
                            logger.debug("PM4: Protein length change")
                except Exception as e:
                    logger.error(f"PM4 assignment failed: {e}")

            # PP2: Missense in missense-rare genes
            if self.config.enable_pp2:
                try:
                    if 'missense' in consequence:
                        matching_genes = genes.intersection(MISSENSE_RARE_GENES)
                        if matching_genes and 'pathogenic' in sig_lower:
                            evidence.pp.add("PP2")
                            logger.debug(f"PP2: Missense in {matching_genes}")
                except Exception as e:
                    logger.error(f"PP2 assignment failed: {e}")

            # PM2 DISABLED - add to conflicts
            if not self.config.enable_pm2:
                evidence.conflicts.add("PM2 DISABLED: requires gnomAD API")  # FIXED: append -> add

            # === BENIGN EVIDENCE ===

            # BA1: Common polymorphism
            if self.config.enable_ba1:
                try:
                    if 'common' in sig_lower and 'polymorphism' in sig_lower:
                        evidence.ba.add("BA1")
                        logger.debug("BA1: Common polymorphism")
                except Exception as e:
                    logger.error(f"BA1 assignment failed: {e}")

            # BS1: High population frequency
            if self.config.enable_bs1:
                try:
                    if ('population' in sig_lower and 'frequency' in sig_lower and 'high' in sig_lower) or                        ('common' in sig_lower and 'pathogenic' not in sig_lower):
                        evidence.bs.add("BS1")
                        logger.debug("BS1: High population frequency")
                except Exception as e:
                    logger.error(f"BS1 assignment failed: {e}")

            # BP1: Missense in LOF genes
            if self.config.enable_bp1:
                try:
                    if 'missense' in consequence:
                        matching_genes = genes.intersection(LOF_GENES)
                        if matching_genes and 'benign' in sig_lower:
                            evidence.bp.add("BP1")
                            logger.debug(f"BP1: Missense in LOF gene {matching_genes}")
                except Exception as e:
                    logger.error(f"BP1 assignment failed: {e}")

            # BP3: In-frame indel in repetitive region
            if self.config.enable_bp3:
                try:
                    if 'inframe' in consequence or 'in-frame' in consequence:
                        if 'repeat' in sig_lower or 'repetitive' in sig_lower:
                            evidence.bp.add("BP3")
                            logger.debug("BP3: In-frame indel in repeat")
                except Exception as e:
                    logger.error(f"BP3 assignment failed: {e}")

            # BP7 DISABLED - add to conflicts
            if not self.config.enable_bp7:
                evidence.conflicts.add("BP7 DISABLED: requires SpliceAI scores")  # FIXED: append -> add

            # Convert sets to lists for deduplication (already done by sets)
            # This ensures no duplicate codes
            for attr in ['pvs', 'ps', 'pm', 'pp', 'ba', 'bs', 'bp']:
                setattr(evidence, attr, list(dict.fromkeys(getattr(evidence, attr))))

            return evidence

        except Exception as e:
            logger.error(f"Evidence assignment failed: {e}", exc_info=True)
            evidence.conflicts.add(f"Assignment error: {str(e)}")  # FIXED: append -> add
            return evidence

    def calculate_evidence_score(self, evidence: ACMGEvidenceSet) -> Tuple[float, float]:
        """Calculate numerical evidence scores."""
        try:
            weights = self.config.get_evidence_weights()

            path_score = (
                len(evidence.pvs) * weights['PVS'] +
                len(evidence.ps) * weights['PS'] +
                len(evidence.pm) * weights['PM'] +
                len(evidence.pp) * weights['PP']
            )

            benign_score = (
                len(evidence.ba) * weights['BA'] +
                len(evidence.bs) * weights['BS'] +
                len(evidence.bp) * weights['BP']
            )

            return float(path_score), float(benign_score)

        except Exception as e:
            logger.error(f"Score calculation failed: {e}")
            return 0.0, 0.0

    def combine_evidence(self, evidence: ACMGEvidenceSet) -> Tuple[str, str]:
        """Apply ACMG 2015 combination rules (Richards et al. Table 5)."""
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
                    return "Uncertain Significance", f"Strong conflict ({path_score}v{benign_score})"
                elif strong_path and benign_score < self.config.strong_evidence_threshold:
                    pass  # Continue to pathogenic rules
                elif strong_benign and path_score < self.config.strong_evidence_threshold:
                    pass  # Continue to benign rules
                elif self.config.conflict_balanced_min <= path_ratio <= self.config.conflict_balanced_max:
                    return "Uncertain Significance", f"Balanced ({path_score}v{benign_score})"
                else:
                    return "Uncertain Significance", f"Conflict ({path_score}v{benign_score})"

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

    def classify_variant(self, variant: VariantData) -> Tuple[str, str, ACMGEvidenceSet, float]:
        """Complete classification pipeline with metrics."""
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

            logger.info(f"Classified {variant} → {classification} ({confidence}) in {duration:.3f}s")

            return classification, confidence, evidence, duration

        except Exception as e:
            duration = time.time() - start_time
            if self.metrics:
                self.metrics.record_failure()

            logger.error(f"Classification pipeline failed: {e}", exc_info=True)
            return "Uncertain Significance", f"Error: {str(e)}", ACMGEvidenceSet(), duration

    def health_check(self) -> Dict[str, Any]:
        """Health check endpoint for production monitoring."""
        try:
            health = {
                'status': 'healthy',
                'version': __version__,
                'config': {
                    'pvs1_enabled': self.config.enable_pvs1,
                    'pm2_enabled': self.config.enable_pm2,
                    'bp7_enabled': self.config.enable_bp7,
                },
                'dependencies': {
                    'lof_genes': len(LOF_GENES),
                    'missense_rare_genes': len(MISSENSE_RARE_GENES),
                }
            }

            if self.metrics:
                health['metrics'] = self.metrics.get_summary()

            return health

        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}


if __name__ == "__main__":
    print("="*80)
    print(f"ACMG Classifier {__version__} CORE - Use tests.py for testing")
    print("="*80)
else:
    logger.info(f"ACMGClassifier {__version__} Production classifier loaded")
    logger.info(f" - {len(LOF_GENES)} LOF genes, {len(MISSENSE_RARE_GENES)} missense-rare genes")
    logger.info(" - Enterprise features: Error handling, Metrics, Config management")
    logger.info(" - DISABLED: PM2 (gnomAD), BP7 (SpliceAI) - hallucination fixes maintained")
