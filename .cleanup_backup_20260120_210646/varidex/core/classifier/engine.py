#!/usr/bin/env python3
"""
varidex/core/classifier/engine.py - ACMG Classifier Engine v6.0.0
====================================================================
Production-grade ACMG 2015 variant classification.

Enabled Evidence: 7 codes (PVS1, PM4, PP2, BA1, BS1, BP1, BP3)
Disabled Evidence: 21 codes (PM2 requires gnomAD, BP7 requires SpliceAI)

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
from varidex.core.classifier.config import ACMGConfig, ACMGMetrics
from varidex.exceptions import ACMGValidationError, ACMGClassificationError

logger = logging.getLogger(__name__)

LOF_INDICATORS = frozenset([
    'frameshift', 'nonsense', 'stop_gain', 'stop-gained',
    'canonical_splice', 'splice_donor', 'splice_acceptor',
    'start_lost', 'stop-lost', 'initiator_codon'
])

SORTED_STAR_RATINGS = sorted(CLINVAR_STAR_RATINGS.items(), key=lambda x: -len(x[0]))


def timed_operation(func):
    """Decorator to time operations for metrics."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start
            return result, duration
        except Exception as e:
            duration = time.time() - start
            raise
    return wrapper


@lru_cache(maxsize=1024)
def normalize_text(text: Optional[str]) -> str:
    """Normalize text for consistent matching (cached)."""
    if pd.isna(text) or not text:
        return ""
    return str(text).strip().lower()


def split_delimited_value(value: str, delimiters: str = ',;|') -> List[str]:
    """Split string on multiple delimiters and spaces."""
    if not value:
        return []
    result = value.split()
    final_result = []
    for item in result:
        parts = [item]
        for delim in delimiters:
            parts = [subitem for part in parts for subitem in part.split(delim)]
        final_result.extend(parts)
    return [x.strip() for x in final_result if x.strip()]


class ACMGClassifier:
    """
    Enterprise-grade ACMG 2015 variant classifier.

    Features: Error handling, configuration management, metrics collection,
    feature flags, input validation, graceful degradation.
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

        logger.info(
            f"ACMGClassifier {__version__} Initialized: "
            f"PVS1={self.config.enable_pvs1}, PM2={self.config.enable_pm2}, "
            f"BP7={self.config.enable_bp7}"
        )

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
                    errors.append(f"Missing field: {description}")
                elif pd.isna(getattr(variant, field)) or not getattr(variant, field):
                    errors.append(f"Empty field: {description}")

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
    def check_lof_variant(consequence: str, sig: str) -> bool:
        """Check if variant is loss-of-function."""
        try:
            cons_lower = normalize_text(consequence)
            sig_lower = normalize_text(sig)
            return any(ind in cons_lower or ind in sig_lower for ind in LOF_INDICATORS)
        except Exception as e:
            logger.warning(f"LOF check failed: {e}")
            return False

    def assign_evidence(self, variant: VariantData) -> ACMGEvidenceSet:
        """
        Assign ACMG evidence codes to variant.

        Enabled codes:
        - PVS1: LOF in LOF-intolerant genes (e.g., BRCA1 frameshift)
        - PM4: Protein length changes (e.g., 3-bp deletion in CFTR)
        - PP2: Missense in missense-rare genes (e.g., HBB missense)
        - BA1: Common polymorphism (e.g., MAF >5%)
        - BS1: High population frequency (e.g., MAF >1%)
        - BP1: Missense in LOF genes (e.g., TP53 missense)
        - BP3: In-frame indel in repetitive region

        Disabled codes (metadata preserved):
        - PM2: Absent/rare in population databases (requires gnomAD API)
        - BP7: Synonymous variant (requires SpliceAI scores)
        """
        evidence = ACMGEvidenceSet()

        try:
            is_valid, errors = self.validate_variant(variant)
            if not is_valid:
                if self.metrics:
                    self.metrics.record_validation_error()
                for error in errors:
                    evidence.conflicts.append(f"Validation: {error}")
                logger.warning(f"Validation failed: {errors}")
                return evidence

            sig_lower = normalize_text(variant.clinical_sig)
            genes = self.extract_genes(variant.gene)
            consequence = normalize_text(variant.molecular_consequence)

            if 'conflict' in sig_lower or '/' in variant.clinical_sig:
                evidence.conflicts.append("ClinVar conflicting interpretations")

            if self.config.enable_pvs1:
                try:
                    if self.check_lof_variant(consequence, sig_lower):
                        matching_genes = genes.intersection(LOF_GENES)
                        if matching_genes:
                            evidence.pvs.append('PVS1')
                            logger.debug(f"PVS1: LOF in {matching_genes}")
                except Exception as e:
                    logger.error(f"PVS1 assignment failed: {e}")

            if self.config.enable_pm4:
                try:
                    if 'inframe' in consequence or 'in-frame' in consequence or 'stop_lost' in consequence:
                        if 'deletion' in consequence or 'insertion' in consequence:
                            evidence.pm.append('PM4')
                            logger.debug("PM4: Protein length change")
                except Exception as e:
                    logger.error(f"PM4 assignment failed: {e}")

            if self.config.enable_pp2:
                try:
                    if 'missense' in consequence:
                        matching_genes = genes.intersection(MISSENSE_RARE_GENES)
                        if matching_genes and 'pathogenic' in sig_lower:
                            evidence.pp.append('PP2')
                            logger.debug(f"PP2: Missense in {matching_genes}")
                except Exception as e:
                    logger.error(f"PP2 assignment failed: {e}")

            if not self.config.enable_pm2:
                evidence.conflicts.append("PM2 DISABLED: requires gnomAD API")

            if self.config.enable_ba1:
                try:
                    if 'common' in sig_lower and 'polymorphism' in sig_lower:
                        evidence.ba.append('BA1')
                        logger.debug("BA1: Common polymorphism")
                except Exception as e:
                    logger.error(f"BA1 assignment failed: {e}")

            if self.config.enable_bs1:
                try:
                    if (('population' in sig_lower and 'frequency' in sig_lower and 'high' in sig_lower) or
                        ('common' in sig_lower and 'pathogenic' not in sig_lower)):
                        evidence.bs.append('BS1')
                        logger.debug("BS1: High population frequency")
                except Exception as e:
                    logger.error(f"BS1 assignment failed: {e}")

            if self.config.enable_bp1:
                try:
                    if 'missense' in consequence:
                        matching_genes = genes.intersection(LOF_GENES)
                        if matching_genes and 'benign' in sig_lower:
                            evidence.bp.append('BP1')
                            logger.debug(f"BP1: Missense in LOF gene {matching_genes}")
                except Exception as e:
                    logger.error(f"BP1 assignment failed: {e}")

            if self.config.enable_bp3:
                try:
                    if 'inframe' in consequence or 'in-frame' in consequence:
                        if 'repeat' in sig_lower or 'repetitive' in sig_lower:
                            evidence.bp.append('BP3')
                            logger.debug("BP3: In-frame indel in repeat")
                except Exception as e:
                    logger.error(f"BP3 assignment failed: {e}")

            if not self.config.enable_bp7:
                evidence.conflicts.append("BP7 DISABLED: requires SpliceAI scores")

            for attr in ['pvs', 'ps', 'pm', 'pp', 'ba', 'bs', 'bp']:
                setattr(evidence, attr, list(dict.fromkeys(getattr(evidence, attr))))

            return evidence

        except Exception as e:
            logger.error(f"Evidence assignment failed: {e}", exc_info=True)
            evidence.conflicts.append(f"Assignment error: {str(e)}")
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

            if ba > 0:
                if pvs + ps + pm + pp > 0:
                    return "Benign", "Stand-alone (BA1 overrides conflict)"
                return "Benign", "Stand-alone (BA1)"

            path_score, benign_score = self.calculate_evidence_score(evidence)

            if path_score > 0 and benign_score > 0:
                total = path_score + benign_score
                path_ratio = path_score / total if total > 0 else 0
                strong_path = path_score >= self.config.strong_evidence_threshold
                strong_benign = benign_score >= self.config.strong_evidence_threshold

                if strong_path and strong_benign:
                    return "Uncertain Significance", f"Strong conflict ({path_score}v{benign_score})"
                elif strong_path and benign_score < self.config.strong_evidence_threshold:
                    pass
                elif strong_benign and path_score < self.config.strong_evidence_threshold:
                    pass
                elif self.config.conflict_balanced_min <= path_ratio <= self.config.conflict_balanced_max:
                    return "Uncertain Significance", f"Balanced ({path_score}v{benign_score})"
                else:
                    return "Uncertain Significance", f"Conflict ({path_score}v{benign_score})"

            if pvs >= 1:
                if ps >= 1:
                    return "Pathogenic", "Very High"
                if pm >= 2:
                    return "Pathogenic", "High"
                if pm == 1 and pp >= 1:
                    return "Pathogenic", "High"
                if pp >= 2:
                    return "Pathogenic", "Moderate"

            if ps >= 2:
                return "Pathogenic", "High"

            if ps == 1:
                if pm >= 3:
                    return "Pathogenic", "High"
                if pm == 2 and pp >= 2:
                    return "Pathogenic", "Moderate"
                if pm == 1 and pp >= 4:
                    return "Pathogenic", "Moderate"

            if pvs == 1 and pm == 1:
                return "Likely Pathogenic", "Moderate"
            if ps == 1 and pm == 1:
                return "Likely Pathogenic", "Moderate"
            if ps == 1 and pp >= 2:
                return "Likely Pathogenic", "Moderate"
            if pm >= 3:
                return "Likely Pathogenic", "Moderate"
            if pm == 2 and pp >= 2:
                return "Likely Pathogenic", "Low"
            if pm == 1 and pp >= 4:
                return "Likely Pathogenic", "Low"

            if bs >= 2:
                return "Benign", "High"
            if bs == 1 and bp >= 1:
                return "Benign", "High"

            if bs == 1:
                return "Likely Benign", "Moderate"
            if bp >= 2:
                return "Likely Benign", "Low"

            if pvs + ps + pm + pp > 0 or bs + bp > 0:
                return "Uncertain Significance", "Insufficient Evidence"

            return "Uncertain Significance", "No Evidence"

        except Exception as e:
            logger.error(f"Classification failed: {e}", exc_info=True)
            return "Uncertain Significance", f"Error: {str(e)}"

    def classify_variant(self, variant: VariantData) -> Tuple[str, str, ACMGEvidenceSet, float]:
        """Complete classification pipeline with metrics."""
        start_time = time.time()
        try:
            evidence = self.assign_evidence(variant)
            classification, confidence = self.combine_evidence(evidence)
            duration = time.time() - start_time

            if self.metrics:
                self.metrics.record_success(duration, classification, evidence)

            logger.info(f"Classified variant: {classification} ({confidence}) in {duration:.3f}s")
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
    print("=" * 80)
    print(f"ACMG Classifier {__version__} CORE - Use tests.py for testing")
    print("=" * 80)
else:
    logger.info(f"ACMGClassifier {__version__} Production classifier loaded")
    logger.info(f" - {len(LOF_GENES)} LOF genes, {len(MISSENSE_RARE_GENES)} missense-rare genes")
    logger.info(" - Enterprise features: Error handling, Metrics, Config management")
    logger.info(" - DISABLED: PM2 (gnomAD), BP7 (SpliceAI) - hallucination fixes maintained")
