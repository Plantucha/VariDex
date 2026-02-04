"""Tests for varidex.pipeline.validators module.

Black formatted with 88-char line limit.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from varidex.core.models import GenomicVariant
from varidex.exceptions import ValidationError
from varidex.pipeline.validators import (
    validate_assembly,
    validate_chromosome,
    validate_coordinates,
    validate_reference_allele,
    validate_variant,
    validate_vcf_file,
)


class TestValidateChromosome:
    """Test chromosome validation."""

    def test_validate_chromosome_valid_autosome(self) -> None:
        """Test validation of valid autosomal chromosome."""
        assert validate_chromosome("chr1") is True
        assert validate_chromosome("1") is True
        assert validate_chromosome("chr22") is True
        assert validate_chromosome("22") is True

    def test_validate_chromosome_valid_sex_chromosome(self) -> None:
        """Test validation of valid sex chromosomes."""
        assert validate_chromosome("chrX") is True
        assert validate_chromosome("X") is True
        assert validate_chromosome("chrY") is True
        assert validate_chromosome("Y") is True

    def test_validate_chromosome_valid_mitochondrial(self) -> None:
        """Test validation of mitochondrial chromosome."""
        assert validate_chromosome("chrM") is True
        assert validate_chromosome("M") is True
        assert validate_chromosome("MT") is True

    def test_validate_chromosome_invalid(self) -> None:
        """Test validation of invalid chromosome."""
        assert validate_chromosome("chr25") is False
        assert validate_chromosome("chrZ") is False
        assert validate_chromosome("") is False
        assert validate_chromosome("invalid") is False

    def test_validate_chromosome_none(self) -> None:
        """Test validation with None value."""
        assert validate_chromosome(None) is False


class TestValidateCoordinates:
    """Test genomic coordinates validation."""

    def test_validate_coordinates_valid(self) -> None:
        """Test validation of valid coordinates."""
        assert validate_coordinates("chr1", 100000, 100001) is True
        assert validate_coordinates("X", 1, 1000000) is True

    def test_validate_coordinates_negative_position(self) -> None:
        """Test validation with negative position."""
        assert validate_coordinates("chr1", -100, 100) is False

    def test_validate_coordinates_zero_position(self) -> None:
        """Test validation with zero position."""
        assert validate_coordinates("chr1", 0, 100) is False

    def test_validate_coordinates_end_before_start(self) -> None:
        """Test validation when end position is before start."""
        assert validate_coordinates("chr1", 100, 50) is False

    def test_validate_coordinates_invalid_chromosome(self) -> None:
        """Test validation with invalid chromosome."""
        assert validate_coordinates("chr99", 100, 200) is False

    def test_validate_coordinates_large_span(self) -> None:
        """Test validation of large coordinate span."""
        assert validate_coordinates("chr1", 1, 249250621) is True


class TestValidateReferenceAllele:
    """Test reference allele validation."""

    def test_validate_reference_allele_valid_single_nucleotide(self) -> None:
        """Test validation of valid single nucleotide."""
        assert validate_reference_allele("A") is True
        assert validate_reference_allele("C") is True
        assert validate_reference_allele("G") is True
        assert validate_reference_allele("T") is True

    def test_validate_reference_allele_valid_sequence(self) -> None:
        """Test validation of valid nucleotide sequence."""
        assert validate_reference_allele("ACGT") is True
        assert validate_reference_allele("GCTA") is True

    def test_validate_reference_allele_lowercase(self) -> None:
        """Test validation handles lowercase nucleotides."""
        assert validate_reference_allele("acgt") is True
        assert validate_reference_allele("GcTa") is True

    def test_validate_reference_allele_invalid_characters(self) -> None:
        """Test validation rejects invalid characters."""
        assert validate_reference_allele("ACGTN") is False
        assert validate_reference_allele("ACG-T") is False
        assert validate_reference_allele("123") is False

    def test_validate_reference_allele_empty(self) -> None:
        """Test validation of empty allele."""
        assert validate_reference_allele("") is False

    def test_validate_reference_allele_none(self) -> None:
        """Test validation with None value."""
        assert validate_reference_allele(None) is False

    def test_validate_reference_allele_deletion(self) -> None:
        """Test validation of deletion representation."""
        assert validate_reference_allele("-") is True


class TestValidateAssembly:
    """Test genome assembly validation."""

    def test_validate_assembly_grch37(self) -> None:
        """Test validation of GRCh37 assemblies."""
        assert validate_assembly("GRCh37") is True
        assert validate_assembly("hg19") is True

    def test_validate_assembly_grch38(self) -> None:
        """Test validation of GRCh38 assemblies."""
        assert validate_assembly("GRCh38") is True
        assert validate_assembly("hg38") is True

    def test_validate_assembly_case_insensitive(self) -> None:
        """Test validation is case-insensitive."""
        assert validate_assembly("grch38") is True
        assert validate_assembly("HG38") is True

    def test_validate_assembly_invalid(self) -> None:
        """Test validation rejects invalid assemblies."""
        assert validate_assembly("GRCh36") is False
        assert validate_assembly("mm10") is False
        assert validate_assembly("") is False

    def test_validate_assembly_none(self) -> None:
        """Test validation with None value."""
        assert validate_assembly(None) is False


class TestValidateVariant:
    """Test variant object validation."""

    def test_validate_variant_valid(self) -> None:
        """Test validation of valid variant."""
        variant = GenomicVariant(
            chromosome="chr1",
            position=12345,
            ref_allele="A",
            alt_allele="G",
            assembly="GRCh38",
        )
        assert validate_variant(variant) is True

    def test_validate_variant_invalid_chromosome(self) -> None:
        """Test validation fails with invalid chromosome."""
        variant = GenomicVariant(
            chromosome="chr99",
            validate=False,
            position=12345,
            ref_allele="A",
            alt_allele="G",
            assembly="GRCh38",
        )
        with pytest.raises(ValidationError, match="Invalid chromosome"):
            validate_variant(variant, raise_on_error=True)

    def test_validate_variant_invalid_position(self) -> None:
        """Test validation fails with invalid position."""
        variant = GenomicVariant(
            chromosome="chr1",
            position=-100,
            validate=False,
            ref_allele="A",
            alt_allele="G",
            assembly="GRCh38",
        )
        assert validate_variant(variant, raise_on_error=False) is False

    def test_validate_variant_invalid_reference(self) -> None:
        """Test validation fails with invalid reference allele."""
        variant = GenomicVariant(
            chromosome="chr1",
            position=12345,
            ref_allele="X",
            validate=False,
            alt_allele="G",
            assembly="GRCh38",
        )
        assert validate_variant(variant, raise_on_error=False) is False

    def test_validate_variant_invalid_assembly(self) -> None:
        """Test validation fails with invalid assembly."""
        variant = GenomicVariant(
            chromosome="chr1",
            position=12345,
            ref_allele="A",
            alt_allele="G",
            assembly="GRCh36",
        )
        with pytest.raises(ValidationError, match="Invalid assembly"):
            validate_variant(variant, raise_on_error=True)

    def test_validate_variant_no_raise(self) -> None:
        """Test validation returns False without raising."""
        variant = GenomicVariant(
            chromosome="chr99",
            validate=False,
            position=12345,
            ref_allele="A",
            alt_allele="G",
            assembly="GRCh38",
        )
        result = validate_variant(variant, raise_on_error=False)
        assert result is False


class TestValidateVCFFile:
    """Test VCF file validation."""

    def test_validate_vcf_file_valid(self, tmp_path: Path) -> None:
        """Test validation of valid VCF file."""
        vcf_file = tmp_path / "test.vcf"
        vcf_content = """##fileformat=VCFv4.2
##ref_allele=GRCh38
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO
chr1\t12345\t.\tA\tG\t.\tPASS\t.
"""
        vcf_file.write_text(vcf_content)

        assert validate_vcf_file(vcf_file) is True

    def test_validate_vcf_file_gzipped(self, tmp_path: Path) -> None:
        """Test validation of gzipped VCF file."""
        import gzip

        vcf_file = tmp_path / "test.vcf.gz"
        vcf_content = b"""##fileformat=VCFv4.2
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO
chr1\t12345\t.\tA\tG\t.\tPASS\t.
"""
        with gzip.open(vcf_file, "wb") as f:
            f.write(vcf_content)

        assert validate_vcf_file(vcf_file) is True

    def test_validate_vcf_file_nonexistent(self) -> None:
        """Test validation of nonexistent file."""
        with pytest.raises(ValidationError, match="File does not exist"):
            validate_vcf_file(Path("/nonexistent/file.vcf"))

    def test_validate_vcf_file_missing_header(self, tmp_path: Path) -> None:
        """Test validation fails without proper header."""
        vcf_file = tmp_path / "no_header.vcf"
        vcf_file.write_text("chr1\t12345\t.\tA\tG\t.\tPASS\t.\n")

        with pytest.raises(ValidationError, match="Missing VCF header"):
            validate_vcf_file(vcf_file)

    def test_validate_vcf_file_empty(self, tmp_path: Path) -> None:
        """Test validation of empty file."""
        vcf_file = tmp_path / "empty.vcf"
        vcf_file.write_text("")

        with pytest.raises(ValidationError, match="Empty file"):
            validate_vcf_file(vcf_file)

    def test_validate_vcf_file_malformed_columns(self, tmp_path: Path) -> None:
        """Test validation with malformed column header."""
        vcf_file = tmp_path / "malformed.vcf"
        vcf_content = """##fileformat=VCFv4.2
#CHROM\tPOS\tREF\tALT
chr1\t12345\tA\tG
"""
        vcf_file.write_text(vcf_content)

        with pytest.raises(ValidationError, match="Invalid column header"):
            validate_vcf_file(vcf_file)


class TestValidationEdgeCases:
    """Test edge cases in validation."""

    def test_validate_coordinates_very_large_position(self) -> None:
        """Test validation with extremely large position."""
        assert validate_coordinates("chr1", 999999999999, 999999999999) is False

    def test_validate_reference_allele_very_long(self) -> None:
        """Test validation with very long reference allele."""
        long_allele = "A" * 10000
        assert validate_reference_allele(long_allele) is True

    def test_validate_variant_missing_fields(self) -> None:
        """Test validation with missing required fields."""
        variant = GenomicVariant(
            chromosome="chr1",
            position=12345,
            ref_allele="",
            validate=False,
            alt_allele="G",
            assembly="GRCh38",
        )
        assert validate_variant(variant, raise_on_error=False) is False

    def test_validate_chromosome_with_whitespace(self) -> None:
        """Test validation handles whitespace."""
        assert validate_chromosome(" chr1 ") is False
        assert validate_chromosome("chr1\n") is False

    def test_validate_reference_allele_with_whitespace(self) -> None:
        """Test validation rejects allele with whitespace."""
        assert validate_reference_allele("A C G T") is False
        assert validate_reference_allele("ACG\nT") is False


class TestValidationPerformance:
    """Test validation performance with bulk data."""

    def test_validate_many_variants(self) -> None:
        """Test validation of many variants."""
        variants = [
            GenomicVariant(
                chromosome=f"chr{i % 22 + 1}",
                position=1000 * (i + 1),
                ref_allele="A",
                alt_allele="G",
                assembly="GRCh38",
            )
            for i in range(1000)
        ]

        valid_count = sum(
            1 for v in variants if validate_variant(v, raise_on_error=False)
        )
        assert valid_count == 1000

    def test_validate_mixed_validity(self) -> None:
        """Test validation with mix of valid and invalid variants."""
        variants = [
            GenomicVariant(
                chromosome="chr1",
                position=100,
                ref_allele="A",
                alt_allele="G",
                assembly="GRCh38",
            ),
            GenomicVariant(
                validate=False,
                chromosome="chr99",
                position=100,
                ref_allele="A",
                alt_allele="G",
                assembly="GRCh38",
            ),
            GenomicVariant(
                validate=False,
                chromosome="chr2",
                position=-1,
                ref_allele="A",
                alt_allele="G",
                assembly="GRCh38",
            ),
            GenomicVariant(
                validate=False,
                chromosome="chrX",
                position=100,
                ref_allele="X",
                alt_allele="G",
                assembly="GRCh38",
            ),
        ]

        valid_count = sum(
            1 for v in variants if validate_variant(v, raise_on_error=False)
        )
        assert valid_count == 1
