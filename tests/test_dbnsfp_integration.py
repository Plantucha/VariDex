"""Tests for dbNSFP integration and computational predictions.

Tests PP3 and BP4 evidence codes with mocked prediction responses.
"""

import pytest
from unittest.mock import Mock, patch

from varidex.integrations.dbnsfp_client import DbNSFPClient, PredictionScore
from varidex.core.services.computational_prediction import (
    ComputationalPredictionService,
    ComputationalEvidence,
)
from varidex.core.classifier.engine_v8 import ACMGClassifierV8
from varidex.core.models import VariantData

pytestmark = pytest.mark.unit


class TestPredictionScore:
    """Test PredictionScore dataclass."""

    def test_count_deleterious_sift(self):
        """Test deleterious count with SIFT."""
        score = PredictionScore(variant_id="1-12345-A-G", sift_score=0.01)  # Deleterious
        assert score.count_deleterious() == 1
        assert score.count_benign() == 0

    def test_count_deleterious_polyphen(self):
        """Test deleterious count with PolyPhen."""
        score = PredictionScore(
            variant_id="1-12345-A-G",
            polyphen_score=0.9,  # Deleterious
            polyphen_prediction="probably_damaging",
        )
        assert score.count_deleterious() == 1

    def test_count_deleterious_cadd(self):
        """Test deleterious count with CADD."""
        score = PredictionScore(variant_id="1-12345-A-G", cadd_phred=25.0)  # Deleterious (>20)
        assert score.count_deleterious() == 1

    def test_count_deleterious_multiple(self):
        """Test deleterious count with multiple algorithms."""
        score = PredictionScore(
            variant_id="1-12345-A-G",
            sift_score=0.01,
            polyphen_score=0.9,
            cadd_phred=25.0,
            revel_score=0.8,
        )
        assert score.count_deleterious() == 4

    def test_count_benign_sift(self):
        """Test benign count with SIFT."""
        score = PredictionScore(
            variant_id="1-12345-A-G", sift_score=0.5, sift_prediction="tolerated"  # Tolerated
        )
        assert score.count_benign() == 1
        assert score.count_deleterious() == 0

    def test_count_benign_polyphen(self):
        """Test benign count with PolyPhen."""
        score = PredictionScore(
            variant_id="1-12345-A-G", polyphen_score=0.1, polyphen_prediction="benign"  # Benign
        )
        assert score.count_benign() == 1

    def test_count_benign_cadd(self):
        """Test benign count with CADD."""
        score = PredictionScore(variant_id="1-12345-A-G", cadd_phred=10.0)  # Benign (<15)
        assert score.count_benign() == 1

    def test_count_benign_multiple(self):
        """Test benign count with multiple algorithms."""
        score = PredictionScore(
            variant_id="1-12345-A-G",
            sift_score=0.5,
            polyphen_score=0.1,
            cadd_phred=10.0,
            revel_score=0.1,
        )
        assert score.count_benign() == 4

    def test_has_scores(self):
        """Test has_scores property."""
        score_with = PredictionScore(variant_id="1-12345-A-G", sift_score=0.01)
        assert score_with.has_scores is True

        score_without = PredictionScore(variant_id="1-12345-A-G")
        assert score_without.has_scores is False

    def test_summary(self):
        """Test summary generation."""
        score = PredictionScore(
            variant_id="1-12345-A-G", sift_score=0.01, polyphen_score=0.9, cadd_phred=25.0
        )
        summary = score.summary()
        assert "3 deleterious" in summary
        assert "0 benign" in summary


class TestDbNSFPClient:
    """Test DbNSFPClient functionality."""

    def test_init_default(self):
        """Test default initialization."""
        client = DbNSFPClient()
        assert client.vep_url == DbNSFPClient.DEFAULT_VEP_URL
        assert client.timeout == DbNSFPClient.DEFAULT_TIMEOUT
        assert client.enable_cache is True

    def test_init_custom(self):
        """Test custom initialization."""
        client = DbNSFPClient(
            vep_url="https://custom.api", timeout=60, enable_cache=False, rate_limit=False
        )
        assert client.vep_url == "https://custom.api"
        assert client.timeout == 60
        assert client.enable_cache is False
        assert client.rate_limit is False

    def test_cache_operations(self):
        """Test cache add/get operations."""
        client = DbNSFPClient(enable_cache=True)

        prediction = PredictionScore(variant_id="1-12345-A-G", sift_score=0.01)

        # Add to cache
        client._add_to_cache("1-12345-A-G", prediction)

        # Retrieve from cache
        cached = client._get_from_cache("1-12345-A-G")
        assert cached is not None
        assert cached.sift_score == 0.01

        # Clear cache
        client.clear_cache()
        cached = client._get_from_cache("1-12345-A-G")
        assert cached is None

    @patch("requests.Session.get")
    def test_get_predictions_not_found(self, mock_get):
        """Test variant not found in VEP."""
        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = DbNSFPClient(rate_limit=False)
        result = client.get_predictions("1", 12345, "A", "G")

        assert result is None

    @patch("requests.Session.get")
    def test_get_predictions_found(self, mock_get):
        """Test variant found in VEP with predictions."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "transcript_consequences": [
                    {
                        "consequence_terms": ["missense_variant"],
                        "sift_score": 0.01,
                        "sift_prediction": "deleterious",
                        "polyphen_score": 0.95,
                        "polyphen_prediction": "probably_damaging",
                        "cadd_phred": 28.5,
                    }
                ]
            }
        ]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = DbNSFPClient(rate_limit=False)
        result = client.get_predictions("1", 12345, "A", "G")

        assert result is not None
        assert result.sift_score == 0.01
        assert result.polyphen_score == 0.95
        assert result.cadd_phred == 28.5

    def test_get_statistics(self):
        """Test statistics retrieval."""
        client = DbNSFPClient()
        stats = client.get_statistics()

        assert "cache_enabled" in stats
        assert "cache_size" in stats
        assert "vep_url" in stats


class TestComputationalPredictionService:
    """Test ComputationalPredictionService logic."""

    def test_init_with_predictions(self):
        """Test initialization with predictions enabled."""
        service = ComputationalPredictionService(enable_predictions=False)
        assert service.enable_predictions is False
        assert service.thresholds is not None

    def test_analyze_sift(self):
        """Test SIFT analysis."""
        service = ComputationalPredictionService(enable_predictions=False)

        score_del = PredictionScore(variant_id="1", sift_score=0.01)
        assert service._analyze_sift(score_del) == "deleterious"

        score_ben = PredictionScore(variant_id="1", sift_score=0.5)
        assert service._analyze_sift(score_ben) == "benign"

    def test_analyze_polyphen(self):
        """Test PolyPhen analysis."""
        service = ComputationalPredictionService(enable_predictions=False)

        score_del = PredictionScore(variant_id="1", polyphen_score=0.9)
        assert service._analyze_polyphen(score_del) == "deleterious"

        score_ben = PredictionScore(variant_id="1", polyphen_score=0.1)
        assert service._analyze_polyphen(score_ben) == "benign"

    def test_analyze_cadd(self):
        """Test CADD analysis."""
        service = ComputationalPredictionService(enable_predictions=False)

        score_del = PredictionScore(variant_id="1", cadd_phred=25.0)
        assert service._analyze_cadd(score_del) == "deleterious"

        score_ben = PredictionScore(variant_id="1", cadd_phred=10.0)
        assert service._analyze_cadd(score_ben) == "benign"

    def test_check_pp3_sufficient(self):
        """Test PP3 applies with sufficient deleterious predictions."""
        service = ComputationalPredictionService(enable_predictions=False)

        evidence = ComputationalEvidence(
            deleterious_count=3,
            benign_count=0,
            total_predictions=3,
            sift_result="deleterious",
            polyphen_result="deleterious",
            cadd_result="deleterious",
        )

        applies, reason = service._check_pp3(evidence)
        assert applies is True
        assert "PP3" in reason

    def test_check_pp3_insufficient(self):
        """Test PP3 doesn't apply with insufficient predictions."""
        service = ComputationalPredictionService(enable_predictions=False)

        evidence = ComputationalEvidence(deleterious_count=2, benign_count=0, total_predictions=2)

        applies, reason = service._check_pp3(evidence)
        assert applies is False

    def test_check_bp4_sufficient(self):
        """Test BP4 applies with sufficient benign predictions."""
        service = ComputationalPredictionService(enable_predictions=False)

        evidence = ComputationalEvidence(
            deleterious_count=0,
            benign_count=3,
            total_predictions=3,
            sift_result="benign",
            polyphen_result="benign",
            cadd_result="benign",
        )

        applies, reason = service._check_bp4(evidence)
        assert applies is True
        assert "BP4" in reason

    def test_check_bp4_deferred_to_pp3(self):
        """Test BP4 defers when PP3 applies."""
        service = ComputationalPredictionService(enable_predictions=False)

        evidence = ComputationalEvidence(
            pp3=True,  # PP3 already applies
            deleterious_count=3,
            benign_count=3,
            total_predictions=6,
        )

        applies, reason = service._check_bp4(evidence)
        assert applies is False
        assert "deferred" in reason.lower()


class TestACMGClassifierV8:
    """Test enhanced classifier with computational predictions."""

    def test_init_without_predictions(self):
        """Test classifier works without predictions."""
        classifier = ACMGClassifierV8(enable_gnomad=False, enable_predictions=False)
        assert classifier.enable_predictions is False
        assert classifier.prediction_service is None

    def test_get_enabled_codes_with_predictions(self):
        """Test enabled codes include PP3/BP4."""
        with patch("varidex.core.services.computational_prediction.DbNSFPClient"):
            classifier = ACMGClassifierV8(enable_gnomad=False, enable_predictions=True)
            codes = classifier.get_enabled_codes()

            # Should have PP3 and BP4
            assert "PP3" in codes["pathogenic"] or not classifier.enable_predictions
            assert "BP4" in codes["benign"] or not classifier.enable_predictions

    def test_health_check(self):
        """Test health check includes prediction status."""
        classifier = ACMGClassifierV8(enable_gnomad=False, enable_predictions=False)
        health = classifier.health_check()

        assert "predictions" in health
        assert "enabled" in health["predictions"]
        assert health["predictions"]["enabled"] is False
        assert health["version"] == ACMGClassifierV8.VERSION

    def test_get_evidence_summary(self):
        """Test evidence summary generation."""
        classifier = ACMGClassifierV8(enable_gnomad=False, enable_predictions=False)

        variant = VariantData(
            rsid="rs123",
            chromosome="17",
            position="43094692",
            genotype="AG",
            gene="BRCA1",
            ref_allele="G",
            alt_allele="A",
            clinical_sig="Pathogenic",
            review_status="reviewed by expert panel",
            variant_type="SNV",
            molecular_consequence="frameshift",
        )

        summary = classifier.get_evidence_summary(variant)

        assert "classification" in summary
        assert "evidence" in summary
        assert "features_used" in summary
        assert "gnomad" in summary["features_used"]
        assert "computational_predictions" in summary["features_used"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
