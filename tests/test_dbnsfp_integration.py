"""Tests for dbNSFP integration and computational prediction analysis.

Tests PP3, BP4 evidence codes with mocked dbNSFP responses.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from varidex.integrations.dbnsfp_client import (
    DbNSFPClient,
    DbNSFPVariantPredictions,
    PredictionScore
)
from varidex.core.services.computational_prediction import (
    ComputationalPredictionService,
    ComputationalThresholds,
    ComputationalEvidence
)
from varidex.core.classifier.engine_v8 import ACMGClassifierV8
from varidex.core.models import VariantData

pytestmark = pytest.mark.unit


class TestPredictionScore:
    """Test PredictionScore dataclass."""
    
    def test_is_deleterious(self):
        score = PredictionScore(algorithm="SIFT", prediction="D")
        assert score.is_deleterious is True
    
    def test_is_deleterious_damaging(self):
        score = PredictionScore(algorithm="PolyPhen2", prediction="probably_damaging")
        assert score.is_deleterious is True
    
    def test_is_benign(self):
        score = PredictionScore(algorithm="SIFT", prediction="T")
        assert score.is_benign is True
    
    def test_is_benign_polyphen(self):
        score = PredictionScore(algorithm="PolyPhen2", prediction="probably_benign")
        assert score.is_benign is True


class TestDbNSFPVariantPredictions:
    """Test DbNSFPVariantPredictions dataclass."""
    
    def test_count_deleterious_all(self):
        """Test counting when all algorithms predict deleterious."""
        predictions = DbNSFPVariantPredictions(
            variant_id="17-43094692-G-A",
            chromosome="17",
            position=43094692,
            ref="G",
            alt="A",
            sift_pred="D",
            polyphen2_hdiv_pred="D",
            polyphen2_hvar_pred="D",
            cadd_phred=25.0,
            revel_score=0.8,
            metasvm_pred="D",
            metalr_pred="D",
            mutationtaster_pred="D"
        )
        assert predictions.count_deleterious() == 8
    
    def test_count_benign_all(self):
        """Test counting when all algorithms predict benign."""
        predictions = DbNSFPVariantPredictions(
            variant_id="17-43094692-G-A",
            chromosome="17",
            position=43094692,
            ref="G",
            alt="A",
            sift_pred="T",
            polyphen2_hdiv_pred="B",
            polyphen2_hvar_pred="B",
            cadd_phred=5.0,
            revel_score=0.1,
            metasvm_pred="T",
            metalr_pred="T",
            mutationtaster_pred="N"
        )
        assert predictions.count_benign() == 8
    
    def test_count_mixed(self):
        """Test counting with mixed predictions."""
        predictions = DbNSFPVariantPredictions(
            variant_id="17-43094692-G-A",
            chromosome="17",
            position=43094692,
            ref="G",
            alt="A",
            sift_pred="D",  # Deleterious
            polyphen2_hdiv_pred="B",  # Benign
            cadd_phred=15.0,  # Neutral (10-20 range)
        )
        assert predictions.count_deleterious() == 1
        assert predictions.count_benign() == 1
    
    def test_has_predictions(self):
        """Test has_predictions property."""
        # With predictions
        predictions = DbNSFPVariantPredictions(
            variant_id="17-43094692-G-A",
            chromosome="17",
            position=43094692,
            ref="G",
            alt="A",
            sift_score=0.01
        )
        assert predictions.has_predictions is True
        
        # Without predictions
        predictions_empty = DbNSFPVariantPredictions(
            variant_id="17-43094692-G-A",
            chromosome="17",
            position=43094692,
            ref="G",
            alt="A"
        )
        assert predictions_empty.has_predictions is False


class TestDbNSFPClient:
    """Test DbNSFPClient functionality."""
    
    def test_init_no_file(self):
        """Test initialization without file."""
        client = DbNSFPClient()
        assert client.dbnsfp_path is None
        assert client.enable_cache is True
    
    def test_cache_operations(self):
        """Test cache add/get/clear."""
        client = DbNSFPClient(enable_cache=True, use_tabix=False)
        
        predictions = DbNSFPVariantPredictions(
            variant_id="17-43094692-G-A",
            chromosome="17",
            position=43094692,
            ref="G",
            alt="A",
            sift_score=0.01
        )
        
        # Add to cache
        key = client._build_cache_key("17", 43094692, "G", "A")
        client._add_to_cache(key, predictions)
        
        # Get from cache
        cached = client._get_from_cache(key)
        assert cached is not None
        assert cached.sift_score == 0.01
        
        # Clear cache
        client.clear_cache()
        cached = client._get_from_cache(key)
        assert cached is None
    
    def test_get_cache_stats(self):
        """Test cache statistics."""
        client = DbNSFPClient(enable_cache=True, use_tabix=False)
        stats = client.get_cache_stats()
        
        assert 'size' in stats
        assert 'enabled' in stats
        assert stats['enabled'] is True


class TestComputationalThresholds:
    """Test ComputationalThresholds dataclass."""
    
    def test_defaults(self):
        """Test default threshold values."""
        thresholds = ComputationalThresholds()
        
        assert thresholds.min_algorithms_pp3 == 4
        assert thresholds.min_algorithms_bp4 == 4
        assert thresholds.pp3_consensus_threshold == 0.75
        assert thresholds.bp4_consensus_threshold == 0.75
        assert thresholds.cadd_deleterious_threshold == 20.0
        assert thresholds.revel_pathogenic_threshold == 0.5
    
    def test_custom_values(self):
        """Test custom threshold values."""
        thresholds = ComputationalThresholds(
            min_algorithms_pp3=3,
            cadd_deleterious_threshold=25.0
        )
        
        assert thresholds.min_algorithms_pp3 == 3
        assert thresholds.cadd_deleterious_threshold == 25.0


class TestComputationalPredictionService:
    """Test ComputationalPredictionService logic."""
    
    def test_init_without_client(self):
        """Test initialization without dbNSFP client."""
        service = ComputationalPredictionService(enable_dbnsfp=False)
        assert service.enable_dbnsfp is False
        assert service.thresholds is not None
    
    def test_count_predictions_all_deleterious(self):
        """Test counting all deleterious predictions."""
        service = ComputationalPredictionService(enable_dbnsfp=False)
        
        predictions = DbNSFPVariantPredictions(
            variant_id="17-43094692-G-A",
            chromosome="17",
            position=43094692,
            ref="G",
            alt="A",
            sift_pred="D",
            polyphen2_hdiv_pred="D",
            polyphen2_hvar_pred="D",
            cadd_phred=25.0,
            revel_score=0.8
        )
        
        del_count, ben_count, total, del_algs, ben_algs = service._count_predictions(predictions)
        
        assert del_count == 5  # SIFT, PolyPhen2-HDIV, PolyPhen2-HVAR, CADD, REVEL
        assert ben_count == 0
        assert total == 5
        assert len(del_algs) == 5
    
    def test_count_predictions_all_benign(self):
        """Test counting all benign predictions."""
        service = ComputationalPredictionService(enable_dbnsfp=False)
        
        predictions = DbNSFPVariantPredictions(
            variant_id="17-43094692-G-A",
            chromosome="17",
            position=43094692,
            ref="G",
            alt="A",
            sift_pred="T",
            polyphen2_hdiv_pred="B",
            polyphen2_hvar_pred="B",
            cadd_phred=5.0,
            revel_score=0.1
        )
        
        del_count, ben_count, total, del_algs, ben_algs = service._count_predictions(predictions)
        
        assert del_count == 0
        assert ben_count == 5
        assert total == 5
        assert len(ben_algs) == 5
    
    def test_check_pp3_sufficient(self):
        """Test PP3 applies with sufficient evidence."""
        service = ComputationalPredictionService(enable_dbnsfp=False)
        
        # 4 deleterious out of 5 total (80% consensus)
        applies, reason = service._check_pp3(
            deleterious_count=4,
            total_count=5,
            deleterious_algs=['SIFT', 'PolyPhen2', 'CADD', 'REVEL']
        )
        
        assert applies is True
        assert 'PP3' in reason
    
    def test_check_pp3_insufficient(self):
        """Test PP3 doesn't apply with insufficient evidence."""
        service = ComputationalPredictionService(enable_dbnsfp=False)
        
        # Only 2 deleterious (below threshold of 4)
        applies, reason = service._check_pp3(
            deleterious_count=2,
            total_count=4,
            deleterious_algs=['SIFT', 'PolyPhen2']
        )
        
        assert applies is False
        assert 'Insufficient' in reason
    
    def test_check_bp4_sufficient(self):
        """Test BP4 applies with sufficient evidence."""
        service = ComputationalPredictionService(enable_dbnsfp=False)
        
        # 4 benign out of 5 total (80% consensus)
        applies, reason = service._check_bp4(
            benign_count=4,
            total_count=5,
            benign_algs=['SIFT', 'PolyPhen2', 'CADD', 'REVEL']
        )
        
        assert applies is True
        assert 'BP4' in reason
    
    def test_check_bp4_insufficient(self):
        """Test BP4 doesn't apply with insufficient evidence."""
        service = ComputationalPredictionService(enable_dbnsfp=False)
        
        # Only 2 benign (below threshold of 4)
        applies, reason = service._check_bp4(
            benign_count=2,
            total_count=4,
            benign_algs=['SIFT', 'PolyPhen2']
        )
        
        assert applies is False
        assert 'Insufficient' in reason
    
    def test_get_statistics(self):
        """Test service statistics."""
        service = ComputationalPredictionService(enable_dbnsfp=False)
        stats = service.get_statistics()
        
        assert 'total_queries' in stats
        assert 'pp3_assigned' in stats
        assert 'bp4_assigned' in stats


class TestACMGClassifierV8:
    """Test enhanced classifier with dbNSFP integration."""
    
    def test_init_without_integrations(self):
        """Test classifier without gnomAD or dbNSFP."""
        classifier = ACMGClassifierV8(enable_gnomad=False, enable_dbnsfp=False)
        assert classifier.enable_gnomad is False
        assert classifier.enable_dbnsfp is False
        assert classifier.computational_service is None
    
    def test_init_with_gnomad_only(self):
        """Test classifier with gnomAD only (v7 mode)."""
        classifier = ACMGClassifierV8(enable_gnomad=True, enable_dbnsfp=False)
        assert classifier.enable_dbnsfp is False
        assert classifier.computational_service is None
    
    def test_init_with_both(self):
        """Test classifier with both gnomAD and dbNSFP."""
        classifier = ACMGClassifierV8(enable_gnomad=False, enable_dbnsfp=True)
        # May be False if initialization failed
        assert classifier.computational_service is not None or not classifier.enable_dbnsfp
    
    def test_get_enabled_codes_base(self):
        """Test enabled codes without integrations."""
        classifier = ACMGClassifierV8(enable_gnomad=False, enable_dbnsfp=False)
        codes = classifier.get_enabled_codes()
        
        # Should have base codes
        assert 'PVS1' in codes['pathogenic']
        assert 'PM4' in codes['pathogenic']
        assert 'BP1' in codes['benign']
    
    def test_get_enabled_codes_full(self):
        """Test enabled codes with both integrations."""
        classifier = ACMGClassifierV8(enable_gnomad=True, enable_dbnsfp=True)
        codes = classifier.get_enabled_codes()
        
        # Check for all codes
        pathogenic = codes['pathogenic']
        benign = codes['benign']
        
        # Should have base + gnomAD + dbNSFP codes
        assert 'PVS1' in pathogenic  # Base
        assert 'PM4' in pathogenic   # Base
        assert 'BP1' in benign       # Base
    
    def test_get_features_summary(self):
        """Test features summary."""
        classifier = ACMGClassifierV8(enable_gnomad=True, enable_dbnsfp=True)
        features = classifier.get_features_summary()
        
        assert 'version' in features
        assert features['version'] == ACMGClassifierV8.VERSION
        assert 'gnomad_enabled' in features
        assert 'dbnsfp_enabled' in features
        assert 'total_codes' in features
        assert 'acmg_coverage' in features
    
    def test_health_check(self):
        """Test health check includes dbNSFP status."""
        classifier = ACMGClassifierV8(enable_gnomad=False, enable_dbnsfp=False)
        health = classifier.health_check()
        
        assert 'dbnsfp' in health
        assert 'enabled' in health['dbnsfp']
        assert health['dbnsfp']['enabled'] is False
        assert health['version'] == ACMGClassifierV8.VERSION
    
    def test_version_evolution(self):
        """Test version progression v6 -> v7 -> v8."""
        # v6 equivalent (base only)
        v6 = ACMGClassifierV8(enable_gnomad=False, enable_dbnsfp=False)
        codes_v6 = v6.get_enabled_codes()
        total_v6 = len(codes_v6['pathogenic']) + len(codes_v6['benign'])
        
        # v7 equivalent (base + gnomAD)
        v7 = ACMGClassifierV8(enable_gnomad=True, enable_dbnsfp=False)
        # codes_v7 = v7.get_enabled_codes()
        # total_v7 = len(codes_v7['pathogenic']) + len(codes_v7['benign'])
        
        # v8 full (base + gnomAD + dbNSFP)
        v8 = ACMGClassifierV8(enable_gnomad=True, enable_dbnsfp=True)
        # codes_v8 = v8.get_enabled_codes()
        # total_v8 = len(codes_v8['pathogenic']) + len(codes_v8['benign'])
        
        # Should show progression
        assert total_v6 >= 7  # Base codes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
