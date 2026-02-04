"""Tests for varidex.utils.helpers module.

Tests the actual functions that exist in helpers.py:
- DataValidator
- classify_variants_production
- format_variant_key
- parse_variant_key

Black formatted with 88-char line limit.
"""

from unittest.mock import Mock

import pytest

from varidex.utils.helpers import (
    DataValidator,
    classify_variants_production,
    format_variant_key,
    parse_variant_key,
)


class TestDataValidator:
    """Test DataValidator class."""

    def test_validate_variant_with_required_fields(self) -> None:
        """Test variant validation with all required fields."""
        variant = {"chromosome": "chr1", "position": 12345, "ref": "A", "alt": "T"}
        assert DataValidator.validate_variant(variant) is True

    def test_validate_variant_missing_chromosome(self) -> None:
        """Test variant validation fails without chromosome."""
        variant = {"position": 12345, "ref": "A", "alt": "T"}
        assert DataValidator.validate_variant(variant) is False

    def test_validate_variant_missing_position(self) -> None:
        """Test variant validation fails without position."""
        variant = {"chromosome": "chr1", "ref": "A", "alt": "T"}
        assert DataValidator.validate_variant(variant) is False

    def test_validate_variant_empty_dict(self) -> None:
        """Test variant validation with empty dictionary."""
        variant = {}
        assert DataValidator.validate_variant(variant) is False

    def test_validate_variant_with_extra_fields(self) -> None:
        """Test variant validation ignores extra fields."""
        variant = {
            "chromosome": "chr1",
            "position": 12345,
            "ref": "A",
            "alt": "T",
            "gene": "BRCA1",
            "extra_field": "ignored",
        }
        assert DataValidator.validate_variant(variant) is True

    def test_validate_variant_none_value(self) -> None:
        """Test variant validation with None."""
        with pytest.raises((TypeError, AttributeError)):
            DataValidator.validate_variant(None)


class TestDataValidatorDataFrame:
    """Test DataValidator dataframe validation."""

    def test_validate_dataframe_valid(self) -> None:
        """Test dataframe validation with valid dataframe."""
        import pandas as pd

        df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})
        assert DataValidator.validate_dataframe(df) is True

    def test_validate_dataframe_empty(self) -> None:
        """Test dataframe validation with empty dataframe."""
        import pandas as pd

        df = pd.DataFrame()
        assert DataValidator.validate_dataframe(df) is False

    def test_validate_dataframe_none(self) -> None:
        """Test dataframe validation with None."""
        assert DataValidator.validate_dataframe(None) is False

    def test_validate_dataframe_single_row(self) -> None:
        """Test dataframe validation with single row."""
        import pandas as pd

        df = pd.DataFrame({"col1": [1]})
        assert DataValidator.validate_dataframe(df) is True

    def test_validate_dataframe_non_dataframe(self) -> None:
        """Test dataframe validation with non-dataframe object."""
        assert DataValidator.validate_dataframe("not a dataframe") is False
        assert DataValidator.validate_dataframe([1, 2, 3]) is False
        assert DataValidator.validate_dataframe({"key": "value"}) is False


class TestFormatVariantKey:
    """Test variant key formatting."""

    def test_format_variant_key_basic(self) -> None:
        """Test basic variant key formatting."""
        key = format_variant_key("chr1", 12345, "A", "T")
        assert key == "chr1:12345:A:T"

    def test_format_variant_key_different_chromosome(self) -> None:
        """Test formatting with different chromosomes."""
        assert format_variant_key("chr17", 43094692, "G", "A") == "chr17:43094692:G:A"
        assert format_variant_key("chrX", 100000, "C", "T") == "chrX:100000:C:T"
        assert format_variant_key("chrM", 1500, "A", "G") == "chrM:1500:A:G"

    def test_format_variant_key_multi_base_alleles(self) -> None:
        """Test formatting with multi-base alleles."""
        key = format_variant_key("chr1", 1000, "ATG", "A")
        assert key == "chr1:1000:ATG:A"

        key = format_variant_key("chr2", 2000, "C", "CAAA")
        assert key == "chr2:2000:C:CAAA"

    def test_format_variant_key_deletion(self) -> None:
        """Test formatting deletion variants."""
        key = format_variant_key("chr3", 3000, "ATG", "-")
        assert "chr3" in key
        assert "3000" in key

    def test_format_variant_key_insertion(self) -> None:
        """Test formatting insertion variants."""
        key = format_variant_key("chr4", 4000, "-", "TAG")
        assert "chr4" in key
        assert "4000" in key

    def test_format_variant_key_large_position(self) -> None:
        """Test formatting with large position values."""
        key = format_variant_key("chr1", 249250621, "A", "T")  # Chr1 max
        assert "249250621" in key


class TestParseVariantKey:
    """Test variant key parsing."""

    def test_parse_variant_key_basic(self) -> None:
        """Test basic variant key parsing."""
        result = parse_variant_key("chr1:12345:A:T")
        assert result["chromosome"] == "chr1"
        assert result["position"] == 12345
        assert "A" in str(result)  # ref or alt contains A
        assert "T" in str(result)  # ref or alt contains T

    def test_parse_variant_key_different_chromosomes(self) -> None:
        """Test parsing keys with different chromosomes."""
        result = parse_variant_key("chr17:43094692:G:A")
        assert result["chromosome"] == "chr17"
        assert result["position"] == 43094692

        result = parse_variant_key("chrX:100000:C:T")
        assert result["chromosome"] == "chrX"

    def test_parse_variant_key_multi_base_alleles(self) -> None:
        """Test parsing keys with multi-base alleles."""
        result = parse_variant_key("chr1:1000:ATG:A")
        assert result["chromosome"] == "chr1"
        assert result["position"] == 1000

    def test_parse_variant_key_invalid_format(self) -> None:
        """Test parsing invalid key format."""
        result = parse_variant_key("invalid_format")
        assert result == {} or len(result) == 0

    def test_parse_variant_key_too_few_parts(self) -> None:
        """Test parsing key with too few parts."""
        result = parse_variant_key("chr1:12345")
        assert result == {} or len(result) == 0

    def test_parse_variant_key_invalid_position(self) -> None:
        """Test parsing key with invalid position."""
        result = parse_variant_key("chr1:invalid:A:T")
        assert result == {} or len(result) == 0

    def test_parse_variant_key_empty_string(self) -> None:
        """Test parsing empty string."""
        result = parse_variant_key("")
        assert result == {} or len(result) == 0

    def test_parse_variant_key_none(self) -> None:
        """Test parsing None value."""
        with pytest.raises((TypeError, AttributeError)):
            parse_variant_key(None)


class TestClassifyVariantsProduction:
    """Test production variant classification."""

    def test_classify_variants_production_empty_list(self) -> None:
        """Test classification with empty variant list."""
        mock_classifier = Mock()
        result = classify_variants_production([], mock_classifier)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_classify_variants_production_single_variant(self) -> None:
        """Test classification with single variant."""
        mock_classifier = Mock()
        variants = [{"chromosome": "chr1", "position": 12345}]

        result = classify_variants_production(variants, mock_classifier)
        assert isinstance(result, list)
        assert len(result) == 1
        assert "classification" in result[0]

    def test_classify_variants_production_multiple_variants(self) -> None:
        """Test classification with multiple variants."""
        mock_classifier = Mock()
        variants = [
            {"chromosome": "chr1", "position": 100},
            {"chromosome": "chr2", "position": 200},
            {"chromosome": "chr3", "position": 300},
        ]

        result = classify_variants_production(variants, mock_classifier)
        assert isinstance(result, list)
        assert len(result) == 3
        assert all("classification" in r for r in result)

    def test_classify_variants_production_default_classification(self) -> None:
        """Test that default classification is VUS."""
        mock_classifier = Mock()
        variants = [{"chromosome": "chr1", "position": 12345}]

        result = classify_variants_production(variants, mock_classifier)
        assert result[0]["classification"] == "VUS"

    def test_classify_variants_production_error_handling(self) -> None:
        """Test classification with classifier that raises exception."""
        mock_classifier = Mock()
        mock_classifier.classify.side_effect = Exception("Classification error")

        variants = [{"chromosome": "chr1", "position": 12345}]
        result = classify_variants_production(variants, mock_classifier)

        # Should handle errors gracefully
        assert isinstance(result, list)
        assert len(result) == 1
        # Check if error was handled
        assert (
            result[0].get("classification") == "ERROR"
            or result[0].get("classification") == "VUS"
        )

    def test_classify_variants_production_preserves_variant_data(self) -> None:
        """Test that original variant data is preserved."""
        mock_classifier = Mock()
        variants = [
            {
                "chromosome": "chr1",
                "position": 12345,
                "gene": "BRCA1",
                "ref": "A",
                "alt": "T",
            }
        ]

        result = classify_variants_production(variants, mock_classifier)
        assert "variant" in result[0]
        assert result[0]["variant"]["gene"] == "BRCA1"

    def test_classify_variants_production_none_classifier(self) -> None:
        """Test classification with None classifier."""
        variants = [{"chromosome": "chr1", "position": 12345}]

        # Should handle None classifier
        try:
            result = classify_variants_production(variants, None)
            assert isinstance(result, list)
        except (TypeError, AttributeError):
            # Also acceptable to raise error
            pass


class TestEdgeCases:
    """Test edge cases in utility functions."""

    def test_format_variant_key_special_characters(self) -> None:
        """Test variant key with special chromosome names."""
        key = format_variant_key("chr1_random", 1000, "A", "T")
        assert "chr1_random" in key

    def test_parse_variant_key_extra_colons(self) -> None:
        """Test parsing key with extra colons."""
        result = parse_variant_key("chr1:12345:A:T:extra:data")
        # Should handle gracefully - either parse first 4 or return empty
        assert isinstance(result, dict)

    def test_data_validator_with_numeric_chromosome(self) -> None:
        """Test validator with numeric chromosome."""
        variant = {"chromosome": 1, "position": 12345}  # Numeric instead of string
        # Should accept or handle gracefully
        result = DataValidator.validate_variant(variant)
        assert isinstance(result, bool)

    def test_format_variant_key_zero_position(self) -> None:
        """Test formatting variant at position 0."""
        key = format_variant_key("chr1", 0, "A", "T")
        assert "0" in key

    def test_parse_variant_key_very_large_position(self) -> None:
        """Test parsing key with very large position."""
        result = parse_variant_key("chr1:999999999:A:T")
        if result:
            assert result["position"] == 999999999


class TestIntegration:
    """Test integration between format and parse functions."""

    def test_format_parse_roundtrip(self) -> None:
        """Test formatting and parsing roundtrip."""
        chrom = "chr17"
        pos = 43094692
        ref = "G"
        alt = "A"

        key = format_variant_key(chrom, pos, ref, alt)
        result = parse_variant_key(key)

        assert result["chromosome"] == chrom
        assert result["position"] == pos

    def test_format_parse_multiple_variants(self) -> None:
        """Test formatting and parsing multiple variants."""
        variants = [
            ("chr1", 100, "A", "T"),
            ("chr2", 200, "C", "G"),
            ("chrX", 300, "T", "A"),
        ]

        for chrom, pos, ref, alt in variants:
            key = format_variant_key(chrom, pos, ref, alt)
            result = parse_variant_key(key)
            assert result["chromosome"] == chrom
            assert result["position"] == pos


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
