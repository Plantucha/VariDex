from unittest.mock import patch

import pytest

"""Comprehensive tests for pipeline stages.

Tests individual pipeline stages including validation, annotation,
filtering, and output generation.
"""

from unittest.mock import patch

import pytest

from varidex.core.config import PipelineConfig
from varidex.core.models import Variant
from varidex.exceptions import ValidationError
from varidex.pipeline.stages import (
    AnnotationStage,
    FilteringStage,
    OutputStage,
    ValidationStage,
)


class TestValidationStage:
    """Test validation stage functionality."""

    @pytest.fixture
    def validation_stage(self, tmp_path):
        """Create validation stage for testing."""
        config = PipelineConfig(
            input_vcf=tmp_path / "input.vcf",
            output_dir=tmp_path / "output",
            reference_genome="GRCh38",
        )
        return ValidationStage(config)

    @pytest.fixture
    def valid_vcf(self, tmp_path):
        """Create valid VCF file."""
        vcf_file = tmp_path / "valid.vcf"
        vcf_file.write_text(
            "##fileformat=VCFv4.2\n"
            "##reference=GRCh38\n"
            "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
            "chr1\t12345\t.\tA\tG\t30\tPASS\t.\n"
        )
        return vcf_file

    @pytest.fixture
    def invalid_vcf(self, tmp_path):
        """Create invalid VCF file."""
        vcf_file = tmp_path / "invalid.vcf"
        vcf_file.write_text("This is not a valid VCF file\n")
        return vcf_file

    def test_validate_vcf_format_valid(self, validation_stage, valid_vcf):
        """Test validation accepts valid VCF."""
        result = validation_stage.validate_vcf_format(valid_vcf)
        assert result is True

    def test_validate_vcf_format_invalid(self, validation_stage, invalid_vcf):
        """Test validation rejects invalid VCF."""
        with pytest.raises(ValidationError):
            validation_stage.validate_vcf_format(invalid_vcf)

    def test_validate_vcf_format_missing_file(self, validation_stage, tmp_path):
        """Test validation handles missing file."""
        missing_file = tmp_path / "nonexistent.vcf"
        with pytest.raises((ValidationError, FileNotFoundError)):
            validation_stage.validate_vcf_format(missing_file)

    def test_validate_reference_genome(self, validation_stage):
        """Test reference genome validation."""
        assert validation_stage.validate_reference_genome("GRCh38") is True
        assert validation_stage.validate_reference_genome("GRCh37") is True

        with pytest.raises(ValidationError):
            validation_stage.validate_reference_genome("InvalidRef")

    def test_validate_chromosome_names(self, validation_stage):
        """Test chromosome name validation."""
        valid_chroms = ["chr1", "chr2", "chrX", "chrY", "chrM"]
        for chrom in valid_chroms:
            assert validation_stage.validate_chromosome(chrom) is True

    def test_validate_positions(self, validation_stage):
        """Test position validation."""
        assert validation_stage.validate_position(12345) is True
        assert validation_stage.validate_position(1) is True

        with pytest.raises(ValidationError):
            validation_stage.validate_position(0)
        with pytest.raises(ValidationError):
            validation_stage.validate_position(-1)

    def test_validate_alleles(self, validation_stage):
        """Test allele validation."""
        assert validation_stage.validate_alleles("A", "G") is True
        assert validation_stage.validate_alleles("ATG", "A") is True

        with pytest.raises(ValidationError):
            validation_stage.validate_alleles("", "G")
        with pytest.raises(ValidationError):
            validation_stage.validate_alleles("A", "")

    def test_execute_validation_stage(self, validation_stage, valid_vcf):
        """Test complete validation stage execution."""
        validation_stage.config.input_vcf = valid_vcf
        result = validation_stage.execute()

        assert result is not None


class TestAnnotationStage:
    """Test annotation stage functionality."""

    @pytest.fixture
    def annotation_stage(self, tmp_path):
        """Create annotation stage for testing."""
        config = PipelineConfig(
            input_vcf=tmp_path / "input.vcf",
            output_dir=tmp_path / "output",
            reference_genome="GRCh38",
        )
        return AnnotationStage(config)

    @pytest.fixture
    def sample_variants(self):
        """Create sample variants for testing."""
        return [
            Variant(
                chromosome="chr1",
                position=12345,
                reference="A",
                alternate="G",
            ),
            Variant(
                chromosome="chr2",
                position=67890,
                reference="C",
                alternate="T",
            ),
        ]

    def test_annotate_with_gnomad(self, annotation_stage, sample_variants):
        """Test annotation with gnomAD data."""
        with patch.object(annotation_stage, "_fetch_gnomad_data") as mock_gnomad:
            mock_gnomad.return_value = {"af": 0.001, "ac": 10}

            result = annotation_stage.annotate_variant(
                sample_variants[0], sources=["gnomad"]
            )

            assert result is not None
            mock_gnomad.assert_called_once()

    def test_annotate_with_clinvar(self, annotation_stage, sample_variants):
        """Test annotation with ClinVar data."""
        with patch.object(annotation_stage, "_fetch_clinvar_data") as mock_clinvar:
            mock_clinvar.return_value = {"clinical_significance": "Pathogenic"}

            result = annotation_stage.annotate_variant(
                sample_variants[0], sources=["clinvar"]
            )

            assert result is not None
            mock_clinvar.assert_called_once()

    def test_annotate_with_dbnsfp(self, annotation_stage, sample_variants):
        """Test annotation with dbNSFP data."""
        with patch.object(annotation_stage, "_fetch_dbnsfp_data") as mock_dbnsfp:
            mock_dbnsfp.return_value = {"sift_score": 0.05}

            result = annotation_stage.annotate_variant(
                sample_variants[0], sources=["dbnsfp"]
            )

            assert result is not None
            mock_dbnsfp.assert_called_once()

    def test_annotate_multiple_sources(self, annotation_stage, sample_variants):
        """Test annotation with multiple sources."""
        with patch.object(annotation_stage, "_fetch_gnomad_data") as mock_gnomad:
            with patch.object(annotation_stage, "_fetch_clinvar_data") as mock_clinvar:
                mock_gnomad.return_value = {"af": 0.001}
                mock_clinvar.return_value = {"clinsig": "Benign"}

                result = annotation_stage.annotate_variant(
                    sample_variants[0], sources=["gnomad", "clinvar"]
                )

                assert result is not None
                mock_gnomad.assert_called_once()
                mock_clinvar.assert_called_once()

    def test_annotation_handles_missing_data(self, annotation_stage, sample_variants):
        """Test annotation handles missing annotation data."""
        with patch.object(annotation_stage, "_fetch_gnomad_data") as mock_gnomad:
            mock_gnomad.return_value = None

            result = annotation_stage.annotate_variant(
                sample_variants[0], sources=["gnomad"]
            )

            assert result is not None  # Should handle gracefully

    def test_batch_annotation(self, annotation_stage, sample_variants):
        """Test batch annotation of multiple variants."""
        with patch.object(annotation_stage, "annotate_variant") as mock_annotate:
            mock_annotate.return_value = sample_variants[0]

            results = annotation_stage.annotate_batch(sample_variants)

            assert len(results) == len(sample_variants)
            assert mock_annotate.call_count == len(sample_variants)

    def test_execute_annotation_stage(self, annotation_stage, sample_variants):
        """Test complete annotation stage execution."""
        with patch.object(annotation_stage, "_load_variants") as mock_load:
            mock_load.return_value = sample_variants

            result = annotation_stage.execute()

            assert result is not None


class TestFilteringStage:
    """Test filtering stage functionality."""

    @pytest.fixture
    def filtering_stage(self, tmp_path):
        """Create filtering stage for testing."""
        config = PipelineConfig(
            input_vcf=tmp_path / "input.vcf",
            output_dir=tmp_path / "output",
            reference_genome="GRCh38",
        )
        return FilteringStage(config)

    @pytest.fixture
    def annotated_variants(self):
        """Create annotated variants for testing."""
        return [
            Variant(
                chromosome="chr1",
                position=12345,
                reference="A",
                alternate="G",
                annotations={"gnomad_af": 0.001, "quality": 30},
            ),
            Variant(
                chromosome="chr2",
                position=67890,
                reference="C",
                alternate="T",
                annotations={"gnomad_af": 0.1, "quality": 10},
            ),
        ]

    def test_filter_by_quality(self, filtering_stage, annotated_variants):
        """Test filtering by quality score."""
        filtered = filtering_stage.filter_by_quality(annotated_variants, min_quality=20)

        assert len(filtered) == 1
        assert filtered[0].annotations["quality"] >= 20

    def test_filter_by_frequency(self, filtering_stage, annotated_variants):
        """Test filtering by allele frequency."""
        filtered = filtering_stage.filter_by_frequency(annotated_variants, max_af=0.05)

        assert len(filtered) == 1
        assert filtered[0].annotations["gnomad_af"] <= 0.05

    def test_filter_by_region(self, filtering_stage, annotated_variants):
        """Test filtering by genomic region."""
        filtered = filtering_stage.filter_by_region(
            annotated_variants, chromosome="chr1", start=10000, end=20000
        )

        assert len(filtered) == 1
        assert filtered[0].chromosome == "chr1"
        assert 10000 <= filtered[0].position <= 20000

    def test_filter_by_gene(self, filtering_stage, annotated_variants):
        """Test filtering by gene name."""
        # Add gene annotations
        annotated_variants[0].annotations["gene"] = "BRCA1"
        annotated_variants[1].annotations["gene"] = "TP53"

        filtered = filtering_stage.filter_by_gene(annotated_variants, genes=["BRCA1"])

        assert len(filtered) == 1
        assert filtered[0].annotations["gene"] == "BRCA1"

    def test_filter_by_impact(self, filtering_stage, annotated_variants):
        """Test filtering by variant impact."""
        annotated_variants[0].annotations["impact"] = "HIGH"
        annotated_variants[1].annotations["impact"] = "LOW"

        filtered = filtering_stage.filter_by_impact(
            annotated_variants, impacts=["HIGH"]
        )

        assert len(filtered) == 1
        assert filtered[0].annotations["impact"] == "HIGH"

    def test_compound_filtering(self, filtering_stage, annotated_variants):
        """Test multiple filters combined."""
        filtered = filtering_stage.apply_filters(
            annotated_variants,
            min_quality=20,
            max_af=0.05,
        )

        assert len(filtered) == 1

    def test_execute_filtering_stage(self, filtering_stage, annotated_variants):
        """Test complete filtering stage execution."""
        with patch.object(filtering_stage, "_load_variants") as mock_load:
            mock_load.return_value = annotated_variants

            result = filtering_stage.execute()

            assert result is not None


class TestOutputStage:
    """Test output stage functionality."""

    @pytest.fixture
    def output_stage(self, tmp_path):
        """Create output stage for testing."""
        config = PipelineConfig(
            input_vcf=tmp_path / "input.vcf",
            output_dir=tmp_path / "output",
            reference_genome="GRCh38",
        )
        return OutputStage(config)

    @pytest.fixture
    def processed_variants(self):
        """Create processed variants for testing."""
        return [
            Variant(
                chromosome="chr1",
                position=12345,
                reference="A",
                alternate="G",
                annotations={"gene": "BRCA1", "impact": "HIGH"},
            ),
        ]

    def test_write_vcf_output(self, output_stage, processed_variants, tmp_path):
        """Test writing VCF output."""
        output_file = tmp_path / "output" / "result.vcf"
        output_stage.write_vcf(processed_variants, output_file)

        assert output_file.exists()
        content = output_file.read_text()
        assert "##fileformat=VCF" in content

    def test_write_tsv_output(self, output_stage, processed_variants, tmp_path):
        """Test writing TSV output."""
        output_file = tmp_path / "output" / "result.tsv"
        output_stage.write_tsv(processed_variants, output_file)

        assert output_file.exists()
        content = output_file.read_text()
        assert "\t" in content  # Tab-separated

    def test_write_json_output(self, output_stage, processed_variants, tmp_path):
        """Test writing JSON output."""
        output_file = tmp_path / "output" / "result.json"
        output_stage.write_json(processed_variants, output_file)

        assert output_file.exists()
        import json

        data = json.loads(output_file.read_text())
        assert isinstance(data, (list, dict))

    def test_write_html_report(self, output_stage, processed_variants, tmp_path):
        """Test writing HTML report."""
        output_file = tmp_path / "output" / "report.html"
        output_stage.write_html_report(processed_variants, output_file)

        assert output_file.exists()
        content = output_file.read_text()
        assert "<html>" in content.lower()

    def test_write_summary_statistics(self, output_stage, processed_variants, tmp_path):
        """Test writing summary statistics."""
        output_file = tmp_path / "output" / "summary.txt"
        output_stage.write_summary(processed_variants, output_file)

        assert output_file.exists()
        content = output_file.read_text()
        assert "Total variants" in content or len(content) > 0

    def test_execute_output_stage(self, output_stage, processed_variants):
        """Test complete output stage execution."""
        with patch.object(output_stage, "_load_variants") as mock_load:
            mock_load.return_value = processed_variants

            result = output_stage.execute()

            assert result is not None


class TestStageDataFlow:
    """Test data flow between stages."""

    def test_validation_to_annotation_flow(self, tmp_path):
        """Test data flows from validation to annotation."""
        config = PipelineConfig(
            input_vcf=tmp_path / "input.vcf",
            output_dir=tmp_path / "output",
            reference_genome="GRCh38",
        )

        validation_stage = ValidationStage(config)
        annotation_stage = AnnotationStage(config)

        # Mock validation output
        with patch.object(validation_stage, "execute") as mock_validation:
            validated_data = [Variant("chr1", 12345, "A", "G")]
            mock_validation.return_value = validated_data

            # Should be able to use validated data in annotation
            with patch.object(annotation_stage, "_load_variants") as mock_load:
                mock_load.return_value = validated_data
                result = annotation_stage.execute()

                assert result is not None

    def test_annotation_to_filtering_flow(self, tmp_path):
        """Test data flows from annotation to filtering."""
        config = PipelineConfig(
            input_vcf=tmp_path / "input.vcf",
            output_dir=tmp_path / "output",
            reference_genome="GRCh38",
        )

        annotation_stage = AnnotationStage(config)
        filtering_stage = FilteringStage(config)

        annotated_data = [Variant("chr1", 12345, "A", "G", annotations={"af": 0.001})]

        with patch.object(filtering_stage, "_load_variants") as mock_load:
            mock_load.return_value = annotated_data
            result = filtering_stage.execute()

            assert result is not None


# @patch('src.pipeline.variant_processor.PipelineOrchestrator')
# @patch('src.pipeline.stages.ValidationStage')
# @patch('src.pipeline.stages.AnnotationStage')
