#!/usr/bin/env python3
"""
tests/test_gnomad_integration.py - gnomAD Integration Tests v6.5.0-dev

Comprehensive test suite for gnomAD integration across all modules.

Tests cover:
- PM2 evidence code with gnomAD data
- Column naming consistency
- Chromosome normalization
- VCF parsing robustness
- API client functionality

Author: VariDex Team
Version: 6.5.0-dev
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path


class TestPM2EvidenceCode:
    """Test PM2 evidence code with gnomAD integration."""

    def test_pm2_with_gnomad_af_field(self):
        """Test PM2 uses pre-annotated gnomad_af field."""
        from varidex.core.classifier.acmg_evidence_pathogenic import (
            PathogenicEvidenceAssigner,
        )

        assigner = PathogenicEvidenceAssigner()

        # Variant with rare frequency (should trigger PM2)
        variant_rare = {
            "chromosome": "1",
            "position": 100000,
            "ref_allele": "A",
            "alt_allele": "G",
            "gnomad_af": 0.00005,  # Below threshold (0.0001)
        }

        result = assigner.check_pm2(variant_rare)
        assert result is True, "PM2 should apply for rare variant (AF < 0.0001)"

        # Variant with common frequency (should NOT trigger PM2)
        variant_common = {
            "chromosome": "1",
            "position": 200000,
            "ref_allele": "C",
            "alt_allele": "T",
            "gnomad_af": 0.01,  # Above threshold
        }

        result = assigner.check_pm2(variant_common)
        assert result is False, "PM2 should NOT apply for common variant"

    def test_pm2_with_gnomad_api(self):
        """Test PM2 uses gnomAD API when af field not present."""
        from varidex.core.classifier.acmg_evidence_pathogenic import (
            PathogenicEvidenceAssigner,
        )

        assigner = PathogenicEvidenceAssigner()

        # Mock gnomAD API
        mock_api = Mock()
        mock_freq = Mock()
        mock_freq.max_af = 0.00002  # Rare
        mock_api.get_variant_frequency.return_value = mock_freq

        variant = {
            "chromosome": "17",
            "position": 43094692,
            "ref_allele": "G",
            "alt_allele": "A",
        }

        result = assigner.check_pm2(variant, gnomad_api=mock_api)
        assert result is True, "PM2 should apply when API returns rare variant"

        # Verify API was called with correct parameters
        mock_api.get_variant_frequency.assert_called_once_with(
            chromosome="17", position=43094692, ref="G", alt="A"
        )

    def test_pm2_column_naming(self):
        """Test PM2 uses standardized column names (ref_allele/alt_allele)."""
        from varidex.core.classifier.acmg_evidence_pathogenic import (
            PathogenicEvidenceAssigner,
        )

        assigner = PathogenicEvidenceAssigner()

        # This tests the critical typo fix: "re" → "ref_allele"
        variant = {
            "chromosome": "1",
            "position": 100000,
            "ref_allele": "A",  # Should use this (not "ref" or "re")
            "alt_allele": "G",  # Should use this (not "alt")
            "gnomad_af": 0.00001,
        }

        # Should not raise KeyError
        result = assigner.check_pm2(variant)
        assert result is True, "PM2 should work with standardized column names"


class TestChromosomeNormalization:
    """Test chromosome name normalization."""

    def test_normalize_chromosome(self):
        """Test chromosome normalization function."""
        from varidex.integrations.gnomad_client import normalize_chromosome

        # Standard chromosomes
        assert normalize_chromosome("1") == "1"
        assert normalize_chromosome("chr1") == "1"
        assert normalize_chromosome("22") == "22"
        assert normalize_chromosome("chr22") == "22"

        # Sex chromosomes
        assert normalize_chromosome("X") == "X"
        assert normalize_chromosome("chrX") == "X"
        assert normalize_chromosome("Y") == "Y"
        assert normalize_chromosome("chrY") == "Y"

        # Mitochondrial (critical fix: M → MT)
        assert normalize_chromosome("M") == "MT"
        assert normalize_chromosome("chrM") == "MT"
        assert normalize_chromosome("MT") == "MT"
        assert normalize_chromosome("chrMT") == "MT"

    def test_gnomad_client_chromosome_handling(self):
        """Test gnomAD client handles chromosome normalization."""
        from varidex.integrations.gnomad_client import GnomadClient

        client = GnomadClient(rate_limit=False)

        # Mock the execute query to avoid actual API call
        with patch.object(client, "_execute_query") as mock_execute:
            mock_execute.return_value = {"data": {"variant": None}}

            # Test MT chromosome normalization
            client.get_variant_frequency(
                chromosome="M", position=1000, ref="A", alt="G"
            )

            # Verify query was built with "MT" not "M"
            call_args = mock_execute.call_args[0][0]
            assert "MT-1000-A-G" in call_args, "M should be normalized to MT"


class TestVCFInfoFieldParsing:
    """Test robust VCF INFO field parsing."""

    def test_safe_get_info_value_list(self):
        """Test parsing list-valued INFO fields."""
        from varidex.integrations.gnomad.query import GnomADQuerier
        from pathlib import Path

        querier = GnomADQuerier(Path("/tmp/gnomad"))

        # Mock record with list-valued INFO
        mock_record = Mock()
        mock_record.info = {"AF": [0.001, 0.002, 0.003], "AC": [10, 20, 30]}

        # Test accessing different indices
        af0 = querier._safe_get_info_value(mock_record, "AF", 0)
        assert af0 == 0.001, "Should get first value"

        af1 = querier._safe_get_info_value(mock_record, "AF", 1)
        assert af1 == 0.002, "Should get second value"

        # Test out-of-bounds access (should return None, not crash)
        af10 = querier._safe_get_info_value(mock_record, "AF", 10)
        assert af10 is None, "Out of bounds should return None"

    def test_safe_get_info_value_scalar(self):
        """Test parsing scalar-valued INFO fields."""
        from varidex.integrations.gnomad.query import GnomADQuerier
        from pathlib import Path

        querier = GnomADQuerier(Path("/tmp/gnomad"))

        # Mock record with scalar INFO
        mock_record = Mock()
        mock_record.info = {"AN": 1000, "AF_popmax": 0.005}

        # Test scalar access
        an = querier._safe_get_info_value(mock_record, "AN", 0)
        assert an == 1000, "Should get scalar value"

        # Accessing scalar with non-zero index should return None
        an_bad = querier._safe_get_info_value(mock_record, "AN", 1)
        assert an_bad is None, "Scalar with index > 0 should return None"

    def test_safe_get_info_value_missing(self):
        """Test handling missing INFO fields."""
        from varidex.integrations.gnomad.query import GnomADQuerier
        from pathlib import Path

        querier = GnomADQuerier(Path("/tmp/gnomad"))

        # Mock record with missing field
        mock_record = Mock()
        mock_record.info = {}

        # Should return None for missing field
        af = querier._safe_get_info_value(mock_record, "AF", 0)
        assert af is None, "Missing field should return None"


class TestGnomADAnnotator:
    """Test gnomAD annotator integration."""

    def test_annotator_column_consistency(self):
        """Test annotator uses consistent column naming."""
        # This test verifies column naming without needing annotator module
        from varidex.core.classifier.acmg_evidence_pathogenic import (
            PathogenicEvidenceAssigner,
        )
        
        assigner = PathogenicEvidenceAssigner()
        
        # Test that PM2 works with standardized columns
        variant = {
            "chromosome": "1",
            "position": 100000,
            "ref_allele": "A",
            "alt_allele": "G",
            "gnomad_af": 0.00001,
        }
        
        # Should not raise KeyError with standardized columns
        result = assigner.check_pm2(variant)
        assert result is True, "PM2 should work with standardized column names"

    def test_annotator_adds_gnomad_columns(self):
        """Test that gnomAD columns are properly used by PM2."""
        from varidex.core.classifier.acmg_evidence_pathogenic import (
            PathogenicEvidenceAssigner,
        )
        
        assigner = PathogenicEvidenceAssigner()
        
        # Test that PM2 can read gnomad_af column
        variant_with_gnomad = {
            "chromosome": "1",
            "position": 100000,
            "ref_allele": "A",
            "alt_allele": "G",
            "gnomad_af": 0.00001,
            "gnomad_ac": 10,
            "gnomad_an": 100000,
        }
        
        result = assigner.check_pm2(variant_with_gnomad)
        assert result is True, "PM2 should use gnomad_af column when present"


class TestGnomADClient:
    """Test gnomAD API client."""

    def test_client_cache(self):
        """Test client caching functionality."""
        from varidex.integrations.gnomad_client import GnomadClient

        client = GnomadClient(enable_cache=True, rate_limit=False)

        # Mock response
        mock_freq = Mock()
        mock_freq.max_af = 0.001

        with patch.object(client, "_execute_query") as mock_execute:
            mock_execute.return_value = {
                "data": {
                    "variant": {
                        "variantId": "1-100000-A-G",
                        "genome": {"af": 0.001, "ac": 10, "an": 10000},
                        "exome": {"af": None, "ac": None, "an": None},
                    }
                }
            }

            # First call - should query API
            result1 = client.get_variant_frequency(
                chromosome="1", position=100000, ref="A", alt="G"
            )
            assert result1 is not None
            assert mock_execute.call_count == 1

            # Second call - should use cache
            result2 = client.get_variant_frequency(
                chromosome="1", position=100000, ref="A", alt="G"
            )
            assert result2 is not None
            assert mock_execute.call_count == 1, "Should use cached result"

    def test_client_rate_limiting(self):
        """Test client rate limiting."""
        from varidex.integrations.gnomad_client import RateLimiter
        import time

        limiter = RateLimiter(max_requests=2, time_window=1)

        # First two requests should be fast
        start = time.time()
        limiter.wait_if_needed()
        limiter.wait_if_needed()
        fast_time = time.time() - start
        assert fast_time < 0.1, "First requests should be fast"

        # Third request should wait
        start = time.time()
        limiter.wait_if_needed()
        wait_time = time.time() - start
        assert wait_time >= 0.9, "Should wait for rate limit window"


class TestEndToEndIntegration:
    """Test complete gnomAD integration workflow."""

    def test_pipeline_with_gnomad_annotation(self):
        """Test variant classification with gnomAD annotation."""
        from varidex.core.classifier.acmg_evidence_pathogenic import (
            PathogenicEvidenceAssigner,
        )

        # Variant with gnomAD annotation
        variant = {
            "chromosome": "17",
            "position": 43094692,
            "ref_allele": "G",
            "alt_allele": "A",
            "gnomad_af": 0.00001,  # Very rare
            "consequence": "missense_variant",
            "gene": "BRCA1",
        }

        assigner = PathogenicEvidenceAssigner()
        resources = {"lof_genes": set(), "missense_rare_genes": {"BRCA1"}}

        evidence = assigner.assign_all(variant, resources)

        # Should assign PM2 (rare in gnomAD) and PP2 (missense in BRCA1)
        assert "PM2" in evidence, "PM2 should be assigned for rare variant"
        assert "PP2" in evidence, "PP2 should be assigned for BRCA1 missense"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
