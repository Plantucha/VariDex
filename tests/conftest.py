"""
Shared pytest fixtures and test configuration for VariDex test suite.
Version: 6.0.0 - Development Grade
Author: VariDex Development Team
Date: January 25, 2026
"""

import pytest
import pandas as pd
from pathlib import Path
from typing import Callable
import tempfile
import shutil
from unittest.mock import Mock, patch

# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "smoke: marks tests for smoke testing")


# ============================================================================
# SESSION-SCOPED FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Create temporary test data directory with cleanup."""
    temp_dir = Path(tempfile.mkdtemp(prefix="varidex_test_"))
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================================
# DATA FIXTURES
# ============================================================================


@pytest.fixture
def sample_clinvar_variants() -> pd.DataFrame:
    """Sample ClinVar variant data for testing."""
    return pd.DataFrame(
        {
            "rsid": ["rs80357906", "rs28934576", "rs121913529", "rs397509247"],
            "chromosome": ["17", "17", "13", "19"],
            "position": ["43094692", "43082434", "32340301", "50378563"],
            "ref_allele": ["G", "G", "C", "C"],
            "alt_allele": ["A", "A", "T", "T"],
            "gene": ["BRCA1", "BRCA1", "BRCA2", "LDLR"],
            "clinical_sig": ["Pathogenic", "Pathogenic", "Pathogenic", "Benign"],
            "review_status": [
                "criteria provided, multiple submitters",
                "reviewed by expert panel",
                "criteria provided, single submitter",
                "practice guideline",
            ],
            "variant_type": ["single nucleotide variant"] * 4,
            "molecular_consequence": [
                "missense_variant",
                "stop_gained",
                "frameshift_variant",
                "synonymous_variant",
            ],
        }
    )


@pytest.fixture
def sample_user_variants() -> pd.DataFrame:
    """Sample user genome data for testing."""
    return pd.DataFrame(
        {
            "rsid": [
                "rs80357906",
                "rs28934576",
                "rs121913530",
                "rs397509247",
                "rs999999",
            ],
            "chromosome": ["17", "17", "13", "19", "1"],
            "position": ["43094692", "43082434", "32340302", "50378563", "12345678"],
            "genotype": ["AG", "GA", "CT", "CC", "TT"],
        }
    )


@pytest.fixture
def variant_data_builder() -> Callable:
    """Factory fixture for building VariantData instances."""
    from varidex.core.models import VariantData, ACMGEvidenceSet

    def builder(
        rsid="rs80357906", chromosome="17", position="43094692", genotype="AG", **kwargs
    ):
        defaults = {
            "rsid": rsid,
            "chromosome": chromosome,
            "position": position,
            "genotype": genotype,
            "normalized_genotype": "A/G",
            "zygosity": "heterozygous",
            "ref_allele": "G",
            "alt_allele": "A",
            "gene": "BRCA1",
            "clinical_sig": "Pathogenic",
            "variant_type": "single nucleotide variant",
            "molecular_consequence": "missense_variant",
            "acmg_evidence": ACMGEvidenceSet(),
            "star_rating": 3,
        }
        defaults.update(kwargs)
        return VariantData(**defaults)

    return builder


@pytest.fixture
def evidence_builder() -> Callable:
    """Factory fixture for building ACMGEvidenceSet instances."""
    from varidex.core.models import ACMGEvidenceSet

    def builder(pathogenic=None, benign=None, conflicts=None):
        evidence = ACMGEvidenceSet()
        if pathogenic:
            for code in pathogenic:
                if not isinstance(code, str):
                    raise ValueError(f"Code must be string, got {type(code).__name__}")
                if code.startswith("PVS"):
                    evidence.pvs.add(code)
                elif code.startswith("PS"):
                    evidence.ps.add(code)
                elif code.startswith("PM"):
                    evidence.pm.add(code)
                elif code.startswith("PP"):
                    evidence.pp.add(code)
        if benign:
            for code in benign:
                if not isinstance(code, str):
                    raise ValueError(f"Code must be string, got {type(code).__name__}")
                if code.startswith("BA"):
                    evidence.ba.add(code)
                elif code.startswith("BS"):
                    evidence.bs.add(code)
                elif code.startswith("BP"):
                    evidence.bp.add(code)
        if conflicts:
            evidence.conflicts.update(conflicts)
        return evidence

    return builder


@pytest.fixture
def sample_variant_data(variant_data_builder, evidence_builder):
    """Pre-built VariantData instance for common test scenarios."""
    evidence = evidence_builder(pathogenic=["PVS1", "PM2"])
    return variant_data_builder(
        acmg_evidence=evidence, acmg_classification="Pathogenic"
    )


# ============================================================================
# CUSTOM ASSERTIONS
# ============================================================================


class VariantAssertions:
    """Custom assertions for variant testing."""

    @staticmethod
    def assert_valid_variant(variant):
        assert variant.rsid is not None, "rsid must not be None"
        assert variant.chromosome is not None, "chromosome must not be None"
        assert variant.position is not None, "position must not be None"
        assert variant.genotype is not None, "genotype must not be None"

    @staticmethod
    def assert_pathogenic_variant(variant):
        assert variant.is_pathogenic(), "Variant should be pathogenic"
        assert variant.acmg_classification in ["Pathogenic", "Likely Pathogenic"]


@pytest.fixture
def variant_assertions():
    return VariantAssertions()


@pytest.fixture
def mock_annotated_variant():
    """Mock single annotated variant."""
    try:
        from src.reporting.models import AnnotatedVariant

        return AnnotatedVariant(chr="1", pos=100, ref="A", alt="T", acmg_class="P")
    except (ImportError, AttributeError):
        return Mock(chr="1", pos=100, ref="A", alt="T", acmg_class="P")


@pytest.fixture
def mock_variants(mock_annotated_variant):
    """Mock list of annotated variants."""
    try:
        from src.reporting.models import AnnotatedVariant

        return [
            mock_annotated_variant,
            AnnotatedVariant(chr="2", pos=200, ref="C", alt="G", acmg_class="B"),
        ]
    except (ImportError, AttributeError):
        return [mock_annotated_variant, Mock(chr="2", pos=200, ref="C", alt="G")]


@pytest.fixture
def mock_config():
    """Mock pipeline config."""
    try:
        from src.pipeline.variant_processor import PipelineConfig

        return PipelineConfig(input_vcf="test.vcf")
    except (ImportError, AttributeError):
        return Mock(input_vcf="test.vcf")


@pytest.fixture
def mock_orchestrator():
    """Mock pipeline orchestrator."""
    orch = Mock()
    orch.run_pipeline.return_value = True
    return orch


@pytest.fixture
def mock_stages():
    """Mock pipeline stages."""
    return [
        Mock(execute=Mock(return_value=[{"CHROM": "1"}])),
        Mock(execute=Mock(return_value=[{"CHROM": "1"}])),
        Mock(execute=Mock(return_value=True)),
    ]


# ============================================================================
# AUTO-USE FIXTURES FOR MOCKING EXTERNALS
# ============================================================================


@pytest.fixture(autouse=True)
def mock_externals(monkeypatch):
    """Auto-patch external annotation loaders during testing.

    This prevents actual API calls to external services during test execution.
    Development version - mocks all external annotation sources.
    """
    try:
        # Mock the loader classes themselves
        from src.annotation import (
            CADDLoader,
            ClinVarLoader,
            DbNSFPLoader,
            GnomADLoader,
        )

        # Replace with mocks
        monkeypatch.setattr("src.annotation.CADDLoader", Mock(return_value=Mock()))
        monkeypatch.setattr("src.annotation.ClinVarLoader", Mock(return_value=Mock()))
        monkeypatch.setattr("src.annotation.DbNSFPLoader", Mock(return_value=Mock()))
        monkeypatch.setattr("src.annotation.GnomADLoader", Mock(return_value=Mock()))
    except (ImportError, AttributeError):
        # If imports fail, still try to mock the modules
        pass
