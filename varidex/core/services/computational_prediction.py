#!/usr/bin/env python3
"""varidex/core/services/computational_prediction.py - Computational Prediction Service

Implements PP3 and BP4 evidence code determination based on computational predictions.

PP3: Multiple lines of computational evidence support a deleterious effect on
     the gene or gene product (conservation, evolutionary, splicing impact, etc.)

BP4: Multiple lines of computational evidence suggest no impact on gene or
     gene product (conservation, evolutionary, splicing impact, etc.)

Criteria (Richards et al. 2015):
- Requires multiple independent algorithms
- Recommended: 4+ algorithms in agreement
- Common algorithms: SIFT, PolyPhen-2, CADD, REVEL, MetaSVM, MutationTaster

Reference: Richards et al. 2015, PMID 25741868
"""

from dataclasses import dataclass
from typing import Optional, List
import logging

from varidex.integrations.dbnsfp_client import (
    DbNSFPClient,
    DbNSFPVariantPredictions,
)

logger = logging.getLogger(__name__)


@dataclass
class ComputationalThresholds:
    """Thresholds for PP3/BP4 determination."""
    
    # Minimum algorithms required for PP3/BP4
    min_algorithms_pp3: int = 4  # Recommended: 4+ algorithms
    min_algorithms_bp4: int = 4
    
    # Consensus threshold (percentage of algorithms in agreement)
    pp3_consensus_threshold: float = 0.75  # 75% must predict deleterious
    bp4_consensus_threshold: float = 0.75  # 75% must predict benign
    
    # Individual algorithm thresholds
    cadd_deleterious_threshold: float = 20.0  # CADD phred score
    cadd_benign_threshold: float = 10.0
    
    revel_pathogenic_threshold: float = 0.5  # REVEL score
    revel_benign_threshold: float = 0.3
    
    # Minimum total algorithms with predictions
    min_total_predictions: int = 3


@dataclass
class ComputationalEvidence:
    """Evidence from computational predictions."""
    
    pp3: bool = False
    bp4: bool = False
    
    deleterious_count: int = 0
    benign_count: int = 0
    total_predictions: int = 0
    
    deleterious_algorithms: List[str] = None
    benign_algorithms: List[str] = None
    
    reasoning: str = ""
    
    def __post_init__(self):
        if self.deleterious_algorithms is None:
            self.deleterious_algorithms = []
        if self.benign_algorithms is None:
            self.benign_algorithms = []
    
    def summary(self) -> str:
        """Generate summary of computational evidence."""
        if self.pp3:
            return (f"PP3: {self.deleterious_count}/{self.total_predictions} algorithms "
                   f"predict deleterious ({', '.join(self.deleterious_algorithms)})")
        elif self.bp4:
            return (f"BP4: {self.benign_count}/{self.total_predictions} algorithms "
                   f"predict benign ({', '.join(self.benign_algorithms)})")
        else:
            return (f"Insufficient computational evidence: "
                   f"{self.deleterious_count} deleterious, {self.benign_count} benign")


class ComputationalPredictionService:
    """Service for determining PP3/BP4 evidence from computational predictions.
    
    Usage:
        service = ComputationalPredictionService(
            dbnsfp_client=DbNSFPClient(dbnsfp_path="/path/to/dbNSFP.gz")
        )
        
        evidence = service.analyze_predictions(
            chromosome="17",
            position=43094692,
            ref="G",
            alt="A"
        )
        
        if evidence.pp3:
            print("Apply PP3 evidence code")
    """
    
    def __init__(
        self,
        dbnsfp_client: Optional[DbNSFPClient] = None,
        thresholds: Optional[ComputationalThresholds] = None,
        enable_dbnsfp: bool = True
    ):
        """Initialize computational prediction service.
        
        Args:
            dbnsfp_client: DbNSFPClient instance (optional)
            thresholds: Custom thresholds (optional)
            enable_dbnsfp: Enable dbNSFP queries
        """
        self.dbnsfp_client = dbnsfp_client
        self.thresholds = thresholds if thresholds else ComputationalThresholds()
        self.enable_dbnsfp = enable_dbnsfp
        
        # Statistics
        self._queries = 0
        self._pp3_assigned = 0
        self._bp4_assigned = 0
        
        if not self.enable_dbnsfp:
            logger.info("ComputationalPredictionService initialized without dbNSFP")
        elif self.dbnsfp_client:
            logger.info("ComputationalPredictionService initialized with dbNSFP")
        else:
            logger.warning("ComputationalPredictionService: No dbNSFP client provided")
    
    def _count_predictions(self, predictions: DbNSFPVariantPredictions) -> tuple[int, int, int, List[str], List[str]]:
        """Count deleterious and benign predictions.
        
        Returns:
            Tuple of (deleterious_count, benign_count, total_count, del_algorithms, ben_algorithms)
        """
        deleterious_count = 0
        benign_count = 0
        deleterious_algs = []
        benign_algs = []
        
        # SIFT: D = deleterious, T = tolerated
        if predictions.sift_pred:
            if 'D' in predictions.sift_pred.upper():
                deleterious_count += 1
                deleterious_algs.append('SIFT')
            elif 'T' in predictions.sift_pred.upper():
                benign_count += 1
                benign_algs.append('SIFT')
        
        # PolyPhen-2 HDIV: D = probably/possibly damaging, B = benign
        if predictions.polyphen2_hdiv_pred:
            pred = predictions.polyphen2_hdiv_pred.upper()
            if 'D' in pred or 'DAMAGING' in pred:
                deleterious_count += 1
                deleterious_algs.append('PolyPhen2-HDIV')
            elif 'B' in pred or 'BENIGN' in pred:
                benign_count += 1
                benign_algs.append('PolyPhen2-HDIV')
        
        # PolyPhen-2 HVAR
        if predictions.polyphen2_hvar_pred:
            pred = predictions.polyphen2_hvar_pred.upper()
            if 'D' in pred or 'DAMAGING' in pred:
                deleterious_count += 1
                deleterious_algs.append('PolyPhen2-HVAR')
            elif 'B' in pred or 'BENIGN' in pred:
                benign_count += 1
                benign_algs.append('PolyPhen2-HVAR')
        
        # CADD: Phred score
        if predictions.cadd_phred is not None:
            if predictions.cadd_phred >= self.thresholds.cadd_deleterious_threshold:
                deleterious_count += 1
                deleterious_algs.append(f'CADD({predictions.cadd_phred:.1f})')
            elif predictions.cadd_phred < self.thresholds.cadd_benign_threshold:
                benign_count += 1
                benign_algs.append(f'CADD({predictions.cadd_phred:.1f})')
        
        # REVEL: Score 0-1
        if predictions.revel_score is not None:
            if predictions.revel_score >= self.thresholds.revel_pathogenic_threshold:
                deleterious_count += 1
                deleterious_algs.append(f'REVEL({predictions.revel_score:.3f})')
            elif predictions.revel_score < self.thresholds.revel_benign_threshold:
                benign_count += 1
                benign_algs.append(f'REVEL({predictions.revel_score:.3f})')
        
        # MetaSVM: D = deleterious, T = tolerated
        if predictions.metasvm_pred:
            if 'D' in predictions.metasvm_pred.upper():
                deleterious_count += 1
                deleterious_algs.append('MetaSVM')
            elif 'T' in predictions.metasvm_pred.upper():
                benign_count += 1
                benign_algs.append('MetaSVM')
        
        # MetaLR: D = deleterious, T = tolerated
        if predictions.metalr_pred:
            if 'D' in predictions.metalr_pred.upper():
                deleterious_count += 1
                deleterious_algs.append('MetaLR')
            elif 'T' in predictions.metalr_pred.upper():
                benign_count += 1
                benign_algs.append('MetaLR')
        
        # MutationTaster: D/A = disease-causing, N/P = polymorphism
        if predictions.mutationtaster_pred:
            pred = predictions.mutationtaster_pred.upper()
            if 'D' in pred or 'A' in pred:
                deleterious_count += 1
                deleterious_algs.append('MutationTaster')
            elif 'N' in pred or 'P' in pred:
                benign_count += 1
                benign_algs.append('MutationTaster')
        
        total_count = deleterious_count + benign_count
        
        return deleterious_count, benign_count, total_count, deleterious_algs, benign_algs
    
    def _check_pp3(
        self,
        deleterious_count: int,
        total_count: int,
        deleterious_algs: List[str]
    ) -> tuple[bool, str]:
        """Check if PP3 criteria are met.
        
        Args:
            deleterious_count: Number of algorithms predicting deleterious
            total_count: Total algorithms with predictions
            deleterious_algs: List of deleterious algorithm names
        
        Returns:
            Tuple of (applies, reasoning)
        """
        # Check minimum algorithms
        if deleterious_count < self.thresholds.min_algorithms_pp3:
            return False, (f"PP3: Insufficient algorithms ({deleterious_count} < "
                          f"{self.thresholds.min_algorithms_pp3} required)")
        
        # Check minimum total predictions
        if total_count < self.thresholds.min_total_predictions:
            return False, (f"PP3: Insufficient total predictions ({total_count} < "
                          f"{self.thresholds.min_total_predictions} required)")
        
        # Check consensus threshold
        consensus = deleterious_count / total_count if total_count > 0 else 0
        if consensus < self.thresholds.pp3_consensus_threshold:
            return False, (f"PP3: Insufficient consensus ({consensus:.1%} < "
                          f"{self.thresholds.pp3_consensus_threshold:.0%} required)")
        
        # PP3 applies
        reason = (f"PP3: {deleterious_count}/{total_count} algorithms "
                 f"({consensus:.0%}) predict deleterious effect: "
                 f"{', '.join(deleterious_algs)}")
        return True, reason
    
    def _check_bp4(
        self,
        benign_count: int,
        total_count: int,
        benign_algs: List[str]
    ) -> tuple[bool, str]:
        """Check if BP4 criteria are met.
        
        Args:
            benign_count: Number of algorithms predicting benign
            total_count: Total algorithms with predictions
            benign_algs: List of benign algorithm names
        
        Returns:
            Tuple of (applies, reasoning)
        """
        # Check minimum algorithms
        if benign_count < self.thresholds.min_algorithms_bp4:
            return False, (f"BP4: Insufficient algorithms ({benign_count} < "
                          f"{self.thresholds.min_algorithms_bp4} required)")
        
        # Check minimum total predictions
        if total_count < self.thresholds.min_total_predictions:
            return False, (f"BP4: Insufficient total predictions ({total_count} < "
                          f"{self.thresholds.min_total_predictions} required)")
        
        # Check consensus threshold
        consensus = benign_count / total_count if total_count > 0 else 0
        if consensus < self.thresholds.bp4_consensus_threshold:
            return False, (f"BP4: Insufficient consensus ({consensus:.1%} < "
                          f"{self.thresholds.bp4_consensus_threshold:.0%} required)")
        
        # BP4 applies
        reason = (f"BP4: {benign_count}/{total_count} algorithms "
                 f"({consensus:.0%}) predict benign/tolerated: "
                 f"{', '.join(benign_algs)}")
        return True, reason
    
    def analyze_predictions(
        self,
        chromosome: str,
        position: int,
        ref: str,
        alt: str
    ) -> ComputationalEvidence:
        """Analyze computational predictions for PP3/BP4 evidence.
        
        Args:
            chromosome: Chromosome (1-22, X, Y, M)
            position: Genomic position (1-based)
            ref: Reference allele
            alt: Alternate allele
        
        Returns:
            ComputationalEvidence with PP3/BP4 determination
        """
        self._queries += 1
        
        evidence = ComputationalEvidence()
        
        try:
            # Query dbNSFP if available
            predictions = None
            if self.enable_dbnsfp and self.dbnsfp_client:
                predictions = self.dbnsfp_client.get_variant_predictions(
                    chromosome, position, ref, alt
                )
            
            if predictions is None or not predictions.has_predictions:
                evidence.reasoning = "No computational predictions available"
                logger.debug(f"No predictions for {chromosome}:{position} {ref}>{alt}")
                return evidence
            
            # Count predictions
            del_count, ben_count, total_count, del_algs, ben_algs = self._count_predictions(predictions)
            
            evidence.deleterious_count = del_count
            evidence.benign_count = ben_count
            evidence.total_predictions = total_count
            evidence.deleterious_algorithms = del_algs
            evidence.benign_algorithms = ben_algs
            
            # Check PP3 (deleterious)
            pp3_applies, pp3_reason = self._check_pp3(del_count, total_count, del_algs)
            if pp3_applies:
                evidence.pp3 = True
                evidence.reasoning = pp3_reason
                self._pp3_assigned += 1
                logger.info(pp3_reason)
                return evidence
            
            # Check BP4 (benign) - only if PP3 doesn't apply
            bp4_applies, bp4_reason = self._check_bp4(ben_count, total_count, ben_algs)
            if bp4_applies:
                evidence.bp4 = True
                evidence.reasoning = bp4_reason
                self._bp4_assigned += 1
                logger.info(bp4_reason)
                return evidence
            
            # Neither applies
            evidence.reasoning = (f"Insufficient consensus: {del_count} deleterious, "
                                 f"{ben_count} benign (need {self.thresholds.min_algorithms_pp3}+)")
            logger.debug(evidence.reasoning)
            
            return evidence
            
        except Exception as e:
            logger.error(f"Computational prediction analysis failed: {e}")
            evidence.reasoning = f"Analysis error: {str(e)}"
            return evidence
    
    def get_statistics(self) -> dict:
        """Get service statistics."""
        return {
            'total_queries': self._queries,
            'pp3_assigned': self._pp3_assigned,
            'bp4_assigned': self._bp4_assigned,
            'pp3_rate': self._pp3_assigned / self._queries if self._queries > 0 else 0,
            'bp4_rate': self._bp4_assigned / self._queries if self._queries > 0 else 0,
        }


if __name__ == "__main__":
    print("="*80)
    print("Computational Prediction Service - PP3/BP4 Evidence")
    print("="*80)
    print("\nEvidence Codes:")
    print("  PP3: Multiple computational evidence support deleterious")
    print("       - Requires 4+ algorithms in agreement (75% consensus)")
    print("       - SIFT, PolyPhen-2, CADD, REVEL, MetaSVM, etc.")
    print("\n  BP4: Multiple computational evidence suggest benign")
    print("       - Requires 4+ algorithms in agreement (75% consensus)")
    print("       - Same algorithms as PP3")
    print("\nThresholds:")
    thresholds = ComputationalThresholds()
    print(f"  Min algorithms: {thresholds.min_algorithms_pp3}")
    print(f"  Consensus: {thresholds.pp3_consensus_threshold:.0%}")
    print(f"  CADD deleterious: ≥{thresholds.cadd_deleterious_threshold}")
    print(f"  REVEL pathogenic: ≥{thresholds.revel_pathogenic_threshold}")
    print("="*80)
else:
    logger.info("ComputationalPredictionService loaded - PP3/BP4 support")
