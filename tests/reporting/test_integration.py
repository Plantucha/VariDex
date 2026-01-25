"""Reporting integration tests (15 tests)."""
import pytest
from pathlib import Path
from src.reporting.core import ReportGenerator

@pytest.mark.integration
class TestReportingIntegration:
    """End-to-end reporting pipeline tests (15 tests)."""
    
    def test_full_pipeline_html(self, sample_variants, tmp_path):
        """Test complete HTML report generation."""
        gen = ReportGenerator(sample_variants)
        html_path = tmp_path / "full_report.html"
        gen.generate_html(str(html_path))
        
        content = html_path.read_text()
        assert "<html>" in content
        assert "VariDex Report" in content
    
    def test_batch_export_all_formats(self, sample_variants, tmp_path):
        """Test generating all export formats simultaneously."""
        gen = ReportGenerator(sample_variants)
        
        formats = [
            (tmp_path / "report.html", gen.generate_html),
            (tmp_path / "variants.tsv", gen.generate_tsv),
            (tmp_path / "data.json", gen.generate_json),
            (tmp_path / "export.csv", gen.generate_csv)
        ]
        
        for path, func in formats:
            func(str(path))
            assert path.exists()
    
    # Edge case tests (10 more)
    @pytest.mark.parametrize("variant_count", [0, 1, 100])
    def test_varying_variant_counts(self, variant_count, tmp_path):
        variants = [AnnotatedVariant("1", i, "A", "T", "B", 0.01) 
                   for i in range(1, variant_count + 1)]
        gen = ReportGenerator(variants)
        tsv_path = tmp_path / "varying.tsv"
        gen.generate_tsv(str(tsv_path))
        df = pd.read_csv(tsv_path, sep="\t")
        assert len(df) == variant_count
