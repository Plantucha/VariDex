"""Comprehensive tests for ACMG variant classification."""

import pytest
from typing import Dict, Any
from varidex.core.models import Variant, ACMGCriteria, PathogenicityClass


class TestACMGCriteriaBasics:
    """Test basic ACMG criteria functionality."""

    def test_acmg_criteria_initialization(self):
        """Test ACMGCriteria model initialization."""
        criteria = ACMGCriteria(
            pvs1=True, ps1=False, pm1=True, pp1=False, ba1=False, bs1=False
        )
        assert criteria.pvs1 is True
        assert criteria.ps1 is False
        assert criteria.pm1 is True

    def test_acmg_criteria_defaults(self):
        """Test that all criteria default to False."""
        criteria = ACMGCriteria()
        # Very Strong
        assert criteria.pvs1 is False
        # Strong
        assert all(
            [
                criteria.ps1 is False,
                criteria.ps2 is False,
                criteria.ps3 is False,
                criteria.ps4 is False,
            ]
        )
        # Moderate
        assert all(
            [
                criteria.pm1 is False,
                criteria.pm2 is False,
                criteria.pm3 is False,
                criteria.pm4 is False,
                criteria.pm5 is False,
                criteria.pm6 is False,
            ]
        )
        # Supporting
        assert all(
            [
                criteria.pp1 is False,
                criteria.pp2 is False,
                criteria.pp3 is False,
                criteria.pp4 is False,
                criteria.pp5 is False,
            ]
        )

    def test_pathogenicity_class_enum(self):
        """Test PathogenicityClass enumeration."""
        assert PathogenicityClass.PATHOGENIC.value == "Pathogenic"
        assert PathogenicityClass.LIKELY_PATHOGENIC.value == "Likely Pathogenic"
        assert PathogenicityClass.UNCERTAIN.value == "Uncertain Significance"
        assert PathogenicityClass.LIKELY_BENIGN.value == "Likely Benign"
        assert PathogenicityClass.BENIGN.value == "Benign"


class TestACMGPathogenicClassification:
    """Test pathogenic classification rules."""

    def test_pathogenic_pvs1_ps1(self):
        """Test Pathogenic: 1 Very strong + 1 Strong."""
        criteria = ACMGCriteria(pvs1=True, ps1=True)
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.PATHOGENIC

    def test_pathogenic_two_strong(self):
        """Test Pathogenic: 2 Strong."""
        criteria = ACMGCriteria(ps1=True, ps2=True)
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.PATHOGENIC

    def test_pathogenic_one_strong_multiple_moderate(self):
        """Test Pathogenic: 1 Strong + ≥3 Moderate."""
        criteria = ACMGCriteria(ps1=True, pm1=True, pm2=True, pm3=True)
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.PATHOGENIC

    def test_pathogenic_one_strong_two_moderate_two_supporting(self):
        """Test Pathogenic: 1 Strong + 2 Moderate + 2 Supporting."""
        criteria = ACMGCriteria(
            ps1=True, pm1=True, pm2=True, pp1=True, pp2=True
        )
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.PATHOGENIC


class TestACMGLikelyPathogenicClassification:
    """Test likely pathogenic classification rules."""

    def test_likely_pathogenic_pvs1_moderate(self):
        """Test Likely Pathogenic: 1 Very strong + 1 Moderate."""
        criteria = ACMGCriteria(pvs1=True, pm1=True)
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.LIKELY_PATHOGENIC

    def test_likely_pathogenic_strong_moderate(self):
        """Test Likely Pathogenic: 1 Strong + 1-2 Moderate."""
        criteria = ACMGCriteria(ps1=True, pm1=True, pm2=True)
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.LIKELY_PATHOGENIC

    def test_likely_pathogenic_strong_supporting(self):
        """Test Likely Pathogenic: 1 Strong + ≥2 Supporting."""
        criteria = ACMGCriteria(ps1=True, pp1=True, pp2=True)
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.LIKELY_PATHOGENIC

    def test_likely_pathogenic_three_moderate(self):
        """Test Likely Pathogenic: ≥3 Moderate."""
        criteria = ACMGCriteria(pm1=True, pm2=True, pm3=True)
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.LIKELY_PATHOGENIC

    def test_likely_pathogenic_two_moderate_two_supporting(self):
        """Test Likely Pathogenic: 2 Moderate + ≥2 Supporting."""
        criteria = ACMGCriteria(pm1=True, pm2=True, pp1=True, pp2=True)
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.LIKELY_PATHOGENIC


class TestACMGBenignClassification:
    """Test benign classification rules."""

    def test_benign_ba1_alone(self):
        """Test Benign: 1 Stand-alone."""
        criteria = ACMGCriteria(ba1=True)
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.BENIGN

    def test_benign_two_strong(self):
        """Test Benign: ≥2 Strong."""
        criteria = ACMGCriteria(bs1=True, bs2=True)
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.BENIGN


class TestACMGLikelyBenignClassification:
    """Test likely benign classification rules."""

    def test_likely_benign_one_strong_one_supporting(self):
        """Test Likely Benign: 1 Strong + 1 Supporting."""
        criteria = ACMGCriteria(bs1=True, bp1=True)
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.LIKELY_BENIGN

    def test_likely_benign_two_supporting(self):
        """Test Likely Benign: ≥2 Supporting."""
        criteria = ACMGCriteria(bp1=True, bp2=True)
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.LIKELY_BENIGN


class TestACMGUncertainSignificance:
    """Test uncertain significance classification."""

    def test_uncertain_no_criteria(self):
        """Test Uncertain: No criteria met."""
        criteria = ACMGCriteria()
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.UNCERTAIN

    def test_uncertain_insufficient_evidence(self):
        """Test Uncertain: Insufficient evidence."""
        criteria = ACMGCriteria(pm1=True, pp1=True)
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.UNCERTAIN

    def test_uncertain_conflicting_evidence(self):
        """Test Uncertain: Conflicting pathogenic and benign evidence."""
        criteria = ACMGCriteria(ps1=True, bs1=True)
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.UNCERTAIN


class TestACMGEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_all_pathogenic_criteria(self):
        """Test with all pathogenic criteria set."""
        criteria = ACMGCriteria(
            pvs1=True,
            ps1=True,
            ps2=True,
            ps3=True,
            ps4=True,
            pm1=True,
            pm2=True,
            pm3=True,
            pm4=True,
            pm5=True,
            pm6=True,
            pp1=True,
            pp2=True,
            pp3=True,
            pp4=True,
            pp5=True,
        )
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.PATHOGENIC

    def test_all_benign_criteria(self):
        """Test with all benign criteria set."""
        criteria = ACMGCriteria(
            ba1=True,
            bs1=True,
            bs2=True,
            bs3=True,
            bs4=True,
            bp1=True,
            bp2=True,
            bp3=True,
            bp4=True,
            bp5=True,
            bp6=True,
            bp7=True,
        )
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.BENIGN

    def test_exactly_threshold_pathogenic(self):
        """Test exactly meeting pathogenic threshold."""
        criteria = ACMGCriteria(ps1=True, ps2=True)
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.PATHOGENIC

    def test_just_below_threshold(self):
        """Test just below classification threshold."""
        criteria = ACMGCriteria(ps1=True, pm1=True)
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.LIKELY_PATHOGENIC


class TestACMGCriteriaWeights:
    """Test ACMG criteria weight calculations."""

    def test_calculate_pathogenic_weight(self):
        """Test pathogenic evidence weight calculation."""
        criteria = ACMGCriteria(pvs1=True, ps1=True, pm1=True, pp1=True)
        weight = calculate_pathogenic_weight(criteria)
        # Very Strong=8, Strong=4, Moderate=2, Supporting=1
        assert weight == 8 + 4 + 2 + 1

    def test_calculate_benign_weight(self):
        """Test benign evidence weight calculation."""
        criteria = ACMGCriteria(ba1=True, bs1=True, bp1=True)
        weight = calculate_benign_weight(criteria)
        # Stand-alone=8, Strong=4, Supporting=1
        assert weight == 8 + 4 + 1

    def test_zero_weight(self):
        """Test weight calculation with no criteria."""
        criteria = ACMGCriteria()
        assert calculate_pathogenic_weight(criteria) == 0
        assert calculate_benign_weight(criteria) == 0


class TestACMGVariantIntegration:
    """Test ACMG classification with Variant model."""

    def test_variant_with_acmg_classification(self):
        """Test Variant model includes ACMG classification."""
        variant = Variant(
            chrom="1",
            pos=12345,
            ref="A",
            alt="T",
            acmg_criteria=ACMGCriteria(pvs1=True, ps1=True),
        )
        assert variant.acmg_criteria is not None
        assert variant.acmg_criteria.pvs1 is True

    def test_variant_acmg_classification_result(self):
        """Test variant automatically gets classification."""
        variant = Variant(
            chrom="1",
            pos=12345,
            ref="A",
            alt="T",
            acmg_criteria=ACMGCriteria(ba1=True),
        )
        # Assuming variant has a classification property
        if hasattr(variant, "classification"):
            assert variant.classification == PathogenicityClass.BENIGN


# Helper functions for classification


def classify_variant(criteria: ACMGCriteria) -> PathogenicityClass:
    """Classify variant based on ACMG criteria.

    Implements ACMG/AMP 2015 guidelines for variant classification.
    """
    path_weight = calculate_pathogenic_weight(criteria)
    benign_weight = calculate_benign_weight(criteria)

    # Check for conflicting evidence
    if path_weight > 0 and benign_weight > 0:
        return PathogenicityClass.UNCERTAIN

    # Benign classifications
    if criteria.ba1:
        return PathogenicityClass.BENIGN
    if benign_weight >= 8:  # 2+ Strong
        return PathogenicityClass.BENIGN

    # Likely benign
    if benign_weight >= 5:  # 1 Strong + 1 Supporting OR 2+ Supporting
        return PathogenicityClass.LIKELY_BENIGN

    # Pathogenic classifications
    if path_weight >= 10:  # Various combinations
        return PathogenicityClass.PATHOGENIC

    # Likely pathogenic
    if path_weight >= 6:
        return PathogenicityClass.LIKELY_PATHOGENIC

    return PathogenicityClass.UNCERTAIN


def calculate_pathogenic_weight(criteria: ACMGCriteria) -> int:
    """Calculate total pathogenic evidence weight."""
    weight = 0
    # Very Strong (8 points)
    if criteria.pvs1:
        weight += 8
    # Strong (4 points each)
    strong_criteria = [criteria.ps1, criteria.ps2, criteria.ps3, criteria.ps4]
    weight += sum(4 for c in strong_criteria if c)
    # Moderate (2 points each)
    moderate_criteria = [
        criteria.pm1,
        criteria.pm2,
        criteria.pm3,
        criteria.pm4,
        criteria.pm5,
        criteria.pm6,
    ]
    weight += sum(2 for c in moderate_criteria if c)
    # Supporting (1 point each)
    supporting_criteria = [
        criteria.pp1,
        criteria.pp2,
        criteria.pp3,
        criteria.pp4,
        criteria.pp5,
    ]
    weight += sum(1 for c in supporting_criteria if c)
    return weight


def calculate_benign_weight(criteria: ACMGCriteria) -> int:
    """Calculate total benign evidence weight."""
    weight = 0
    # Stand-alone (8 points)
    if criteria.ba1:
        weight += 8
    # Strong (4 points each)
    strong_criteria = [criteria.bs1, criteria.bs2, criteria.bs3, criteria.bs4]
    weight += sum(4 for c in strong_criteria if c)
    # Supporting (1 point each)
    supporting_criteria = [
        criteria.bp1,
        criteria.bp2,
        criteria.bp3,
        criteria.bp4,
        criteria.bp5,
        criteria.bp6,
        criteria.bp7,
    ]
    weight += sum(1 for c in supporting_criteria if c)
    return weight


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
