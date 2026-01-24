"""End-to-end integration tests for VariDex.

Black formatted with 88-char line limit.
"""

import gzip
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from varidex.core.config import Config
from varidex.core.models import GenomicVariant, VariantAnnotation
from varidex.exceptions import PipelineError, ValidationError


@pytest.mark.integration
class TestEndToEndPipeline:
    """End-to-end pipeline integration tests."""

    def test_e2e_single_variant_annotation(self, tmp_path: Path) -> None:
        """Test complete pipeline with single variant."""
        # Create test VCF file
        vcf_file = tmp_path / "test.vcf"
        vcf_content = """##fileformat=VCFv4.2
##reference=GRCh38
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO
chr1\t100000\trs123\tA\tG\t100\tPASS\t.
"""
        vcf_file.write_text(vcf_content)

        # Read and validate
        from varidex.io.loaders.vcf_loader import load_vcf
        from varidex.pipeline.validators import validate_vcf_file

        assert validate_vcf_file(vcf_file)
        variants_df = load_vcf(vcf_file)

        assert len(variants_df) == 1
        assert variants_df.iloc[0]["chromosome"] == "chr1"
        assert variants_df.iloc[0]["position"] == 100000

    def test_e2e_variant_matching_workflow(self, tmp_path: Path) -> None:
        """Test variant matching against reference database."""
        # Create query variants
        query_df = pd.DataFrame(
            {
                "chromosome": ["chr1", "chr2"],
                "position": [100000, 200000],
                "reference": ["A", "C"],
                "alternate": ["G", "T"],
            }
        )

        # Create reference database
        reference_df = pd.DataFrame(
            {
                "chromosome": ["chr1", "chr3"],
                "position": [100000, 300000],
                "reference": ["A", "G"],
                "alternate": ["G", "A"],
                "clinical_significance": ["Pathogenic", "Benign"],
            }
        )

        # Match variants
        from varidex.io.matching import match_by_coordinates

        matches = match_by_coordinates(query_df, reference_df)

        assert len(matches) == 1
        assert matches.iloc[0]["clinical_significance"] == "Pathogenic"

    def test_e2e_multi_source_integration(self, tmp_path: Path) -> None:
        """Test integration of multiple data sources."""
        # Create test data from multiple sources
        vcf_file = tmp_path / "variants.vcf"
        vcf_content = """##fileformat=VCFv4.2
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO
chr7\t140753336\trs113488022\tA\tT\t100\tPASS\tGENE=BRAF
"""
        vcf_file.write_text(vcf_content)

        # Load variants
        from varidex.io.loaders.vcf_loader import load_vcf

        variants_df = load_vcf(vcf_file)

        # Simulate annotation from ClinVar
        clinvar_df = pd.DataFrame(
            {
                "chromosome": ["chr7"],
                "position": [140753336],
                "reference": ["A"],
                "alternate": ["T"],
                "clinical_significance": ["Pathogenic"],
                "review_status": ["criteria provided, multiple submitters"],
            }
        )

        # Simulate annotation from gnomAD
        gnomad_df = pd.DataFrame(
            {
                "chromosome": ["chr7"],
                "position": [140753336],
                "reference": ["A"],
                "alternate": ["T"],
                "allele_frequency": [0.00001],
                "allele_count": [2],
            }
        )

        # Merge annotations
        from varidex.io.matching import match_by_coordinates

        annotated = match_by_coordinates(variants_df, clinvar_df)
        annotated = match_by_coordinates(annotated, gnomad_df)

        assert len(annotated) == 1
        assert "clinical_significance" in annotated.columns
        assert "allele_frequency" in annotated.columns

    def test_e2e_pipeline_with_filtering(self, tmp_path: Path) -> None:
        """Test pipeline with variant filtering."""
        # Create variants with different properties
        variants_df = pd.DataFrame(
            {
                "chromosome": ["chr1", "chr1", "chr2"],
                "position": [100, 200, 300],
                "reference": ["A", "C", "G"],
                "alternate": ["G", "T", "A"],
                "quality": [100, 50, 30],
                "depth": [100, 80, 20],
            }
        )

        # Filter by quality
        filtered = variants_df[variants_df["quality"] >= 50]
        assert len(filtered) == 2

        # Filter by depth
        filtered = filtered[filtered["depth"] >= 50]
        assert len(filtered) == 2

    def test_e2e_report_generation(self, tmp_path: Path) -> None:
        """Test complete workflow with report generation."""
        # Create annotated variants
        annotated_df = pd.DataFrame(
            {
                "chromosome": ["chr1", "chr2"],
                "position": [100000, 200000],
                "reference": ["A", "C"],
                "alternate": ["G", "T"],
                "gene": ["BRCA1", "TP53"],
                "clinical_significance": ["Pathogenic", "Likely pathogenic"],
                "allele_frequency": [0.00001, 0.00005],
            }
        )

        # Generate report
        report_file = tmp_path / "report.tsv"
        annotated_df.to_csv(report_file, sep="\t", index=False)

        assert report_file.exists()
        assert report_file.stat().st_size > 0

        # Verify report contents
        report_df = pd.read_csv(report_file, sep="\t")
        assert len(report_df) == 2
        assert "clinical_significance" in report_df.columns


@pytest.mark.integration
@pytest.mark.slow
class TestPerformanceIntegration:
    """Performance integration tests."""

    def test_large_vcf_processing(self, tmp_path: Path) -> None:
        """Test processing large VCF file."""
        # Create large VCF file
        vcf_file = tmp_path / "large.vcf"
        n_variants = 10000

        with vcf_file.open("w") as f:
            f.write("##fileformat=VCFv4.2\n")
            f.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")
            for i in range(n_variants):
                chrom = f"chr{(i % 22) + 1}"
                pos = 100000 + i * 1000
                f.write(f"{chrom}\t{pos}\t.\tA\tG\t100\tPASS\t.\n")

        # Load and process
        from varidex.io.loaders.vcf_loader import load_vcf

        variants_df = load_vcf(vcf_file)
        assert len(variants_df) == n_variants

    def test_concurrent_matching_performance(self) -> None:
        """Test performance of matching large datasets."""
        n_variants = 50000

        # Create large query dataset
        query_df = pd.DataFrame(
            {
                "chromosome": [f"chr{i % 22 + 1}" for i in range(n_variants)],
                "position": [100000 + i * 100 for i in range(n_variants)],
                "reference": ["A"] * n_variants,
                "alternate": ["G"] * n_variants,
            }
        )

        # Create reference dataset
        ref_df = pd.DataFrame(
            {
                "chromosome": [f"chr{i % 22 + 1}" for i in range(n_variants // 2)],
                "position": [100000 + i * 100 for i in range(n_variants // 2)],
                "reference": ["A"] * (n_variants // 2),
                "alternate": ["G"] * (n_variants // 2),
            }
        )

        # Match
        from varidex.io.matching import match_by_coordinates

        matches = match_by_coordinates(query_df, ref_df)
        assert len(matches) == n_variants // 2

    def test_memory_efficient_processing(self, tmp_path: Path) -> None:
        """Test memory-efficient processing of large files."""
        # Create gzipped VCF
        vcf_gz = tmp_path / "test.vcf.gz"
        n_variants = 100000

        with gzip.open(vcf_gz, "wt") as f:
            f.write("##fileformat=VCFv4.2\n")
            f.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")
            for i in range(n_variants):
                chrom = f"chr{(i % 22) + 1}"
                pos = 100000 + i * 100
                f.write(f"{chrom}\t{pos}\t.\tA\tG\t100\tPASS\t.\n")

        # Process in chunks (memory-efficient)
        from varidex.io.loaders.vcf_loader import load_vcf_chunked

        total_variants = 0
        for chunk in load_vcf_chunked(vcf_gz, chunk_size=10000):
            total_variants += len(chunk)
            assert len(chunk) <= 10000

        assert total_variants == n_variants


@pytest.mark.integration
class TestDataIntegrity:
    """Data integrity integration tests."""

    def test_roundtrip_vcf_to_dataframe(self, tmp_path: Path) -> None:
        """Test VCF to DataFrame and back conversion."""
        original_vcf = tmp_path / "original.vcf"
        vcf_content = """##fileformat=VCFv4.2
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO
chr1\t100000\trs123\tA\tG\t100\tPASS\tGENE=BRCA1
chr2\t200000\trs456\tC\tT\t200\tPASS\tGENE=TP53
"""
        original_vcf.write_text(vcf_content)

        # Load
        from varidex.io.loaders.vcf_loader import load_vcf
        from varidex.io.writers.vcf_writer import write_vcf

        variants_df = load_vcf(original_vcf)

        # Write back
        output_vcf = tmp_path / "output.vcf"
        write_vcf(variants_df, output_vcf)

        # Load again and compare
        reloaded_df = load_vcf(output_vcf)
        assert len(reloaded_df) == len(variants_df)
        assert list(reloaded_df["chromosome"]) == list(variants_df["chromosome"])
        assert list(reloaded_df["position"]) == list(variants_df["position"])

    def test_coordinate_system_consistency(self) -> None:
        """Test coordinate system consistency across operations."""
        # Create variants in 0-based coordinates
        variants_0based = pd.DataFrame(
            {
                "chromosome": ["chr1"],
                "position": [99999],
                "reference": ["A"],
                "alternate": ["G"],
            }
        )

        # Convert to 1-based
        from varidex.utils.coordinates import convert_to_1based

        variants_1based = convert_to_1based(variants_0based)
        assert variants_1based.iloc[0]["position"] == 100000

        # Convert back to 0-based
        from varidex.utils.coordinates import convert_to_0based

        variants_back = convert_to_0based(variants_1based)
        assert variants_back.iloc[0]["position"] == 99999

    def test_allele_normalization_integrity(self) -> None:
        """Test allele normalization maintains integrity."""
        # Create variants with different representations
        variants = pd.DataFrame(
            {
                "chromosome": ["chr1", "chr1", "chr1"],
                "position": [100000, 100000, 100001],
                "reference": ["A", "AT", "T"],
                "alternate": ["AT", "A", "-"],
            }
        )

        # Normalize
        from varidex.io.normalization import normalize_alleles

        normalized = normalize_alleles(variants)

        # First two should normalize to same representation
        assert (
            normalized.iloc[0]["reference"] == normalized.iloc[1]["reference"]
            or normalized.iloc[0]["alternate"] == normalized.iloc[1]["alternate"]
        )


@pytest.mark.integration
class TestErrorRecovery:
    """Error recovery integration tests."""

    def test_pipeline_handles_malformed_input(self, tmp_path: Path) -> None:
        """Test pipeline error handling with malformed input."""
        malformed_vcf = tmp_path / "malformed.vcf"
        malformed_vcf.write_text("This is not a valid VCF file")

        from varidex.io.loaders.vcf_loader import load_vcf

        with pytest.raises((ValidationError, ValueError)):
            load_vcf(malformed_vcf)

    def test_pipeline_handles_missing_files(self) -> None:
        """Test pipeline error handling with missing files."""
        from varidex.io.loaders.vcf_loader import load_vcf

        with pytest.raises(FileNotFoundError):
            load_vcf(Path("/nonexistent/file.vcf"))

    def test_pipeline_partial_failure_recovery(self) -> None:
        """Test pipeline continues after partial failures."""
        # Create mix of valid and invalid variants
        variants_df = pd.DataFrame(
            {
                "chromosome": ["chr1", "invalid", "chr2"],
                "position": [100000, 200000, 300000],
                "reference": ["A", "C", "G"],
                "alternate": ["G", "T", "A"],
            }
        )

        # Filter valid variants
        from varidex.pipeline.validators import validate_chromosome

        valid_variants = variants_df[
            variants_df["chromosome"].apply(lambda x: validate_chromosome(x))
        ]

        assert len(valid_variants) == 2
        assert "invalid" not in list(valid_variants["chromosome"])


@pytest.mark.integration
class TestConfigurationIntegration:
    """Configuration integration tests."""

    def test_config_affects_pipeline_behavior(self, tmp_path: Path) -> None:
        """Test configuration affects pipeline execution."""
        config = Config()
        config.output_dir = tmp_path
        config.validate_inputs = True
        config.allow_missing_data = False

        assert config.output_dir == tmp_path
        assert config.validate_inputs is True
        assert config.allow_missing_data is False

    def test_config_persistence(self, tmp_path: Path) -> None:
        """Test configuration save and load."""
        config_file = tmp_path / "config.yaml"

        # Create config
        config = Config()
        config.output_dir = tmp_path
        config.validate_inputs = True

        # Save
        config.save(config_file)

        # Load
        loaded_config = Config.load(config_file)
        assert loaded_config.output_dir == tmp_path
        assert loaded_config.validate_inputs is True
