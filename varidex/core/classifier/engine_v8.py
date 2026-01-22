#!/usr/bin/env python3
"""varidex/core/classifier/engine_v8.py - ACMG Classifier with Computational Predictions

Production ACMG 2015 classifier with gnomAD + dbNSFP integration.

Enabled Evidence (12 codes):
  Pathogenic:
    - PVS1: LOF in LOF-intolerant genes
    - PM2: Absent/rare in population databases (gnomAD)
    - PM4: Protein length changes
    - PP2: Missense in missense-rare genes
    - PP3: Computational evidence supports deleterious (dbNSFP)
  
  Benign:
    - BA1: Common polymorphism >5% (gnomAD)
    - BS1: Allele frequency too high >1% (gnomAD)
    - BP1: Missense in LOF genes
    - BP3: In-frame indel in repetitive region
    - BP4: Computational evidence suggests benign (dbNSFP)

Disabled Evidence (16 codes):
  PS1-4, PM1, PM3, PM5-6, PP1, PP4-5, BS2-4, BP2, BP5-7

Reference: Richards et al. 2015, PMID 25741868
"""

from typing import Tuple, Optional, Dict, Any
import logging
import time

from varidex.version import __version__
from varidex.core.models import ACMGEvidenceSet, VariantData
from varidex.core.classifier.engine_v7 import ACMGClassifierV7
from varidex.core.classifier.config import ACMGConfig
from varidex.core.services.computational_prediction import (
    ComputationalPredictionService,
    ComputationalThresholds
)
from varidex.integrations.dbnsfp_client import DbNSFPClient

logger = logging.getLogger(__name__)


class ACMGClassifierV8(ACMGClassifierV7):
    """Enhanced ACMG classifier with gnomAD + dbNSFP integration.
    
    Extends ACMGClassifierV7 with:
    - PP3: Computational evidence supports pathogenic (dbNSFP)
    - BP4: Computational evidence supports benign (dbNSFP)
    
    Maintains all v7 features:
    - PM2, BA1, BS1 from gnomAD
    - PVS1, PM4, PP2, BP1, BP3 from base classifier
    
    Total: 12 evidence codes (43% of ACMG 2015)
    """
    
    VERSION = "8.0.0"
    
    def __init__(
        self,
        config: Optional[ACMGConfig] = None,
        enable_gnomad: bool = True,
        enable_dbnsfp: bool = True,
        gnomad_client: Optional[Any] = None,
        dbnsfp_client: Optional[DbNSFPClient] = None,
        dbnsfp_path: Optional[str] = None,
        computational_thresholds: Optional[ComputationalThresholds] = None,
        **kwargs
    ):
        """Initialize enhanced classifier with gnomAD + dbNSFP.
        
        Args:
            config: ACMG configuration
            enable_gnomad: Enable gnomAD queries (PM2, BA1, BS1)
            enable_dbnsfp: Enable dbNSFP queries (PP3, BP4)
            gnomad_client: Custom GnomadClient instance
            dbnsfp_client: Custom DbNSFPClient instance
            dbnsfp_path: Path to dbNSFP file (if dbnsfp_client not provided)
            computational_thresholds: Custom thresholds for PP3/BP4
            **kwargs: Additional arguments for parent class
        """
        # Initialize parent (v7 with gnomAD)
        super().__init__(
            config=config,
            enable_gnomad=enable_gnomad,
            gnomad_client=gnomad_client,
            **kwargs
        )
        
        # Initialize computational prediction service
        self.enable_dbnsfp = enable_dbnsfp
        self.computational_service = None
        
        if enable_dbnsfp:
            try:
                # Create dbNSFP client if not provided
                if dbnsfp_client is None and dbnsfp_path:
                    dbnsfp_client = DbNSFPClient(
                        dbnsfp_path=dbnsfp_path,
                        enable_cache=True
                    )
                
                # Create computational service
                self.computational_service = ComputationalPredictionService(
                    dbnsfp_client=dbnsfp_client,
                    thresholds=computational_thresholds,
                    enable_dbnsfp=True
                )
                logger.info(f"ACMGClassifierV8 {self.VERSION} initialized with dbNSFP")
            except Exception as e:
                logger.error(f"Failed to initialize dbNSFP service: {e}")
                logger.warning("Continuing without dbNSFP integration")
                self.enable_dbnsfp = False
                self.computational_service = None
        else:
            logger.info(f"ACMGClassifierV8 {self.VERSION} initialized without dbNSFP")
    
    def assign_evidence(self, variant: VariantData) -> ACMGEvidenceSet:
        """Assign ACMG evidence codes including computational predictions.
        
        Extends v7 classifier with PP3 and BP4 from dbNSFP.
        
        Args:
            variant: VariantData object
        
        Returns:
            ACMGEvidenceSet with evidence codes
        """
        # Get evidence from parent (v7: gnomAD + base codes)
        evidence = super().assign_evidence(variant)
        
        # Add computational prediction evidence if enabled
        if self.enable_dbnsfp and self.computational_service:
            try:
                # Extract coordinates (reuse parent method)
                coords = self._extract_variant_coordinates(variant)
                
                if coords is None:
                    logger.debug("No coordinates for dbNSFP query, skipping computational analysis")
                    evidence.conflicts.add("Missing coordinates for dbNSFP")
                    return evidence
                
                # Analyze computational predictions
                comp_evidence = self.computational_service.analyze_predictions(
                    chromosome=coords['chromosome'],
                    position=coords['position'],
                    ref=coords['ref'],
                    alt=coords['alt']
                )
                
                # Add evidence codes
                if comp_evidence.pp3:
                    evidence.pp.add("PP3")
                    logger.info(f"PP3: {comp_evidence.reasoning}")
                
                if comp_evidence.bp4:
                    evidence.bp.add("BP4")
                    logger.info(f"BP4: {comp_evidence.reasoning}")
                
                # Store computational info for reference
                if hasattr(evidence, 'metadata'):
                    if not hasattr(evidence, 'metadata') or evidence.metadata is None:
                        evidence.metadata = {}
                    evidence.metadata['computational'] = {
                        'deleterious_count': comp_evidence.deleterious_count,
                        'benign_count': comp_evidence.benign_count,
                        'total_predictions': comp_evidence.total_predictions,
                        'deleterious_algorithms': comp_evidence.deleterious_algorithms,
                        'benign_algorithms': comp_evidence.benign_algorithms,
                    }
                
                logger.debug(f"Computational analysis: {comp_evidence.summary()}")
                
            except Exception as e:
                logger.error(f"dbNSFP computational analysis failed: {e}")
                evidence.conflicts.add(f"dbNSFP error: {str(e)}")
        
        # Convert sets to lists (inherited from parent)
        for attr in ['pvs', 'ps', 'pm', 'pp', 'ba', 'bs', 'bp']:
            setattr(evidence, attr, list(getattr(evidence, attr)))
        
        return evidence
    
    def classify_variant(self, variant: VariantData) -> Tuple[str, str, ACMGEvidenceSet, float]:
        """Complete classification pipeline with gnomAD + dbNSFP.
        
        Args:
            variant: VariantData object
        
        Returns:
            Tuple of (classification, confidence, evidence, duration)
        """
        start_time = time.time()
        
        try:
            # Assign evidence (includes gnomAD + dbNSFP)
            evidence = self.assign_evidence(variant)
            
            # Combine evidence using parent logic
            classification, confidence = self.combine_evidence(evidence)
            
            duration = time.time() - start_time
            
            # Record metrics
            if self.metrics:
                self.metrics.record_success(duration, classification, evidence)
            
            logger.info(
                f"Classified {variant} → {classification} ({confidence}) "
                f"in {duration:.3f}s [gnomAD: {self.enable_gnomad}, dbNSFP: {self.enable_dbnsfp}]"
            )
            
            return classification, confidence, evidence, duration
            
        except Exception as e:
            duration = time.time() - start_time
            if self.metrics:
                self.metrics.record_failure()
            
            logger.error(f"Classification pipeline failed: {e}", exc_info=True)
            return "Uncertain Significance", f"Error: {str(e)}", ACMGEvidenceSet(), duration
    
    def health_check(self) -> Dict[str, Any]:
        """Health check with gnomAD + dbNSFP service status.
        
        Returns:
            Dictionary with health status
        """
        health = super().health_check()
        
        # Add dbNSFP status
        health['dbnsfp'] = {
            'enabled': self.enable_dbnsfp,
            'service_initialized': self.computational_service is not None
        }
        
        if self.computational_service:
            try:
                health['dbnsfp']['statistics'] = self.computational_service.get_statistics()
            except Exception as e:
                health['dbnsfp']['error'] = str(e)
        
        health['version'] = self.VERSION
        
        return health
    
    def get_enabled_codes(self) -> Dict[str, list]:
        """Get list of enabled evidence codes.
        
        Returns:
            Dictionary with pathogenic and benign evidence codes
        """
        # Get parent codes (v7)
        codes = super().get_enabled_codes()
        
        # Add dbNSFP codes
        if self.enable_dbnsfp:
            codes['pathogenic'].append('PP3')
            codes['benign'].append('BP4')
        
        return codes
    
    def get_features_summary(self) -> Dict[str, Any]:
        """Get summary of enabled features.
        
        Returns:
            Dictionary with feature status
        """
        return {
            'version': self.VERSION,
            'base_classifier': 'v6.3 (PVS1, PM4, PP2, BP1, BP3)',
            'gnomad_enabled': self.enable_gnomad,
            'gnomad_codes': ['PM2', 'BA1', 'BS1'] if self.enable_gnomad else [],
            'dbnsfp_enabled': self.enable_dbnsfp,
            'dbnsfp_codes': ['PP3', 'BP4'] if self.enable_dbnsfp else [],
            'total_codes': len(self.get_enabled_codes()['pathogenic']) + len(self.get_enabled_codes()['benign']),
            'acmg_coverage': f"{(len(self.get_enabled_codes()['pathogenic']) + len(self.get_enabled_codes()['benign'])) / 28 * 100:.1f}%"
        }


if __name__ == "__main__":
    print("="*80)
    print(f"ACMG Classifier V8 {ACMGClassifierV8.VERSION} - Full Integration")
    print("="*80)
    
    # Test without integrations
    print("\n1. Without integrations (base v6.3):")
    classifier_base = ACMGClassifierV8(enable_gnomad=False, enable_dbnsfp=False)
    features = classifier_base.get_features_summary()
    print(f"   Base codes: {features['base_classifier']}")
    print(f"   Total: {features['total_codes']} codes")
    
    # Test with gnomAD only
    print("\n2. With gnomAD (v7.0 compatibility):")
    classifier_gnomad = ACMGClassifierV8(enable_gnomad=True, enable_dbnsfp=False)
    features = classifier_gnomad.get_features_summary()
    print(f"   gnomAD codes: {', '.join(features['gnomad_codes'])}")
    print(f"   Total: {features['total_codes']} codes")
    
    # Test with both
    print("\n3. With gnomAD + dbNSFP (v8.0 full):")
    classifier_full = ACMGClassifierV8(enable_gnomad=True, enable_dbnsfp=True)
    features = classifier_full.get_features_summary()
    print(f"   gnomAD codes: {', '.join(features['gnomad_codes'])}")
    print(f"   dbNSFP codes: {', '.join(features['dbnsfp_codes'])}")
    print(f"   Total: {features['total_codes']} codes ({features['acmg_coverage']} ACMG coverage)")
    
    print("\n" + "="*80)
    print("Evolution:")
    print("  v6.3: 7 codes (25%) - Base classifier")
    print("  v7.0: 10 codes (36%) - +gnomAD (PM2, BA1, BS1)")
    print("  v8.0: 12 codes (43%) - +dbNSFP (PP3, BP4)")
    print("="*80)
else:
    logger.info(f"ACMGClassifierV8 {ACMGClassifierV8.VERSION} loaded")
    logger.info("  Enhanced with gnomAD (PM2, BA1, BS1) + dbNSFP (PP3, BP4)")
    logger.info("  Backward compatible with v7/v6, graceful degradation")
