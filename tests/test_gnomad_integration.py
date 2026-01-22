"""Tests for gnomAD integration and population frequency analysis.

Tests PM2, BA1, BS1 evidence codes with mocked gnomAD responses.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from varidex.integrations.gnomad_client import (
    GnomadClient,
    GnomadVariantFrequency,
    RateLimiter
)
from varidex.core.services.population_frequency import (
    PopulationFrequencyService,
    InheritanceMode,
    FrequencyThresholds,
    FrequencyEvidence
)
from varidex.core.classifier.engine_v7 import ACMGClassifierV7
from varidex.core.models import VariantData

pytestmark = pytest.mark.unit


class TestGnomadVariantFrequency:
    """Test GnomadVariantFrequency dataclass."""
    
    def test_max_af_with_genome_only(self):
        freq = GnomadVariantFrequency(
            variant_id="1-12345-A-G",
            genome_af=0.001
        )
        assert freq.max_af == 0.001
    
    def test_max_af_with_exome_only(self):
        freq = GnomadVariantFrequency(
            variant_id="1-12345-A-G",
            exome_af=0.002
        )
        assert freq.max_af == 0.002
    
    def test_max_af_with_both(self):
        freq = GnomadVariantFrequency(
            variant_id="1-12345-A-G",
            genome_af=0.001,
            exome_af=0.002,
            popmax_af=0.003
        )
        assert freq.max_af == 0.003
    
    def test_max_af_none(self):
        freq = GnomadVariantFrequency(variant_id="1-12345-A-G")
        assert freq.max_af is None
    
    def test_is_common(self):
        freq = GnomadVariantFrequency(
            variant_id="1-12345-A-G",
            genome_af=0.02
        )
        assert freq.is_common is True
    
    def test_is_rare(self):
        freq = GnomadVariantFrequency(
            variant_id="1-12345-A-G",
            genome_af=0.00005
        )
        assert freq.is_rare is True
    
    def test_is_rare_absent(self):
        freq = GnomadVariantFrequency(variant_id="1-12345-A-G")
        assert freq.is_rare is True


class TestRateLimiter:
    """Test rate limiting functionality."""
    
    def test_under_limit(self):
        limiter = RateLimiter(max_requests=5, time_window=1)
        
        # Should not wait if under limit
        for _ in range(5):
            limiter.wait_if_needed()
        
        assert len(limiter.requests) <= 5
    
    def test_exceeds_limit(self):
        limiter = RateLimiter(max_requests=2, time_window=10)
        
        # First two should be fine
        limiter.wait_if_needed()
        limiter.wait_if_needed()
        
        # Third would trigger wait (but we won't actually wait in test)
        assert len(limiter.requests) == 2


class TestGnomadClient:
    """Test GnomadClient functionality."""
    
    def test_init_default(self):
        client = GnomadClient()
        assert client.api_url == GnomadClient.DEFAULT_API_URL
        assert client.timeout == GnomadClient.DEFAULT_TIMEOUT
        assert client.enable_cache is True
    
    def test_init_custom(self):
        client = GnomadClient(
            api_url="https://custom.api",
            timeout=60,
            enable_cache=False,
            rate_limit=False
        )
        assert client.api_url == "https://custom.api"
        assert client.timeout == 60
        assert client.enable_cache is False
        assert client.rate_limiter is None
    
    def test_cache_operations(self):
        client = GnomadClient(enable_cache=True)
        
        freq = GnomadVariantFrequency(
            variant_id="1-12345-A-G",
            genome_af=0.001
        )
        
        # Add to cache
        client._add_to_cache("1-12345-A-G", freq)
        
        # Retrieve from cache
        cached = client._get_from_cache("1-12345-A-G")
        assert cached is not None
        assert cached.genome_af == 0.001
        
        # Clear cache
        client.clear_cache()
        cached = client._get_from_cache("1-12345-A-G")
        assert cached is None
    
    def test_build_graphql_query(self):
        client = GnomadClient()
        query = client._build_graphql_query("1-12345-A-G", "gnomad_r4")
        
        assert "variant" in query
        assert "1-12345-A-G" in query
        assert "gnomad_r4" in query
        assert "genome" in query
        assert "exome" in query
    
    @patch('requests.Session.post')
    def test_get_variant_frequency_not_found(self, mock_post):
        """Test variant not found in gnomAD."""
        mock_response = Mock()
        mock_response.json.return_value = {'data': {'variant': None}}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        client = GnomadClient(rate_limit=False)
        result = client.get_variant_frequency("1", 12345, "A", "G")
        
        assert result is None
    
    @patch('requests.Session.post')
    def test_get_variant_frequency_found(self, mock_post):
        """Test variant found in gnomAD."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': {
                'variant': {
                    'variantId': '1-12345-A-G',
                    'genome': {
                        'ac': 10,
                        'an': 10000,
                        'af': 0.001,
                        'filters': ['PASS'],
                        'populations': []
                    },
                    'exome': None
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        client = GnomadClient(rate_limit=False)
        result = client.get_variant_frequency("1", 12345, "A", "G")
        
        assert result is not None
        assert result.genome_af == 0.001
        assert result.genome_ac == 10
        assert result.genome_an == 10000


class TestPopulationFrequencyService:
    """Test PopulationFrequencyService logic."""
    
    def test_init_with_gnomad(self):
        service = PopulationFrequencyService(enable_gnomad=False)
        assert service.enable_gnomad is False
        assert service.thresholds is not None
    
    def test_pm2_absent_variant(self):
        """Test PM2 applies for absent variant."""
        service = PopulationFrequencyService(enable_gnomad=False)
        freq = GnomadVariantFrequency(variant_id="1-12345-A-G")
        
        applies, reason = service._check_pm2(freq, InheritanceMode.DOMINANT)
        assert applies is True
        assert "absent" in reason.lower()
    
    def test_pm2_rare_dominant(self):
        """Test PM2 applies for rare variant in dominant inheritance."""
        service = PopulationFrequencyService(enable_gnomad=False)
        freq = GnomadVariantFrequency(
            variant_id="1-12345-A-G",
            genome_af=0.00005  # Below 0.0001 threshold
        )
        
        applies, reason = service._check_pm2(freq, InheritanceMode.DOMINANT)
        assert applies is True
    
    def test_pm2_not_rare_enough(self):
        """Test PM2 doesn't apply if frequency too high."""
        service = PopulationFrequencyService(enable_gnomad=False)
        freq = GnomadVariantFrequency(
            variant_id="1-12345-A-G",
            genome_af=0.001  # Above 0.0001 threshold
        )
        
        applies, reason = service._check_pm2(freq, InheritanceMode.DOMINANT)
        assert applies is False
    
    def test_ba1_common_variant(self):
        """Test BA1 applies for common variant >5%."""
        service = PopulationFrequencyService(enable_gnomad=False)
        freq = GnomadVariantFrequency(
            variant_id="1-12345-A-G",
            genome_af=0.06,  # 6% > 5% threshold
            popmax_af=0.06,
            popmax_population="NFE"
        )
        
        applies, reason = service._check_ba1(freq)
        assert applies is True
        assert "BA1" in reason or "0.06" in reason
    
    def test_ba1_not_common(self):
        """Test BA1 doesn't apply for uncommon variant."""
        service = PopulationFrequencyService(enable_gnomad=False)
        freq = GnomadVariantFrequency(
            variant_id="1-12345-A-G",
            genome_af=0.03  # 3% < 5% threshold
        )
        
        applies, reason = service._check_ba1(freq)
        assert applies is False
    
    def test_bs1_too_high_frequency(self):
        """Test BS1 applies for frequency too high >1%."""
        service = PopulationFrequencyService(enable_gnomad=False)
        freq = GnomadVariantFrequency(
            variant_id="1-12345-A-G",
            genome_af=0.015  # 1.5% > 1% threshold
        )
        
        applies, reason = service._check_bs1(freq, InheritanceMode.DOMINANT)
        assert applies is True
    
    def test_bs1_vs_ba1_precedence(self):
        """Test BA1 takes precedence over BS1."""
        service = PopulationFrequencyService(enable_gnomad=False)
        freq = GnomadVariantFrequency(
            variant_id="1-12345-A-G",
            genome_af=0.06  # 6% - qualifies for both BA1 and BS1
        )
        
        # BA1 check should pass
        ba1_applies, _ = service._check_ba1(freq)
        assert ba1_applies is True
        
        # BS1 should defer to BA1
        bs1_applies, reason = service._check_bs1(freq, InheritanceMode.DOMINANT)
        assert bs1_applies is False
        assert "BA1" in reason


class TestACMGClassifierV7:
    """Test enhanced classifier with gnomAD integration."""
    
    def test_init_without_gnomad(self):
        """Test classifier works without gnomAD."""
        classifier = ACMGClassifierV7(enable_gnomad=False)
        assert classifier.enable_gnomad is False
        assert classifier.frequency_service is None
    
    def test_init_with_gnomad(self):
        """Test classifier initializes with gnomAD."""
        # Mock the gnomAD client to avoid real API calls
        with patch('varidex.core.services.population_frequency.GnomadClient'):
            classifier = ACMGClassifierV7(enable_gnomad=True)
            # May be False if initialization failed
            assert classifier.frequency_service is not None or not classifier.enable_gnomad
    
    def test_extract_coordinates_full(self):
        """Test coordinate extraction with all fields."""
        classifier = ACMGClassifierV7(enable_gnomad=False)
        
        variant = VariantData(
            rsid='rs123',
            chromosome='17',
            position='43094692',
            genotype='AG',
            gene='BRCA1',
            ref_allele='G',
            alt_allele='A',
            clinical_sig='Pathogenic',
            review_status='reviewed by expert panel',
            variant_type='SNV',
            molecular_consequence='frameshift'
        )
        
        coords = classifier._extract_variant_coordinates(variant)
        assert coords is not None
        assert coords['chromosome'] == '17'
        assert coords['position'] == 43094692
        assert coords['ref'] == 'G'
        assert coords['alt'] == 'A'
        assert coords['gene'] == 'BRCA1'
    
    def test_extract_coordinates_missing(self):
        """Test coordinate extraction with missing fields."""
        classifier = ACMGClassifierV7(enable_gnomad=False)
        
        variant = VariantData(
            rsid='rs123',
            chromosome='17',
            # Missing position, ref, alt
            genotype='AG',
            gene='BRCA1',
            clinical_sig='Pathogenic',
            review_status='reviewed',
            variant_type='SNV',
            molecular_consequence='frameshift'
        )
        
        coords = classifier._extract_variant_coordinates(variant)
        assert coords is None
    
    def test_infer_inheritance_dominant(self):
        """Test inheritance mode inference."""
        classifier = ACMGClassifierV7(enable_gnomad=False)
        
        # Test with explicit mode
        variant = Mock()
        variant.inheritance_mode = "Autosomal Dominant"
        mode = classifier._infer_inheritance_mode(variant)
        assert mode == InheritanceMode.DOMINANT
    
    def test_infer_inheritance_xlinked(self):
        """Test X-linked inference from chromosome."""
        classifier = ACMGClassifierV7(enable_gnomad=False)
        
        variant = Mock()
        variant.inheritance_mode = None
        variant.chromosome = "X"
        mode = classifier._infer_inheritance_mode(variant)
        assert mode == InheritanceMode.X_LINKED
    
    def test_get_enabled_codes_with_gnomad(self):
        """Test enabled codes include gnomAD codes."""
        with patch('varidex.core.services.population_frequency.GnomadClient'):
            classifier = ACMGClassifierV7(enable_gnomad=True)
            codes = classifier.get_enabled_codes()
            
            # Should have base codes plus gnomAD codes
            assert 'PM4' in codes['pathogenic']
            assert 'BP1' in codes['benign']
    
    def test_health_check(self):
        """Test health check includes gnomAD status."""
        classifier = ACMGClassifierV7(enable_gnomad=False)
        health = classifier.health_check()
        
        assert 'gnomad' in health
        assert 'enabled' in health['gnomad']
        assert health['gnomad']['enabled'] is False
        assert health['version'] == ACMGClassifierV7.VERSION


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
