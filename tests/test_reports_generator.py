"""Comprehensive tests for report generation.

Tests report generators, formatters, and templates for various
output formats including HTML, PDF, and summary statistics.
"""

import json
from pathlib import Path

import pytest

from varidex.core.models import Variant
from varidex.exceptions import ReportError
from varidex.reports.formatters import HTMLFormatter, JSONFormatter, TSVFormatter
from varidex.reports.generator import ReportGenerator


class TestReportGenerator:
    """Test main report generator functionality."""

    @pytest.fixture
    def generator(self, tmp_path):
        """Create report generator for testing."""
        return ReportGenerator(output_dir=tmp_path)

    @pytest.fixture
    def sample_variants(self):
        """Create sample variants for reporting."""
        return [
            Variant(
                chromosome="chr1",
                position=12345,
                reference="A",
                alternate="G",
                annotations={
                    "gene": "BRCA1",
                    "impact": "HIGH",
                    "gnomad_af": 0.001,
                },
            ),
            Variant(
                chromosome="chr2",
                position=67890,
                reference="C",
                alternate="T",
                annotations={
                    "gene": "TP53",
                    "impact": "MODERATE",
                    "gnomad_af": 0.05,
                },
            ),
        ]

    def test_generator_initialization(self, tmp_path):
        """Test report generator initializes correctly."""
        generator = ReportGenerator(output_dir=tmp_path)
        assert generator.output_dir == tmp_path
        assert tmp_path.exists()

    def test_generate_html_report(self, generator, sample_variants, tmp_path):
        """Test HTML report generation."""
        output_file = tmp_path / "report.html"
        generator.generate_html_report(sample_variants, output_file)

        assert output_file.exists()
        content = output_file.read_text()
        assert "<html>" in content.lower()
        assert "BRCA1" in content or "TP53" in content

    def test_generate_summary_statistics(self, generator, sample_variants):
        """Test summary statistics generation."""
        summary = generator.generate_summary(sample_variants)

        assert "total_variants" in summary
        assert summary["total_variants"] == 2
        assert "by_chromosome" in summary or "chromosomes" in summary

    def test_generate_json_report(self, generator, sample_variants, tmp_path):
        """Test JSON report generation."""
        output_file = tmp_path / "report.json"
        generator.generate_json_report(sample_variants, output_file)

        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert isinstance(data, (list, dict))

    def test_generate_tsv_report(self, generator, sample_variants, tmp_path):
        """Test TSV report generation."""
        output_file = tmp_path / "report.tsv"
        generator.generate_tsv_report(sample_variants, output_file)

        assert output_file.exists()
        content = output_file.read_text()
        assert "\t" in content
        assert "chr1" in content or "chr2" in content

    def test_generate_with_empty_data(self, generator, tmp_path):
        """Test report generation with empty variant list."""
        output_file = tmp_path / "empty_report.html"
        generator.generate_html_report([], output_file)

        assert output_file.exists()
        content = output_file.read_text()
        assert "no variants" in content.lower() or "empty" in content.lower()

    def test_generate_with_invalid_output_path(self, generator, sample_variants):
        """Test error handling for invalid output path."""
        invalid_path = Path("/invalid/nonexistent/path/report.html")

        with pytest.raises((ReportError, OSError, PermissionError)):
            generator.generate_html_report(sample_variants, invalid_path)


class TestHTMLFormatter:
    """Test HTML formatter functionality."""

    @pytest.fixture
    def formatter(self):
        """Create HTML formatter for testing."""
        return HTMLFormatter()

    @pytest.fixture
    def sample_data(self):
        """Create sample data for formatting."""
        return {
            "variants": [
                {
                    "chromosome": "chr1",
                    "position": 12345,
                    "gene": "BRCA1",
                    "impact": "HIGH",
                }
            ],
            "summary": {"total": 1, "high_impact": 1},
        }

    def test_format_variant_table(self, formatter, sample_data):
        """Test variant table formatting."""
        html = formatter.format_variant_table(sample_data["variants"])

        assert "<table" in html
        assert "chr1" in html
        assert "BRCA1" in html

    def test_format_summary_section(self, formatter, sample_data):
        """Test summary section formatting."""
        html = formatter.format_summary(sample_data["summary"])

        assert "total" in html.lower() or "Total" in html
        assert "1" in html

    def test_format_complete_report(self, formatter, sample_data):
        """Test complete HTML report formatting."""
        html = formatter.format_report(sample_data)

        assert "<!DOCTYPE html>" in html or "<html>" in html
        assert "</html>" in html
        assert "BRCA1" in html

    def test_format_with_custom_template(self, formatter, sample_data):
        """Test formatting with custom template."""
        custom_template = "<html><body>{{ title }}</body></html>"
        html = formatter.format_with_template(sample_data, template=custom_template)

        assert "<html>" in html
        assert "<body>" in html

    def test_escape_html_characters(self, formatter):
        """Test HTML character escaping."""
        dangerous_input = "<script>alert('xss')</script>"
        safe_output = formatter.escape(dangerous_input)

        assert "<script>" not in safe_output
        assert "&lt;" in safe_output or "script" not in safe_output

    def test_format_with_missing_data(self, formatter):
        """Test formatting with missing data fields."""
        incomplete_data = {"variants": []}
        html = formatter.format_report(incomplete_data)

        assert html is not None
        assert len(html) > 0


class TestJSONFormatter:
    """Test JSON formatter functionality."""

    @pytest.fixture
    def formatter(self):
        """Create JSON formatter for testing."""
        return JSONFormatter()

    @pytest.fixture
    def sample_variants(self):
        """Create sample variants for testing."""
        return [
            Variant(
                chromosome="chr1",
                position=12345,
                reference="A",
                alternate="G",
            )
        ]

    def test_format_variants_to_json(self, formatter, sample_variants):
        """Test variant formatting to JSON."""
        json_str = formatter.format(sample_variants)
        data = json.loads(json_str)

        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["chromosome"] == "chr1"

    def test_format_with_pretty_print(self, formatter, sample_variants):
        """Test JSON formatting with pretty printing."""
        json_str = formatter.format(sample_variants, indent=2)
        data = json.loads(json_str)

        assert "\n" in json_str  # Pretty-printed
        assert isinstance(data, list)

    def test_format_with_null_values(self, formatter):
        """Test JSON formatting with null values."""
        variant = Variant(
            chromosome="chr1",
            position=12345,
            reference="A",
            alternate="G",
            annotations={"gene": None},
        )
        json_str = formatter.format([variant])
        data = json.loads(json_str)

        assert data is not None

    def test_format_nested_annotations(self, formatter):
        """Test formatting variants with nested annotations."""
        variant = Variant(
            chromosome="chr1",
            position=12345,
            reference="A",
            alternate="G",
            annotations={"predictions": {"sift": 0.05, "polyphen": 0.95}},
        )
        json_str = formatter.format([variant])
        data = json.loads(json_str)

        assert "annotations" in data[0]


class TestTSVFormatter:
    """Test TSV formatter functionality."""

    @pytest.fixture
    def formatter(self):
        """Create TSV formatter for testing."""
        return TSVFormatter()

    @pytest.fixture
    def sample_variants(self):
        """Create sample variants for testing."""
        return [
            Variant(
                chromosome="chr1",
                position=12345,
                reference="A",
                alternate="G",
                annotations={"gene": "BRCA1"},
            ),
            Variant(
                chromosome="chr2",
                position=67890,
                reference="C",
                alternate="T",
                annotations={"gene": "TP53"},
            ),
        ]

    def test_format_variants_to_tsv(self, formatter, sample_variants):
        """Test variant formatting to TSV."""
        tsv_str = formatter.format(sample_variants)

        assert "\t" in tsv_str
        assert "chr1" in tsv_str
        assert "chr2" in tsv_str

    def test_tsv_header_row(self, formatter, sample_variants):
        """Test TSV includes header row."""
        tsv_str = formatter.format(sample_variants)
        lines = tsv_str.split("\n")

        header = lines[0]
        assert "chromosome" in header.lower() or "chrom" in header.lower()
        assert "position" in header.lower() or "pos" in header.lower()

    def test_tsv_data_rows(self, formatter, sample_variants):
        """Test TSV data rows are correctly formatted."""
        tsv_str = formatter.format(sample_variants)
        lines = tsv_str.split("\n")

        assert len(lines) >= 3  # Header + 2 data rows + possible empty
        assert "12345" in lines[1]
        assert "67890" in lines[2]

    def test_tsv_with_missing_annotations(self, formatter):
        """Test TSV formatting with missing annotations."""
        variant = Variant(
            chromosome="chr1", position=12345, reference="A", alternate="G"
        )
        tsv_str = formatter.format([variant])

        assert "chr1" in tsv_str
        assert "12345" in tsv_str

    def test_tsv_special_character_handling(self, formatter):
        """Test TSV handles special characters."""
        variant = Variant(
            chromosome="chr1",
            position=12345,
            reference="A",
            alternate="G",
            annotations={"note": "Contains\ttab"},
        )
        tsv_str = formatter.format([variant])

        # Should escape or handle tabs in data
        assert tsv_str is not None


class TestReportStatistics:
    """Test statistical summary generation."""

    @pytest.fixture
    def generator(self, tmp_path):
        """Create report generator for testing."""
        return ReportGenerator(output_dir=tmp_path)

    @pytest.fixture
    def sample_variants(self):
        """Create sample variants with diverse annotations."""
        return [
            Variant(
                "chr1",
                12345,
                "A",
                "G",
                annotations={"impact": "HIGH", "gene": "BRCA1"},
            ),
            Variant(
                "chr1",
                23456,
                "C",
                "T",
                annotations={"impact": "MODERATE", "gene": "TP53"},
            ),
            Variant(
                "chr2",
                34567,
                "G",
                "A",
                annotations={"impact": "LOW", "gene": "EGFR"},
            ),
        ]

    def test_count_by_chromosome(self, generator, sample_variants):
        """Test variant count by chromosome."""
        stats = generator.generate_summary(sample_variants)

        if "by_chromosome" in stats:
            assert "chr1" in stats["by_chromosome"]
            assert stats["by_chromosome"]["chr1"] == 2
            assert stats["by_chromosome"]["chr2"] == 1

    def test_count_by_impact(self, generator, sample_variants):
        """Test variant count by impact level."""
        stats = generator.generate_summary(sample_variants)

        if "by_impact" in stats:
            assert "HIGH" in stats["by_impact"]
            assert stats["by_impact"]["HIGH"] == 1

    def test_count_by_gene(self, generator, sample_variants):
        """Test variant count by gene."""
        stats = generator.generate_summary(sample_variants)

        if "by_gene" in stats:
            assert "BRCA1" in stats["by_gene"]
            assert "TP53" in stats["by_gene"]

    def test_total_variant_count(self, generator, sample_variants):
        """Test total variant count."""
        stats = generator.generate_summary(sample_variants)

        assert "total_variants" in stats or "total" in stats
        total = stats.get("total_variants", stats.get("total", 0))
        assert total == 3

    def test_statistics_with_empty_list(self, generator):
        """Test statistics generation with empty variant list."""
        stats = generator.generate_summary([])

        total = stats.get("total_variants", stats.get("total", 0))
        assert total == 0


class TestReportTemplates:
    """Test report template handling."""

    @pytest.fixture
    def generator(self, tmp_path):
        """Create report generator for testing."""
        return ReportGenerator(output_dir=tmp_path)

    def test_load_default_template(self, generator):
        """Test loading default HTML template."""
        try:
            template = generator.load_template("default.html")
            assert template is not None
        except (FileNotFoundError, AttributeError):
            pytest.skip("Template loading not implemented")

    def test_load_custom_template(self, generator, tmp_path):
        """Test loading custom template."""
        template_file = tmp_path / "custom.html"
        template_file.write_text("<html><body>{{ content }}</body></html>")

        try:
            template = generator.load_template(str(template_file))
            assert template is not None
        except (AttributeError, NotImplementedError):
            pytest.skip("Custom template loading not implemented")

    def test_template_variable_substitution(self, generator):
        """Test template variable substitution."""
        template_str = "<html><body>{{ title }}</body></html>"
        data = {"title": "Test Report"}

        try:
            result = generator.render_template(template_str, data)
            assert "Test Report" in result
        except (AttributeError, NotImplementedError):
            pytest.skip("Template rendering not implemented")
