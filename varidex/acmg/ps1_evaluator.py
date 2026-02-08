"""Unit tests for PS1 ACMG criterion implementation."""

import pytest
import sys
import os
from pathlib import Path

# Add src to path for imports (standard project structure)
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from acmg.ps1_evaluator import (  # Assuming file saved as src/acmg/ps1_evaluator.py
    PS1Evaluator,
    PS1Evidence,
    ProteinChangeMatch,
    apply_ps1_to_variant,
)


# Mock SecuritySanitizer for testing
class MockSecuritySanitizer:
    def validate_hgvs(self, hgvs: str) -> str:
        return hgvs

    def validate_acmg_code(self, code: str) -> None:
        if code != "PS1":
            raise ValueError(f"Invalid ACMG code: {code}")


@pytest.fixture
def mock_sanitizer(mocker):
    """Mock SecuritySanitizer."""
    sanitizer = MockSecuritySanitizer()
    mocker.patch("acmg.ps1_evaluator.SecuritySanitizer", return_value=sanitizer)
    return sanitizer


@pytest.fixture
def ps1_evaluator(mock_sanitizer):
    """PS1 evaluator fixture with mock ClinVar path."""
    return PS1Evaluator("tests/data/mock_clinvar.db")


def test_ps1_evaluator_initialization(mock_sanitizer):
    """Test PS1Evaluator initialization."""
    evaluator = PS1Evaluator("clinvar.db")
    assert evaluator.clinvar_db_path == "clinvar.db"
    assert evaluator.sanitizer is not None


def test_parse_protein_hgvs_valid(mock_sanitizer):
    """Test parsing valid protein HGVS."""
    evaluator = PS1Evaluator("clinvar.db")
    result = evaluator._parse_protein_hgvs("p.Arg123Gln")
    assert result == (123, "Arg", "Gln")


def test_parse_protein_hgvs_invalid(mock_sanitizer):
    """Test parsing invalid protein HGVS."""
    evaluator = PS1Evaluator("clinvar.db")
    result = evaluator._parse_protein_hgvs("invalid")
    assert result is None


def test_load_pathogenic_protein_variants(ps1_evaluator):
    """Test loading pathogenic variants cache."""
    variants = ps1_evaluator._load_pathogenic_protein_variants()
    assert isinstance(variants, set)
    assert len(variants) > 0
    # Example data should be present
    assert (123, "Arg", "Gln") in variants


def test_ps1_exact_match(ps1_evaluator):
    """Test PS1 with exact amino acid match."""
    hgvs = "p.Arg123Gln"
    evidence = ps1_evaluator.evaluate(hgvs)

    assert evidence.validated is True
    assert evidence.is_applicable is True
    assert len(evidence.matches) == 1

    match = evidence.matches[0]
    assert match.query_aa_pos == 123
    assert match.query_aa_ref == "Arg"
    assert match.query_aa_alt == "Gln"
    assert match.match_type == "exact_aa"
    assert "pathogenic" in match.pathogenicity


def test_ps1_no_match(ps1_evaluator):
    """Test PS1 with no pathogenic match."""
    hgvs = "p.Gly999Val"
    evidence = ps1_evaluator.evaluate(hgvs)

    assert evidence.validated is True
    assert evidence.is_applicable is False
    assert len(evidence.matches) == 0
    assert "not applicable" in evidence.evidence_summary


def test_ps1_invalid_hgvs(ps1_evaluator):
    """Test PS1 with invalid HGVS format."""
    hgvs = "invalid_hgvs"
    evidence = ps1_evaluator.evaluate(hgvs)

    assert evidence.validated is True
    assert evidence.is_applicable is False
    assert "No valid protein HGVS" in evidence.evidence_summary


def test_apply_ps1_to_variant(ps1_evaluator):
    """Test pipeline integration function."""
    result = apply_ps1_to_variant("tests/data/clinvar.db", "p.Arg123Gln")

    assert "ps1" in result
    assert result["is_ps1_supporting"] is True
    ps1_data = result["ps1"]
    assert ps1_data["criterion"] == "PS1"
    assert ps1_data["strength"] == "very_strong"


def test_ps1_evidence_model():
    """Test PS1Evidence model properties."""
    match = ProteinChangeMatch(
        query_aa_pos=123,
        query_aa_ref="Arg",
        query_aa_alt="Gln",
        pathogenic_var="p.Arg123Gln",
        clinvar_id="RCV000123456",
        pathogenicity="pathogenic",
        match_type="exact_aa",
    )

    evidence = PS1Evidence(
        matches=[match], evidence_summary="Test summary", validated=True
    )

    assert evidence.criterion == "PS1"
    assert evidence.is_applicable is True
    assert len(evidence.matches) == 1
    assert evidence.to_dict()["strength"] == "very_strong"


def test_ps1_cache_efficiency(ps1_evaluator):
    """Test pathogenic variants cache works."""
    # First call loads cache
    variants1 = ps1_evaluator._load_pathogenic_protein_variants()
    # Second call uses cache
    variants2 = ps1_evaluator._load_pathogenic_protein_variants()
    assert variants1 is variants2  # Same object (cached)


class TestPS1SecurityIntegration:
    """Test security sanitizer integration."""

    def test_security_validation_called(self, mocker, mock_sanitizer):
        """Verify SecuritySanitizer methods are called."""
        hgvs_mock = mocker.patch.object(mock_sanitizer, "validate_hgvs")
        acmg_mock = mocker.patch.object(mock_sanitizer, "validate_acmg_code")

        evaluator = PS1Evaluator("clinvar.db")
        evaluator.evaluate("p.Arg123Gln")

        hgvs_mock.assert_called_once()
        acmg_mock.assert_called_once_with("PS1")


def test_ps1_pipeline_integration_example():
    """Test full pipeline-like usage."""
    # Simulate pipeline processing multiple variants
    variants = ["p.Arg123Gln", "p.Gly456Arg", "p.Gly999Val"]
    results = []

    evaluator = PS1Evaluator("clinvar.db")
    for var in variants:
        result = apply_ps1_to_variant("clinvar.db", var)
        results.append(result)

    # First two should match, third shouldn't
    assert results[0]["is_ps1_supporting"] is True
    assert results[1]["is_ps1_supporting"] is True
    assert results[2]["is_ps1_supporting"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
