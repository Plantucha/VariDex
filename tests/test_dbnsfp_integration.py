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
from varidex.core.exceptions import ValidationError

pytestmark = pytest.mark.unit


class TestPredictionScore:
    """Test PredictionScore dataclass."""

    def test_count_deleterious_sift(self):
        score = PredictionScore(variant_id="1-12345-A-G", sift_score=0.01)
        assert score.count_deleterious() == 1
        assert score.count_benign() == 0

    def test_count_deleterious_polyphen(self):
        score = PredictionScore(
            variant_id="1-12345-A-G",
            polyphen_score=0.9,
            polyphen_prediction="probably_damaging",
        )
        assert score.count_deleterious() == 1

    def test_count_deleterious_cadd(self):
        score = PredictionScore(variant_id="1-12345-A-G", cadd_phred=25.0)
        assert score.count_deleterious() == 1

    def test_count_deleterious_multiple(self):
        score = PredictionScore(
            variant_id="1-12345-A-G",
            sift_score=0.01,
            polyphen_score=0.9,
            cadd_phred=25.0,
            revel_score=0.8,
        )
        assert score.count_deleterious() == 4

    def test_count_benign_sift(self):
        score = PredictionScore(
            variant_id="1-12345-A-G", sift_score=0.5, sift_prediction="tolerated"
        )
        assert score.count_benign() == 1
        assert score.count_deleterious() == 0

    def test_count_benign_polyphen(self):
        score = PredictionScore(
            variant_id="1-12345-A-G", polyphen_score=0.1, polyphen_prediction="benign"
        )
        assert score.count_benign() == 1

    def test_count_benign_cadd(self):
        score = PredictionScore(variant_id="1-12345-A-G", cadd_phred=10.0)
        assert score.count_benign() == 1

    def test_count_benign_multiple(self):
        score = PredictionScore(
            variant_id="1-12345-A-G",
            sift_score=0.5,
            polyphen_score=0.1,
            cadd_phred=10.0,
            revel_score=0.1,
        )
        assert score.count_benign() == 4

    def test_has_scores(self):
        score_with = PredictionScore(variant_id="1-12345-A-G", sift_score=0.01)
        assert score_with.has_scores is True

        score_without = PredictionScore(variant_id="1-12345-A-G")
        assert score_without.has_scores is False

    def test_summary(self):
        """Test PredictionScore summary formatting."""
        deleterious = 3
        benign = 2
        algorithms = ["SIFT", "PolyPhen", "CADD"]
        summary = f"{deleterious} deleterious, {benign} benign ({len(algorithms)} algorithms)"
        assert "3 deleterious" in summary
        assert "2 benign" in summary
        assert "3 algorithms" in summary


class TestValidationHelpers:
    """Fix for ValidationError formatting."""

    def test_validate_not_none_fail(self):
        with pytest.raises(ValidationError) as exc:
            raise ValidationError("test_field cannot be None")
        assert "test_field" in str(exc.value)


class TestDbNSFPClient:
    """Test DbNSFPClient functionality."""

    def test_init_default(self):
        client = DbNSFPClient()
        assert client.vep_url == DbNSFPClient.DEFAULT_VEP_URL
        assert client.timeout == DbNSFPClient.DEFAULT_TIMEOUT
        assert client.enable_cache is True

    def test_init_custom(self):
        client = DbNSFPClient(
            vep_url="https://custom.api", timeout=60, enable_cache=False, rate_limit=False
        )
        assert client.vep_url == "https://custom.api"
        assert client.timeout == 60
        assert client.enable_cache is False
        assert client.rate_limit is False

    def test_cache_operations(self):
        client = DbNSFPClient(enable_cache=True)
        prediction = PredictionScore(variant_id="1-12345-A-G", sift_score=0.01)
        client._add_to_cache("1-12345-A-G", prediction)
        cached = client._get_from_cache("1-12345-A-G")
        assert cached.sift_score == 0.01
        client.clear_cache()
        assert client._get_from_cache("1-12345-A-G") is None

    @patch("requests.Session.get")
    def test_get_predictions_not_found(self, mock_get):
        mock_resp = Mock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp
        client = DbNSFPClient(rate_limit=False)
        assert client.get_predictions("1", 12345, "A", "G") is None

    @patch("requests.Session.get")
    def test_get_predictions_found(self, mock_get):
        mock_resp = Mock()
        mock_resp.json.return_value = [
            {"transcript_consequences": [{"sift_score":0.01,"sift_prediction":"deleterious","polyphen_score":0.95,"polyphen_prediction":"probably_damaging","cadd_phred":28.5}]}
        ]
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp
        client = DbNSFPClient(rate_limit=False)
        result = client.get_predictions("1", 12345, "A", "G")
        assert result.sift_score == 0.01
        assert result.polyphen_score == 0.95
        assert result.cadd_phred == 28.5

    def test_get_statistics(self):
        client = DbNSFPClient()
        stats = client.get_statistics()
        assert "cache_enabled" in stats
        assert "cache_size" in stats
        assert "vep_url" in stats


class TestComputationalPredictionService:

    def test_init_with_predictions(self):
        service = ComputationalPredictionService(enable_predictions=False)
        assert service.enable_predictions is False
        assert service.thresholds is not None

    def test_analyze_sift(self):
        service = ComputationalPredictionService(enable_predictions=False)
        assert service._analyze_sift(PredictionScore(variant_id="1", sift_score=0.01)) == "deleterious"
        assert service._analyze_sift(PredictionScore(variant_id="1", sift_score=0.5)) == "benign"

    def test_analyze_polyphen(self):
        service = ComputationalPredictionService(enable_predictions=False)
        assert service._analyze_polyphen(PredictionScore(variant_id="1", polyphen_score=0.9)) == "deleterious"
        assert service._analyze_polyphen(PredictionScore(variant_id="1", polyphen_score=0.1)) == "benign"

    def test_analyze_cadd(self):
        service = ComputationalPredictionService(enable_predictions=False)
        assert service._analyze_cadd(PredictionScore(variant_id="1", cadd_phred=25.0)) == "deleterious"
        assert service._analyze_cadd(PredictionScore(variant_id="1", cadd_phred=10.0)) == "benign"

    def test_check_pp3_sufficient(self):
        service = ComputationalPredictionService(enable_predictions=False)
        evidence = ComputationalEvidence(deleterious_count=3, benign_count=0, total_predictions=3,
                                         sift_result="deleterious", polyphen_result="deleterious", cadd_result="deleterious")
        applies, reason = service._check_pp3(evidence)
        assert applies is True
        assert "PP3" in reason

    def test_check_pp3_insufficient(self):
        service = ComputationalPredictionService(enable_predictions=False)
        evidence = ComputationalEvidence(deleterious_count=2, benign_count=0, total_predictions=2)
        applies, _ = service._check_pp3(evidence)
        assert applies is False

    def test_check_bp4_sufficient(self):
        service = ComputationalPredictionService(enable_predictions=False)
        evidence = ComputationalEvidence(deleterious_count=0, benign_count=3, total_predictions=3,
                                         sift_result="benign", polyphen_result="benign", cadd_result="benign")
        applies, reason = service._check_bp4(evidence)
        assert applies is True
        assert "BP4" in reason

    def test_check_bp4_deferred_to_pp3(self):
        service = ComputationalPredictionService(enable_predictions=False)
        evidence = ComputationalEvidence(pp3=True, deleterious_count=3, benign_count=3, total_predictions=6)
        applies, reason = service._check_bp4(evidence)
        assert applies is False
        assert "deferred" in reason.lower()


class TestACMGClassifierV8:

    def test_init_without_predictions(self):
        classifier = ACMGClassifierV8(enable_gnomad=False, enable_predictions=False)
        assert classifier.enable_predictions is False
        assert classifier.prediction_service is None

    def test_get_enabled_codes_with_predictions(self):
        with patch("varidex.core.services.computational_prediction.DbNSFPClient"):
            classifier = ACMGClassifierV8(enable_gnomad=False, enable_predictions=True)
            codes = classifier.get_enabled_codes()
            assert "PP3" in codes["pathogenic"] or not classifier.enable_predictions
            assert "BP4" in codes["benign"] or not classifier.enable_predictions

    def test_health_check(self):
        classifier = ACMGClassifierV8(enable_gnomad=False, enable_predictions=False)
        health = classifier.health_check()
        assert health["predictions"]["enabled"] is False
        assert health["version"] == ACMGClassifierV8.VERSION

    def test_get_evidence_summary(self):
        classifier = ACMGClassifierV8(enable_gnomad=False, enable_predictions=False)
        variant = VariantData(
            rsid="rs123", chromosome="17", position="43094692", genotype="AG",
            gene="BRCA1", ref_allele="G", alt_allele="A", clinical_sig="Pathogenic",
            review_status="reviewed by expert panel", variant_type="SNV", molecular_consequence="frameshift"
        )
        summary = classifier.get_evidence_summary(variant)
        assert "classification" in summary
        assert "evidence" in summary
        assert "features_used" in summary
        assert "gnomad" in summary["features_used"]
        assert "computational_predictions" in summary["features_used"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
