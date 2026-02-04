"""Comprehensive tests for varidex.core.models module.

Tests cover:
- Variant model creation and validation
- Model serialization/deserialization
- Field validation and constraints
- Edge cases and error handling
"""

import pytest

from varidex.core.exceptions import ValidationError
from varidex.core.models import AnnotatedVariant, Variant, VariantClassification


class TestVariantCreation:
    """Test Variant model creation."""

    def test_minimal_variant_creation(self) -> None:
        """Test creating variant with minimal required fields."""
        variant = Variant(
            chrom="chr1",
            pos=12345,
            ref="A",
            alt="G",
        )
        assert variant.chrom == "chr1"
        assert variant.pos == 12345
        assert variant.ref == "A"
        assert variant.alt == "G"

    def test_full_variant_creation(self) -> None:
        """Test creating variant with all fields."""
        variant = Variant(
            chrom="chr17",
            pos=7577548,
            ref="G",
            alt="A",
            gene="TP53",
            rs_id="rs11540652",
            quality_score=95.5,
        )
        assert variant.chrom == "chr17"
        assert variant.pos == 7577548
        assert variant.ref == "G"
        assert variant.alt == "A"
        assert variant.gene == "TP53"
        assert variant.rs_id == "rs11540652"
        assert variant.quality_score == 95.5

    def test_variant_with_optional_fields(self) -> None:
        """Test variant with optional annotation fields."""
        variant = Variant(
            chrom="chr1",
            pos=100,
            ref="C",
            alt="T",
            consequence="missense_variant",
            hgvs_c="c.123G>A",
            hgvs_p="p.Arg41Gln",
        )
        assert variant.consequence == "missense_variant"
        assert variant.hgvs_c == "c.123G>A"
        assert variant.hgvs_p == "p.Arg41Gln"


class TestVariantValidation:
    """Test variant field validation."""

    def test_invalid_chromosome(self) -> None:
        """Test invalid chromosome format raises error."""
        with pytest.raises((ValidationError, ValueError)):
            Variant(chrom="invalid", pos=100, ref="A", alt="G")

    def test_negative_position(self) -> None:
        """Test negative position raises error."""
        with pytest.raises((ValidationError, ValueError)):
            Variant(chrom="chr1", pos=-100, ref="A", alt="G")

    def test_zero_position(self) -> None:
        """Test zero position raises error."""
        with pytest.raises((ValidationError, ValueError)):
            Variant(chrom="chr1", pos=0, ref="A", alt="G")

    def test_empty_ref_allele(self) -> None:
        """Test empty reference allele."""
        with pytest.raises((ValidationError, ValueError)):
            Variant(chrom="chr1", pos=100, ref="", alt="G")

    def test_empty_alt_allele(self) -> None:
        """Test empty alternate allele."""
        with pytest.raises((ValidationError, ValueError)):
            Variant(chrom="chr1", pos=100, ref="A", alt="")

    def test_invalid_nucleotides(self) -> None:
        """Test invalid nucleotide characters."""
        with pytest.raises((ValidationError, ValueError)):
            Variant(chrom="chr1", pos=100, ref="X", alt="G")

    def test_valid_nucleotides(self) -> None:
        """Test all valid nucleotide combinations."""
        for ref in ["A", "C", "G", "T", "N"]:
            for alt in ["A", "C", "G", "T"]:
                if ref != alt:
                    variant = Variant(chrom="chr1", pos=100, ref=ref, alt=alt)
                    assert variant.ref == ref
                    assert variant.alt == alt


class TestVariantIdentifier:
    """Test variant identifier generation."""

    def test_variant_id_generation(self) -> None:
        """Test variant ID is correctly generated."""
        variant = Variant(chrom="chr1", pos=12345, ref="A", alt="G")
        expected_id = "chr1:12345:A>G"
        assert variant.variant_id == expected_id

    def test_unique_variant_ids(self) -> None:
        """Test different variants have different IDs."""
        variant1 = Variant(chrom="chr1", pos=100, ref="A", alt="G")
        variant2 = Variant(chrom="chr1", pos=101, ref="A", alt="G")
        variant3 = Variant(chrom="chr2", pos=100, ref="A", alt="G")
        assert variant1.variant_id != variant2.variant_id
        assert variant1.variant_id != variant3.variant_id
        assert variant2.variant_id != variant3.variant_id

    def test_reproducible_variant_id(self) -> None:
        """Test same variant always gets same ID."""
        variant1 = Variant(chrom="chr1", pos=100, ref="A", alt="G")
        variant2 = Variant(chrom="chr1", pos=100, ref="A", alt="G")
        assert variant1.variant_id == variant2.variant_id


class TestVariantSerialization:
    """Test variant serialization and deserialization."""

    def test_to_dict(self) -> None:
        """Test variant can be converted to dictionary."""
        variant = Variant(chrom="chr1", pos=100, ref="A", alt="G", gene="TEST_GENE")
        variant_dict = variant.to_dict()
        assert isinstance(variant_dict, dict)
        assert variant_dict["chrom"] == "chr1"
        assert variant_dict["pos"] == 100
        assert variant_dict["ref"] == "A"
        assert variant_dict["alt"] == "G"
        assert variant_dict["gene"] == "TEST_GENE"

    def test_from_dict(self) -> None:
        """Test variant can be created from dictionary."""
        variant_dict = {
            "chrom": "chr2",
            "pos": 200,
            "ref": "C",
            "alt": "T",
            "gene": "GENE2",
        }
        variant = Variant.from_dict(variant_dict)
        assert variant.chrom == "chr2"
        assert variant.pos == 200
        assert variant.ref == "C"
        assert variant.alt == "T"
        assert variant.gene == "GENE2"

    def test_round_trip_serialization(self) -> None:
        """Test variant survives round-trip serialization."""
        original = Variant(
            chrom="chr3",
            pos=300,
            ref="G",
            alt="A",
            gene="GENE3",
            quality_score=85.0,
        )
        variant_dict = original.to_dict()
        restored = Variant.from_dict(variant_dict)
        assert original.chrom == restored.chrom
        assert original.pos == restored.pos
        assert original.ref == restored.ref
        assert original.alt == restored.alt
        assert original.gene == restored.gene
        assert original.quality_score == restored.quality_score


class TestVariantClassification:
    """Test VariantClassification model."""

    def test_classification_creation(self) -> None:
        """Test creating variant classification."""
        classification = VariantClassification(
            variant_id="chr1:100:A>G",
            classification="Pathogenic",
            confidence=0.95,
        )
        assert classification.variant_id == "chr1:100:A>G"
        assert classification.classification == "Pathogenic"
        assert classification.confidence == 0.95

    def test_valid_classifications(self) -> None:
        """Test all valid ACMG classifications."""
        valid_classes = [
            "Pathogenic",
            "Likely Pathogenic",
            "Uncertain Significance",
            "Likely Benign",
            "Benign",
        ]
        for cls in valid_classes:
            classification = VariantClassification(
                variant_id="chr1:100:A>G", classification=cls, confidence=0.9
            )
            assert classification.classification == cls

    def test_confidence_range(self) -> None:
        """Test confidence must be between 0 and 1."""
        valid_confidence = VariantClassification(
            variant_id="chr1:100:A>G", classification="Benign", confidence=0.5
        )
        assert 0 <= valid_confidence.confidence <= 1.0

        with pytest.raises((ValidationError, ValueError)):
            VariantClassification(
                variant_id="chr1:100:A>G",
                classification="Benign",
                confidence=1.5,
            )


class TestAnnotatedVariant:
    """Test AnnotatedVariant model with full annotations."""

    def test_annotated_variant_creation(self) -> None:
        """Test creating fully annotated variant."""
        annotated = AnnotatedVariant(
            chrom="chr1",
            pos=100,
            ref="A",
            alt="G",
            gene="TEST",
            consequence="missense_variant",
            gnomad_af=0.001,
            cadd_score=25.0,
            classification="Pathogenic",
        )
        assert annotated.chrom == "chr1"
        assert annotated.consequence == "missense_variant"
        assert annotated.gnomad_af == 0.001
        assert annotated.cadd_score == 25.0
        assert annotated.classification == "Pathogenic"

    def test_gnomad_af_range(self) -> None:
        """Test gnomAD allele frequency range validation."""
        annotated = AnnotatedVariant(
            chrom="chr1", pos=100, ref="A", alt="G", gnomad_af=0.5
        )
        assert 0 <= annotated.gnomad_af <= 1.0

    def test_cadd_score_range(self) -> None:
        """Test CADD score range."""
        annotated = AnnotatedVariant(
            chrom="chr1", pos=100, ref="A", alt="G", cadd_score=30.0
        )
        assert annotated.cadd_score >= 0


class TestVariantComparison:
    """Test variant comparison and equality."""

    def test_equal_variants(self) -> None:
        """Test identical variants are equal."""
        variant1 = Variant(chrom="chr1", pos=100, ref="A", alt="G")
        variant2 = Variant(chrom="chr1", pos=100, ref="A", alt="G")
        assert variant1 == variant2

    def test_different_variants(self) -> None:
        """Test different variants are not equal."""
        variant1 = Variant(chrom="chr1", pos=100, ref="A", alt="G")
        variant2 = Variant(chrom="chr1", pos=101, ref="A", alt="G")
        assert variant1 != variant2

    def test_variant_hash(self) -> None:
        """Test variants can be hashed."""
        variant = Variant(chrom="chr1", pos=100, ref="A", alt="G")
        variant_hash = hash(variant)
        assert isinstance(variant_hash, int)

    def test_variants_in_set(self) -> None:
        """Test variants can be stored in sets."""
        variant1 = Variant(chrom="chr1", pos=100, ref="A", alt="G")
        variant2 = Variant(chrom="chr1", pos=101, ref="A", alt="G")
        variant3 = Variant(chrom="chr1", pos=100, ref="A", alt="G")

        variant_set = {variant1, variant2, variant3}
        assert len(variant_set) == 2


class TestVariantEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_insertion_variant(self) -> None:
        """Test insertion variant (ref shorter than alt)."""
        variant = Variant(chrom="chr1", pos=100, ref="A", alt="ATG")
        assert len(variant.ref) < len(variant.alt)

    def test_deletion_variant(self) -> None:
        """Test deletion variant (ref longer than alt)."""
        variant = Variant(chrom="chr1", pos=100, ref="ATG", alt="A")
        assert len(variant.ref) > len(variant.alt)

    def test_complex_variant(self) -> None:
        """Test complex variant (substitution)."""
        variant = Variant(chrom="chr1", pos=100, ref="ATG", alt="GCA")
        assert len(variant.ref) == len(variant.alt)
        assert variant.ref != variant.alt

    def test_long_alleles(self) -> None:
        """Test handling of long alleles."""
        long_ref = "A" * 100
        long_alt = "G" * 100
        variant = Variant(chrom="chr1", pos=100, ref=long_ref, alt=long_alt)
        assert variant.ref == long_ref
        assert variant.alt == long_alt

    def test_max_chromosome_position(self) -> None:
        """Test maximum chromosome position."""
        variant = Variant(chrom="chr1", pos=249250621, ref="A", alt="G")  # chr1 length
        assert variant.pos == 249250621

    def test_sex_chromosomes(self) -> None:
        """Test variants on sex chromosomes."""
        variant_x = Variant(chrom="chrX", pos=100, ref="A", alt="G")
        variant_y = Variant(chrom="chrY", pos=100, ref="A", alt="G")
        assert variant_x.chrom == "chrX"
        assert variant_y.chrom == "chrY"

    def test_mitochondrial_variant(self) -> None:
        """Test mitochondrial variant."""
        variant = Variant(chrom="chrM", pos=100, ref="A", alt="G")
        assert variant.chrom == "chrM"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
