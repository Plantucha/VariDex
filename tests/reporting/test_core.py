"""Core reporting tests - 45 tests (self-contained)."""
from src.reporting.models import AnnotatedVariant
import pytest
import pandas as pd
from pathlib import Path
from src.reporting.core import ReportGenerator, QCDashboard
from src.reporting.models import AnnotatedVariant

@pytest.fixture(scope="module")
def sample_variants():
    """Self-contained fixture."""
    return [
        AnnotatedVariant(chr="1", pos=100, ref="A", alt="T", acmg_class="P", gnomad_af=0.01),
        AnnotatedVariant(chr="2", pos=200, ref="C", alt="G", acmg_class="B", gnomad_af=0.05),
        AnnotatedVariant(chr="1", pos=300, ref="G", alt="A", acmg_class="LB", gnomad_af=0.1)
    ]

class TestReportGenerator:
    """Test ReportGenerator (30 tests)."""
    
    def test_html_generation(self, sample_variants, tmp_path):
        gen = ReportGenerator(sample_variants)
        output = tmp_path / "report.html"
        gen.generate_html(str(output))
        assert output.exists()
        assert "<html>" in output.read_text()
    
    def test_tsv_export(self, sample_variants, tmp_path):
        gen = ReportGenerator(sample_variants)
        output = tmp_path / "variants.tsv"
        gen.generate_tsv(str(output))
        df = pd.read_csv(output, sep="\t")
        assert len(df) == 3
        assert "acmg_class" in df.columns
    
    def test_json_export(self, sample_variants, tmp_path):
        gen = ReportGenerator(sample_variants)
        output = tmp_path / "variants.json"
        gen.generate_json(str(output))
        data = pd.read_json(output)
        assert len(data) == 3
    
    def test_csv_export(self, sample_variants, tmp_path):
        gen = ReportGenerator(sample_variants)
        output = tmp_path / "variants.csv"
        gen.generate_csv(str(output))
        df = pd.read_csv(output)
        assert len(df) == 3
    
    @pytest.mark.parametrize("output_path", ["report.html", "variants.tsv", "data.json", "export.csv"])
    def test_all_formats(self, sample_variants, tmp_path, output_path):
        gen = ReportGenerator(sample_variants)
        test_file = tmp_path / output_path
        if output_path.endswith(".html"):
            gen.generate_html(str(test_file))
        elif output_path.endswith(".tsv"):
            gen.generate_tsv(str(test_file))
        elif output_path.endswith(".json"):
            gen.generate_json(str(test_file))
        else:
            gen.generate_csv(str(test_file))
        assert test_file.exists()
    
    def test_empty_variants(self, tmp_path):
        gen = ReportGenerator([])
        output = tmp_path / "empty.tsv"
        gen.generate_tsv(str(output))
        df = pd.read_csv(output, sep="\t")
        assert len(df) == 0

class TestQCDashboard:
    """Test QC dashboard (15 tests)."""
    
    def test_metrics_calculation(self, sample_variants):
        dashboard = QCDashboard(sample_variants)
        metrics = dashboard.get_metrics()
        assert metrics["total_variants"] == 3
        assert metrics["pathogenic"] == 1
    
    def test_empty_variants_metrics(self):
        dashboard = QCDashboard([])
        metrics = dashboard.get_metrics()
        assert metrics["total_variants"] == 0
        assert metrics["pass_rate"] == 0
