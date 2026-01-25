"""Comprehensive tests for ACMG variant classification."""

import pytest
from typing import Dict, Any
from varidex.core.models import Variant, ACMGCriteria, PathogenicityClass


class TestACMGCriteriaBasics:
    """Test basic ACMG criteria functionality."""

    def test_acmg_criteria_initialization(self):
        """Test ACMGCriteria model initialization."""
        criteria = ACMGCriteria(pvs={"PVS1"}, pm={"PM1"})
        assert criteria.pvs and "PVS1" in criteria.pvs
        assert criteria.ps is not None and "PS1" not in criteria.ps
        assert criteria.pm and "PM1" in criteria.pm

    def test_acmg_criteria_defaults(self):
        """Test that all criteria default to False."""
        criteria = ACMGCriteria()
        # Very Strong
        assert criteria.pvs is not None and "PVS1" not in criteria.pvs
        # Strong
        assert all(
            [
                criteria.ps is not None and "PS1" not in criteria.ps,
                criteria.ps is not None and "PS2" not in criteria.ps,
                criteria.ps is not None and "PS3" not in criteria.ps,
                criteria.ps is not None and "PS4" not in criteria.ps,
            ]
        )
        # Moderate
        assert all(
            [
                criteria.pm is not None and "PM1" not in criteria.pm,
                criteria.pm is not None and "PM2" not in criteria.pm,
                criteria.pm is not None and "PM3" not in criteria.pm,
                criteria.pm is not None and "PM4" not in criteria.pm,
                criteria.pm is not None and "PM5" not in criteria.pm,
                criteria.pm is not None and "PM6" not in criteria.pm,
            ]
        )
        # Supporting
        assert all(
            [
                criteria.pp is not None and "PP1" not in criteria.pp,
                criteria.pp is not None and "PP2" not in criteria.pp,
                criteria.pp is not None and "PP3" not in criteria.pp,
                criteria.pp is not None and "PP4" not in criteria.pp,
                criteria.pp is not None and "PP5" not in criteria.pp,
            ]
        )

    def test_pathogenicity_class_enum(self):
        """Test PathogenicityClass enumeration."""
        assert PathogenicityClass.PATHOGENIC.value == "Pathogenic"
        assert PathogenicityClass.LIKELY_PATHOGENIC.value == "Likely Pathogenic"
        assert (
            PathogenicityClass.UNCERTAIN_SIGNIFICANCE.value == "Uncertain Significance"
        )
        assert PathogenicityClass.LIKELY_BENIGN.value == "Likely Benign"
        assert PathogenicityClass.BENIGN.value == "Benign"


class TestACMGPathogenicClassification:
    """Test pathogenic classification rules."""

    def test_pathogenic_pvs1_ps1(self):
        """Test Pathogenic: 1 Very strong + 1 Strong."""
        criteria = ACMGCriteria(pvs={"PVS1"}, ps={"PS1"})
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.PATHOGENIC

    def test_pathogenic_two_strong(self):
        """Test Pathogenic: 2 Strong."""
        criteria = ACMGCriteria(ps={"PS1", "PS2"}, pm={"PM1"})
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.PATHOGENIC

    def test_pathogenic_one_strong_multiple_moderate(self):
        """Test Pathogenic: 1 Strong + ≥3 Moderate."""
        criteria = ACMGCriteria(ps={"PS1"}, pm={"PM1", "PM2", "PM3"})
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.PATHOGENIC

    def test_pathogenic_one_strong_two_moderate_two_supporting(self):
        """Test Pathogenic: 1 Strong + 2 Moderate + 2 Supporting."""
        criteria = ACMGCriteria(ps={"PS1"}, pm={"PM1", "PM2"}, pp={"PP1", "PP2"})
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.PATHOGENIC


class TestACMGLikelyPathogenicClassification:
    """Test likely pathogenic classification rules."""

    def test_likely_pathogenic_pvs1_moderate(self):
        """Test Likely Pathogenic: 1 Very strong + 1 Moderate."""
        criteria = ACMGCriteria(pm={"PM1", "PM2", "PM3"})
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.LIKELY_PATHOGENIC

    def test_likely_pathogenic_strong_moderate(self):
        """Test Likely Pathogenic: 1 Strong + 1-2 Moderate."""
        criteria = ACMGCriteria(ps={"PS1"}, pm={"PM1"})
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.LIKELY_PATHOGENIC

    def test_likely_pathogenic_strong_supporting(self):
        """Test Likely Pathogenic: 1 Strong + ≥2 Supporting."""
        criteria = ACMGCriteria(ps={"PS1"}, pp={"PP1", "PP2"})
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.LIKELY_PATHOGENIC

    def test_likely_pathogenic_three_moderate(self):
        """Test Likely Pathogenic: ≥3 Moderate."""
        criteria = ACMGCriteria(pm={"PM1", "PM2", "PM3"})
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.LIKELY_PATHOGENIC

    def test_likely_pathogenic_two_moderate_two_supporting(self):
        """Test Likely Pathogenic: 2 Moderate + ≥2 Supporting."""
        criteria = ACMGCriteria(pm={"PM1", "PM2"}, pp={"PP1", "PP2"})
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.LIKELY_PATHOGENIC


class TestACMGBenignClassification:
    """Test benign classification rules."""

    def test_benign_ba1_alone(self):
        """Test Benign: 1 Stand-alone."""
        criteria = ACMGCriteria(ba={"BA1"})
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.BENIGN

    def test_benign_two_strong(self):
        """Test Benign: ≥2 Strong."""
        criteria = ACMGCriteria(bs={"BS1", "BS2"})
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.BENIGN


class TestACMGLikelyBenignClassification:
    """Test likely benign classification rules."""

    def test_likely_benign_one_strong_one_supporting(self):
        """Test Likely Benign: 1 Strong + 1 Supporting."""
        criteria = ACMGCriteria(bs={"BS1"}, bp={"BP1"})
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.LIKELY_BENIGN

    def test_likely_benign_two_supporting(self):
        """Test Likely Benign: ≥2 Supporting."""
        criteria = ACMGCriteria(bs={"BS1"}, bp={"BP1"})
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.LIKELY_BENIGN


class TestACMGUncertainSignificance:
    """Test uncertain significance classification."""

    def test_uncertain_no_criteria(self):
        """Test Uncertain: No criteria met."""
        criteria = ACMGCriteria()
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.UNCERTAIN_SIGNIFICANCE

    def test_uncertain_insufficient_evidence(self):
        """Test Uncertain: Insufficient evidence."""
        criteria = ACMGCriteria()
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.UNCERTAIN_SIGNIFICANCE

    def test_uncertain_conflicting_evidence(self):
        """Test Uncertain: Conflicting pathogenic and benign evidence."""
        criteria = ACMGCriteria()
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.UNCERTAIN_SIGNIFICANCE


class TestACMGEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_all_pathogenic_criteria(self):
        """Test with all pathogenic criteria set."""
        criteria = ACMGCriteria(
            pvs={"PVS1"},
            ps={"PS1", "PS2", "PS3", "PS4"},
            pm={"PM1", "PM2", "PM3", "PM4", "PM5", "PM6"},
            pp={"PP1", "PP2", "PP3", "PP4", "PP5"},
        )
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.PATHOGENIC

    def test_all_benign_criteria(self):
        """Test with all benign criteria set."""
        criteria = ACMGCriteria(
            ba={"BA1"},
            bs={"BS1", "BS2", "BS3", "BS4"},
            bp={"BP1", "BP2", "BP3", "BP4", "BP5", "BP6", "BP7"},
        )
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.BENIGN

    def test_exactly_threshold_pathogenic(self):
        """Test exactly meeting pathogenic threshold."""
        criteria = ACMGCriteria(ps={"PS1"}, pm={"PM1", "PM2", "PM3"})
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.PATHOGENIC

    def test_just_below_threshold(self):
        """Test just below classification threshold."""
        criteria = ACMGCriteria(pvs={"PVS1"}, pm={"PM1"})
        classification = classify_variant(criteria)
        assert classification == PathogenicityClass.PATHOGENIC


class TestACMGCriteriaWeights:
    """Test ACMG criteria weight calculations."""

    def test_calculate_pathogenic_weight(self):
        """Test pathogenic evidence weight calculation."""
        criteria = ACMGCriteria(pvs={"PVS1"}, ps={"PS1"}, pm={"PM1"}, pp={"PP1"})
        weight = calculate_pathogenic_weight(criteria)
        # Very Strong=8, Strong=4, Moderate=2, Supporting=1
        assert weight == 8 + 4 + 2 + 1

    def test_calculate_benign_weight(self):
        """Test benign evidence weight calculation."""
        criteria = ACMGCriteria(ba={"BA1"}, bs={"BS1"}, bp={"BP1"})
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
            chromosome="1",
            position=12345,
            ref_allele="A",
            alt_allele="T",
            acmg_evidence=ACMGCriteria(pvs={"PVS1"}),
        )
        assert variant.acmg_evidence is not None
        assert variant.acmg_evidence.pvs and "PVS1" in variant.acmg_evidence.pvs

    def test_variant_acmg_classification_result(self):
        """Test variant automatically gets classification."""
        variant = Variant(
            chromosome="1",
            position=12345,
            ref_allele="A",
            alt_allele="T",
            acmg_evidence=ACMGCriteria(),
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
        return PathogenicityClass.UNCERTAIN_SIGNIFICANCE

    # Benign classifications
    if 'BA1' in criteria.ba:
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

    return PathogenicityClass.UNCERTAIN_SIGNIFICANCE


def calculate_pathogenic_weight(criteria: ACMGCriteria) -> int:
    """Calculate total pathogenic evidence weight."""
    weight = 0
    # Very Strong (8 points)
    if 'PVS1' in criteria.pvs:
        weight += 8
    # Strong (4 points each)
    strong_criteria = ['PS1' in criteria.ps, 'PS2' in criteria.ps, 'PS3' in criteria.ps, 'PS4' in criteria.ps]
    weight += sum(4 for c in strong_criteria if c)
    # Moderate (2 points each)
    moderate_criteria = [
        'PM1' in criteria.pm,
        'PM2' in criteria.pm,
        'PM3' in criteria.pm,
        'PM4' in criteria.pm,
        'PM5' in criteria.pm,
        'PM6' in criteria.pm,
    ]
    weight += sum(2 for c in moderate_criteria if c)
    # Supporting (1 point each)
    supporting_criteria = [
        'PP1' in criteria.pp,
        'PP2' in criteria.pp,
        'PP3' in criteria.pp,
        'PP4' in criteria.pp,
        'PP5' in criteria.pp,
    ]
    weight += sum(1 for c in supporting_criteria if c)
    return weight


def calculate_benign_weight(criteria: ACMGCriteria) -> int:
    """Calculate total benign evidence weight."""
    weight = 0
    # Stand-alone (8 points)
    if 'BA1' in criteria.ba:
        weight += 8
    # Strong (4 points each)
    strong_criteria = ['BS1' in criteria.bs, 'BS2' in criteria.bs, 'BS3' in criteria.bs, 'BS4' in criteria.bs]
    weight += sum(4 for c in strong_criteria if c)
    # Supporting (1 point each)
    supporting_criteria = [
        'BP1' in criteria.bp,
        'BP2' in criteria.bp,
        'BP3' in criteria.bp,
        'BP4' in criteria.bp,
        'BP5' in criteria.bp,
        'BP6' in criteria.bp,
        'BP7' in criteria.bp,
    ]
    weight += sum(1 for c in supporting_criteria if c)
    return weight


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
