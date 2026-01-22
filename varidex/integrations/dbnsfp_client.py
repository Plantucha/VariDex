#!/usr/bin/env python3
"""varidex/integrations/dbnsfp_client.py - dbNSFP Database Client

Client for querying dbNSFP (database of Non-Synonymous Functional Predictions).
Supports computational prediction scores for variant interpretation.

dbNSFP aggregates:
- SIFT: Deleteriousness prediction
- PolyPhen-2: Functional impact (HDIV, HVAR)
- CADD: Combined Annotation Dependent Depletion
- REVEL: Rare Exome Variant Ensemble Learner
- MetaSVM/MetaLR: Ensemble predictors
- MutationTaster: Disease-causing potential
- FATHMM: Functional analysis through hidden Markov models

Reference: Liu et al. 2020, dbNSFP v4.0+
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from functools import lru_cache
import logging
import os

logger = logging.getLogger(__name__)


@dataclass
class PredictionScore:
    """Single algorithm prediction score."""
    
    algorithm: str
    score: Optional[float] = None
    prediction: Optional[str] = None  # e.g., "D" (deleterious), "T" (tolerated)
    raw_value: Optional[str] = None
    
    @property
    def is_deleterious(self) -> bool:
        """Check if prediction suggests deleteriousness."""
        if self.prediction:
            pred_lower = self.prediction.lower()
            return any([
                pred_lower in ['d', 'deleterious', 'damaging', 'disease_causing'],
                'probably' in pred_lower and 'damaging' in pred_lower,
                'possibly' in pred_lower and 'damaging' in pred_lower,
            ])
        return False
    
    @property
    def is_benign(self) -> bool:
        """Check if prediction suggests benign/tolerated."""
        if self.prediction:
            pred_lower = self.prediction.lower()
            return any([
                pred_lower in ['t', 'tolerated', 'benign', 'neutral', 'polymorphism'],
                'probably' in pred_lower and 'benign' in pred_lower,
            ])
        return False


@dataclass
class DbNSFPVariantPredictions:
    """Aggregated computational predictions for a variant."""
    
    variant_id: str
    chromosome: str
    position: int
    ref: str
    alt: str
    
    # Individual algorithm scores
    sift_score: Optional[float] = None
    sift_pred: Optional[str] = None
    
    polyphen2_hdiv_score: Optional[float] = None
    polyphen2_hdiv_pred: Optional[str] = None
    
    polyphen2_hvar_score: Optional[float] = None
    polyphen2_hvar_pred: Optional[str] = None
    
    cadd_phred: Optional[float] = None
    
    revel_score: Optional[float] = None
    
    metasvm_score: Optional[float] = None
    metasvm_pred: Optional[str] = None
    
    metalr_score: Optional[float] = None
    metalr_pred: Optional[str] = None
    
    mutationtaster_score: Optional[float] = None
    mutationtaster_pred: Optional[str] = None
    
    # Aggregated counts
    scores: Dict[str, PredictionScore] = field(default_factory=dict)
    
    def count_deleterious(self) -> int:
        """Count algorithms predicting deleterious effect."""
        count = 0
        
        if self.sift_pred and 'D' in self.sift_pred.upper():
            count += 1
        if self.polyphen2_hdiv_pred and 'D' in self.polyphen2_hdiv_pred.upper():
            count += 1
        if self.polyphen2_hvar_pred and 'D' in self.polyphen2_hvar_pred.upper():
            count += 1
        if self.metasvm_pred and 'D' in self.metasvm_pred.upper():
            count += 1
        if self.metalr_pred and 'D' in self.metalr_pred.upper():
            count += 1
        if self.mutationtaster_pred and 'D' in self.mutationtaster_pred.upper():
            count += 1
        
        # Score-based thresholds
        if self.cadd_phred and self.cadd_phred >= 20:  # CADD > 20 is deleterious
            count += 1
        if self.revel_score and self.revel_score >= 0.5:  # REVEL > 0.5 is pathogenic
            count += 1
        
        return count
    
    def count_benign(self) -> int:
        """Count algorithms predicting benign/tolerated effect."""
        count = 0
        
        if self.sift_pred and 'T' in self.sift_pred.upper():
            count += 1
        if self.polyphen2_hdiv_pred and 'B' in self.polyphen2_hdiv_pred.upper():
            count += 1
        if self.polyphen2_hvar_pred and 'B' in self.polyphen2_hvar_pred.upper():
            count += 1
        if self.metasvm_pred and 'T' in self.metasvm_pred.upper():
            count += 1
        if self.metalr_pred and 'T' in self.metalr_pred.upper():
            count += 1
        if self.mutationtaster_pred and ('N' in self.mutationtaster_pred.upper() or 
                                          'P' in self.mutationtaster_pred.upper()):
            count += 1
        
        # Score-based thresholds
        if self.cadd_phred and self.cadd_phred < 10:  # CADD < 10 is likely benign
            count += 1
        if self.revel_score and self.revel_score < 0.3:  # REVEL < 0.3 is likely benign
            count += 1
        
        return count
    
    @property
    def has_predictions(self) -> bool:
        """Check if any predictions are available."""
        return any([
            self.sift_score is not None,
            self.polyphen2_hdiv_score is not None,
            self.polyphen2_hvar_score is not None,
            self.cadd_phred is not None,
            self.revel_score is not None,
            self.metasvm_score is not None,
            self.metalr_score is not None,
            self.mutationtaster_score is not None,
        ])


class DbNSFPClient:
    """Client for querying dbNSFP database.
    
    Supports:
    - Local tabix-indexed files (preferred for production)
    - In-memory caching
    - Multiple query methods
    
    Usage:
        client = DbNSFPClient(dbnsfp_path="/path/to/dbNSFP4.5a.gz")
        predictions = client.get_variant_predictions("17", 43094692, "G", "A")
    """
    
    def __init__(
        self,
        dbnsfp_path: Optional[str] = None,
        enable_cache: bool = True,
        cache_expiry_hours: int = 24,
        use_tabix: bool = True
    ):
        """Initialize dbNSFP client.
        
        Args:
            dbnsfp_path: Path to dbNSFP tabix-indexed file
            enable_cache: Enable in-memory caching
            cache_expiry_hours: Cache expiry time
            use_tabix: Use tabix for queries (requires pysam)
        """
        self.dbnsfp_path = dbnsfp_path
        self.enable_cache = enable_cache
        self.cache_expiry = timedelta(hours=cache_expiry_hours)
        self.use_tabix = use_tabix
        
        # Initialize cache
        self._cache: Dict[str, tuple[DbNSFPVariantPredictions, datetime]] = {}
        
        # Check if tabix file exists
        if self.dbnsfp_path and not os.path.exists(self.dbnsfp_path):
            logger.warning(f"dbNSFP file not found: {self.dbnsfp_path}")
            self.dbnsfp_path = None
        
        # Try to import pysam for tabix
        self.tabix = None
        if self.use_tabix and self.dbnsfp_path:
            try:
                import pysam
                self.tabix = pysam.TabixFile(self.dbnsfp_path)
                logger.info(f"dbNSFP client initialized with tabix: {self.dbnsfp_path}")
            except ImportError:
                logger.warning("pysam not available, tabix queries disabled")
                self.use_tabix = False
            except Exception as e:
                logger.error(f"Failed to open tabix file: {e}")
                self.use_tabix = False
    
    def _build_cache_key(self, chromosome: str, position: int, ref: str, alt: str) -> str:
        """Build cache key for variant."""
        return f"{chromosome}-{position}-{ref}-{alt}"
    
    def _get_from_cache(self, cache_key: str) -> Optional[DbNSFPVariantPredictions]:
        """Retrieve predictions from cache if valid."""
        if not self.enable_cache:
            return None
        
        if cache_key in self._cache:
            predictions, timestamp = self._cache[cache_key]
            if datetime.now() - timestamp < self.cache_expiry:
                logger.debug(f"Cache hit: {cache_key}")
                return predictions
            else:
                del self._cache[cache_key]
        
        return None
    
    def _add_to_cache(self, cache_key: str, predictions: DbNSFPVariantPredictions) -> None:
        """Add predictions to cache."""
        if self.enable_cache:
            self._cache[cache_key] = (predictions, datetime.now())
    
    def clear_cache(self) -> None:
        """Clear prediction cache."""
        self._cache.clear()
        logger.info("dbNSFP cache cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            'size': len(self._cache),
            'enabled': self.enable_cache
        }
    
    def _parse_tabix_record(self, record: str, ref: str, alt: str) -> Optional[DbNSFPVariantPredictions]:
        """Parse a tabix record from dbNSFP."""
        try:
            fields = record.strip().split('\t')
            
            # dbNSFP v4 column indices (approximate, may vary by version)
            # User should verify column positions for their dbNSFP version
            predictions = DbNSFPVariantPredictions(
                variant_id=f"{fields[0]}-{fields[1]}-{ref}-{alt}",
                chromosome=fields[0],
                position=int(fields[1]),
                ref=ref,
                alt=alt
            )
            
            # Parse prediction scores (column indices are examples)
            # Adjust based on actual dbNSFP version
            def safe_float(value: str) -> Optional[float]:
                try:
                    if value and value != '.' and value != 'NA':
                        return float(value)
                except (ValueError, TypeError):
                    pass
                return None
            
            def safe_str(value: str) -> Optional[str]:
                if value and value != '.' and value != 'NA':
                    return value
                return None
            
            # Example parsing (adjust column indices for your dbNSFP version)
            if len(fields) > 20:
                predictions.sift_score = safe_float(fields[6] if len(fields) > 6 else None)
                predictions.sift_pred = safe_str(fields[7] if len(fields) > 7 else None)
                predictions.polyphen2_hdiv_score = safe_float(fields[8] if len(fields) > 8 else None)
                predictions.polyphen2_hdiv_pred = safe_str(fields[9] if len(fields) > 9 else None)
                predictions.cadd_phred = safe_float(fields[10] if len(fields) > 10 else None)
            
            return predictions
            
        except Exception as e:
            logger.error(f"Failed to parse tabix record: {e}")
            return None
    
    def get_variant_predictions(
        self,
        chromosome: str,
        position: int,
        ref: str,
        alt: str
    ) -> Optional[DbNSFPVariantPredictions]:
        """Query dbNSFP for variant predictions.
        
        Args:
            chromosome: Chromosome (1-22, X, Y, M)
            position: Genomic position (1-based)
            ref: Reference allele
            alt: Alternate allele
        
        Returns:
            DbNSFPVariantPredictions or None if not found
        """
        try:
            # Normalize chromosome
            chrom = str(chromosome).replace('chr', '')
            
            # Check cache
            cache_key = self._build_cache_key(chrom, position, ref, alt)
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                return cached
            
            # Query using tabix
            if self.tabix:
                try:
                    region = f"{chrom}:{position}-{position}"
                    records = list(self.tabix.fetch(region))
                    
                    if records:
                        # Parse first matching record
                        predictions = self._parse_tabix_record(records[0], ref, alt)
                        if predictions:
                            self._add_to_cache(cache_key, predictions)
                            return predictions
                except Exception as e:
                    logger.error(f"Tabix query failed: {e}")
            
            # No predictions found
            logger.debug(f"No dbNSFP predictions for {chrom}:{position} {ref}>{alt}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get variant predictions: {e}")
            return None
    
    def close(self) -> None:
        """Close tabix file handle."""
        if self.tabix:
            self.tabix.close()
            self.tabix = None


if __name__ == "__main__":
    print("="*80)
    print("dbNSFP Client - Computational Prediction Integration")
    print("="*80)
    print("\nSupported Algorithms:")
    algorithms = [
        "SIFT: Deleteriousness prediction",
        "PolyPhen-2: Functional impact (HDIV, HVAR)",
        "CADD: Combined annotation score",
        "REVEL: Ensemble predictor",
        "MetaSVM/MetaLR: Meta-predictors",
        "MutationTaster: Disease-causing potential",
    ]
    for alg in algorithms:
        print(f"  • {alg}")
    print("\nUsage:")
    print("  client = DbNSFPClient(dbnsfp_path='/path/to/dbNSFP.gz')")
    print("  predictions = client.get_variant_predictions('17', 43094692, 'G', 'A')")
    print("="*80)
else:
    logger.info("DbNSFPClient loaded - computational prediction support")
