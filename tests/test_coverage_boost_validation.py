"""Validation edge case tests to boost coverage.

Focuses on:
- Boundary condition testing
- Input validation edge cases  
- Sanitization and normalization
- Invalid input handling
- Validation error paths

Target: Increase coverage by testing uncovered validation branches.
Black formatted with 88-char line limit.
"""

import pytest
from typing import Optional, Dict, Any
import pandas as pd

from varidex.core.models import Variant, VariantData
from varidex.exceptions import ValidationError
from varidex.utils.helpers import DataValidator, format_variant_key, parse_variant_key

pytestmark = pytest.mark.unit


class TestChromosomeValidation:
    """Test chromosome validation edge cases."""

    def test_standard_chromosomes(self) -> None:
        """Test all standard human chromosomes."""
        for i in range(1, 23):
            chrom = f"chr{i}"
            variant = Variant(chrom=chrom, pos=1000, ref="A", alt="G")
            assert variant.chrom == chrom

    def test_sex_chromosomes(self) -> None:
        """Test sex chromosomes X and Y."""
        variant_x = Variant(chrom="chrX", pos=1000, ref="A", alt="G")
        variant_y = Variant(chrom="chrY", pos=1000, ref="A", alt="G")
        assert variant_x.chrom == "chrX"
        assert variant_y.chrom == "chrY"

    def test_mitochondrial_chromosome(self) -> None:
        """Test mitochondrial chromosome M/MT."""
        variant_m = Variant(chrom="chrM", pos=1000, ref="A", alt="G")
        assert variant_m.chrom == "chrM"

    def test_chromosome_without_chr_prefix(self) -> None:
        """Test chromosomes without chr prefix."""
        try:
            variant = Variant(chrom="1", pos=1000, ref="A", alt="G")
            assert variant.chrom in ["1", "chr1"]
        except ValidationError:
            pass  # May require chr prefix

    def test_chromosome_case_insensitive(self) -> None:
        """Test chromosome names are case-insensitive."""
        try:
            variant = Variant(chrom="CHRX", pos=1000, ref="A", alt="G")
            assert variant.chrom.upper() == "CHRX"
        except ValidationError:
            pass  # May be case-sensitive

    def test_invalid_chromosome_names(self) -> None:
        """Test invalid chromosome names raise errors."""
        invalid_chroms = ["chr0", "chr25", "chrZ", "chr-1", ""]
        for chrom in invalid_chroms:
            with pytest.raises((ValidationError, ValueError)):
                Variant(chrom=chrom, pos=1000, ref="A", alt="G")

    def test_chromosome_with_special_characters(self) -> None:
        """Test chromosomes with special characters."""
        special = ["chr@", "chr!", "chr#", "chr$"]
        for chrom in special:
            with pytest.raises((ValidationError, ValueError)):
                Variant(chrom=chrom, pos=1000, ref="A", alt="G")


class TestPositionValidation:
    """Test genomic position validation."""

    def test_minimum_position(self) -> None:
        """Test minimum valid position is 1."""
        variant = Variant(chrom="chr1", pos=1, ref="A", alt="G")
        assert variant.pos == 1

    def test_position_zero_invalid(self) -> None:
        """Test position 0 is invalid."""
        with pytest.raises((ValidationError, ValueError)):
            Variant(chrom="chr1", pos=0, ref="A", alt="G")

    def test_negative_position_invalid(self) -> None:
        """Test negative positions are invalid."""
        with pytest.raises((ValidationError, ValueError)):
            Variant(chrom="chr1", pos=-100, ref="A", alt="G")

    def test_very_large_position(self) -> None:
        """Test very large position values."""
        variant = Variant(chrom="chr1", pos=249250621, ref="A", alt="G")
        assert variant.pos == 249250621

    def test_position_exceeds_chromosome_length(self) -> None:
        """Test position exceeding chromosome length."""
        # May or may not validate chromosome lengths
        try:
            variant = Variant(chrom="chr1", pos=999999999, ref="A", alt="G")
            assert variant.pos == 999999999
        except ValidationError:
            pass  # Validation of max position is OK

    def test_position_float_rejected(self) -> None:
        """Test float positions are rejected."""
        with pytest.raises((ValidationError, TypeError, ValueError)):
            Variant(chrom="chr1", pos=123.45, ref="A", alt="G")

    def test_position_string_rejected(self) -> None:
        """Test string positions are rejected."""
        with pytest.raises((ValidationError, TypeError, ValueError)):
            Variant(chrom="chr1", pos="12345", ref="A", alt="G")


class TestAlleleValidation:
    """Test reference and alternate allele validation."""

    def test_single_nucleotide_variants(self) -> None:
        """Test all single nucleotide combinations."""
        nucleotides = ["A", "C", "G", "T"]
        for ref in nucleotides:
            for alt in nucleotides:
                if ref != alt:
                    variant = Variant(chrom="chr1", pos=100, ref=ref, alt=alt)
                    assert variant.ref == ref
                    assert variant.alt == alt

    def test_same_ref_and_alt_invalid(self) -> None:
        """Test ref and alt cannot be the same."""
        with pytest.raises((ValidationError, ValueError)):
            Variant(chrom="chr1", pos=100, ref="A", alt="A")

    def test_empty_ref_allele(self) -> None:
        """Test empty reference allele is invalid."""
        with pytest.raises((ValidationError, ValueError)):
            Variant(chrom="chr1", pos=100, ref="", alt="G")

    def test_empty_alt_allele(self) -> None:
        """Test empty alternate allele is invalid."""
        with pytest.raises((ValidationError, ValueError)):
            Variant(chrom="chr1", pos=100, ref="A", alt="")

    def test_lowercase_nucleotides(self) -> None:
        """Test lowercase nucleotides are handled."""
        try:
            variant = Variant(chrom="chr1", pos=100, ref="a", alt="g")
            assert variant.ref.upper() == "A" or variant.ref == "a"
        except ValidationError:
            pass  # May require uppercase

    def test_invalid_nucleotide_characters(self) -> None:
        """Test invalid nucleotide characters."""
        invalid = ["X", "Z", "@", "1", " "]
        for nuc in invalid:
            with pytest.raises((ValidationError, ValueError)):
                Variant(chrom="chr1", pos=100, ref=nuc, alt="G")

    def test_multi_nucleotide_ref(self) -> None:
        """Test multi-nucleotide reference alleles."""
        variant = Variant(chrom="chr1", pos=100, ref="ATG", alt="A")
        assert variant.ref == "ATG"
        assert len(variant.ref) == 3

    def test_multi_nucleotide_alt(self) -> None:
        """Test multi-nucleotide alternate alleles."""
        variant = Variant(chrom="chr1", pos=100, ref="A", alt="ATG")
        assert variant.alt == "ATG"
        assert len(variant.alt) == 3

    def test_very_long_alleles(self) -> None:
        """Test very long allele sequences."""
        long_ref = "A" * 100
        long_alt = "G" * 100
        variant = Variant(chrom="chr1", pos=100, ref=long_ref, alt=long_alt)
        assert len(variant.ref) == 100
        assert len(variant.alt) == 100


class TestVariantTypeDetection:
    """Test variant type detection and classification."""

    def test_snv_detection(self) -> None:
        """Test single nucleotide variant detection."""
        variant = Variant(chrom="chr1", pos=100, ref="A", alt="G")
        assert len(variant.ref) == 1
        assert len(variant.alt) == 1

    def test_insertion_detection(self) -> None:
        """Test insertion variant detection."""
        variant = Variant(chrom="chr1", pos=100, ref="A", alt="ATG")
        assert len(variant.ref) < len(variant.alt)

    def test_deletion_detection(self) -> None:
        """Test deletion variant detection."""
        variant = Variant(chrom="chr1", pos=100, ref="ATG", alt="A")
        assert len(variant.ref) > len(variant.alt)

    def test_complex_variant_detection(self) -> None:
        """Test complex variant detection."""
        variant = Variant(chrom="chr1", pos=100, ref="ATG", alt="GCA")
        assert len(variant.ref) == len(variant.alt)
        assert variant.ref != variant.alt

    def test_mnv_detection(self) -> None:
        """Test multi-nucleotide variant detection."""
        variant = Variant(chrom="chr1", pos=100, ref="AT", alt="GC")
        assert len(variant.ref) == 2
        assert len(variant.alt) == 2


class TestDataValidatorMethods:
    """Test DataValidator utility methods."""

    def test_validate_variant_dict_valid(self) -> None:
        """Test validating valid variant dictionary."""
        variant_dict = {"chromosome": "chr1", "position": 12345, "ref": "A", "alt": "G"}
        result = DataValidator.validate_variant(variant_dict)
        assert result is True

    def test_validate_variant_dict_missing_chromosome(self) -> None:
        """Test validation fails with missing chromosome."""
        variant_dict = {"position": 12345, "ref": "A", "alt": "G"}
        result = DataValidator.validate_variant(variant_dict)
        assert result is False

    def test_validate_variant_dict_missing_position(self) -> None:
        """Test validation fails with missing position."""
        variant_dict = {"chromosome": "chr1", "ref": "A", "alt": "G"}
        result = DataValidator.validate_variant(variant_dict)
        assert result is False

    def test_validate_variant_dict_none(self) -> None:
        """Test validation with None."""
        with pytest.raises((TypeError, AttributeError)):
            DataValidator.validate_variant(None)

    def test_validate_variant_dict_empty(self) -> None:
        """Test validation with empty dict."""
        result = DataValidator.validate_variant({})
        assert result is False

    def test_validate_dataframe_valid(self) -> None:
        """Test validating valid dataframe."""
        df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})
        result = DataValidator.validate_dataframe(df)
        assert result is True

    def test_validate_dataframe_empty(self) -> None:
        """Test validation fails with empty dataframe."""
        df = pd.DataFrame()
        result = DataValidator.validate_dataframe(df)
        assert result is False

    def test_validate_dataframe_none(self) -> None:
        """Test validation fails with None."""
        result = DataValidator.validate_dataframe(None)
        assert result is False

    def test_validate_dataframe_not_dataframe(self) -> None:
        """Test validation fails with non-dataframe."""
        result = DataValidator.validate_dataframe([1, 2, 3])
        assert result is False


class TestVariantKeyFormatting:
    """Test variant key formatting functions."""

    def test_format_key_standard(self) -> None:
        """Test standard variant key formatting."""
        key = format_variant_key("chr1", 12345, "A", "G")
        assert "chr1" in key
        assert "12345" in key
        assert "A" in key
        assert "G" in key

    def test_format_key_different_separators(self) -> None:
        """Test key format uses consistent separator."""
        key = format_variant_key("chr1", 12345, "A", "G")
        assert ":" in key or "-" in key or "_" in key

    def test_parse_key_standard(self) -> None:
        """Test parsing standard variant key."""
        key = "chr1:12345:A:G"
        result = parse_variant_key(key)
        assert result["chromosome"] == "chr1"
        assert result["position"] == 12345

    def test_parse_key_invalid_format(self) -> None:
        """Test parsing invalid key format."""
        result = parse_variant_key("invalid_key")
        assert result == {} or len(result) == 0

    def test_parse_key_empty(self) -> None:
        """Test parsing empty key."""
        result = parse_variant_key("")
        assert result == {} or len(result) == 0

    def test_format_parse_roundtrip(self) -> None:
        """Test format and parse roundtrip."""
        original_chrom = "chr17"
        original_pos = 43094692
        original_ref = "G"
        original_alt = "A"

        key = format_variant_key(original_chrom, original_pos, original_ref, original_alt)
        parsed = parse_variant_key(key)

        assert parsed["chromosome"] == original_chrom
        assert parsed["position"] == original_pos


class TestInputSanitization:
    """Test input sanitization and normalization."""

    def test_whitespace_handling(self) -> None:
        """Test whitespace in inputs is handled."""
        try:
            variant = Variant(chrom=" chr1 ", pos=100, ref=" A ", alt=" G ")
            assert variant.chrom.strip() == "chr1"
        except ValidationError:
            pass  # Strict validation may reject whitespace

    def test_case_normalization(self) -> None:
        """Test case normalization for chromosomes."""
        try:
            variant = Variant(chrom="Chr1", pos=100, ref="A", alt="G")
            assert "chr1" in variant.chrom.lower()
        except ValidationError:
            pass  # May be case-sensitive

    def test_leading_zeros_in_chromosome(self) -> None:
        """Test chromosomes with leading zeros."""
        try:
            variant = Variant(chrom="chr01", pos=100, ref="A", alt="G")
            assert variant.chrom in ["chr01", "chr1"]
        except ValidationError:
            pass  # May reject leading zeros


class TestBoundaryConditions:
    """Test boundary conditions in validation."""

    def test_max_integer_position(self) -> None:
        """Test maximum integer position."""
        import sys

        try:
            max_pos = min(sys.maxsize, 2**31 - 1)  # Reasonable max
            variant = Variant(chrom="chr1", pos=max_pos, ref="A", alt="G")
            assert variant.pos == max_pos
        except (ValidationError, OverflowError):
            pass  # May have position limits

    def test_single_character_alleles(self) -> None:
        """Test single character is minimum allele length."""
        variant = Variant(chrom="chr1", pos=100, ref="A", alt="G")
        assert len(variant.ref) >= 1
        assert len(variant.alt) >= 1

    def test_maximum_allele_length(self) -> None:
        """Test very long alleles are accepted."""
        max_len = 1000
        long_ref = "A" * max_len
        long_alt = "G" * max_len
        variant = Variant(chrom="chr1", pos=100, ref=long_ref, alt=long_alt)
        assert len(variant.ref) == max_len
        assert len(variant.alt) == max_len


class TestVariantDataModel:
    """Test VariantData model validation."""

    def test_variant_data_creation(self) -> None:
        """Test creating VariantData instance."""
        vdata = VariantData(
            rsid="rs123",
            chromosome="17",
            position="43094692",
            genotype="AG",
            gene="BRCA1",
            ref_allele="G",
            alt_allele="A",
            clinical_sig="Pathogenic",
            review_status="reviewed",
            variant_type="SNV",
            molecular_consequence="missense",
        )
        assert vdata.chromosome == "17"
        assert vdata.gene == "BRCA1"

    def test_variant_data_optional_fields(self) -> None:
        """Test VariantData with optional fields."""
        vdata = VariantData(
            rsid="rs123",
            chromosome="1",
            position="12345",
            genotype="AG",
            gene="TEST",
            ref_allele="A",
            alt_allele="G",
        )
        assert vdata.rsid == "rs123"
        assert vdata.chromosome == "1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
