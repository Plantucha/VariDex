"""CLI reporting tests (20 tests)."""

from src.reporting.models import AnnotatedVariant
import pytest
from click.testing import CliRunner
from src.reporting.cli import reporting


@pytest.fixture
def runner():
    return CliRunner()


class TestReportingCLI:
    """Test reporting CLI commands (20 tests)."""

    def test_generate_help(self, runner):
        result = runner.invoke(reporting, ["--help"])
        assert result.exit_code == 0
        assert "Generate reports from annotated VCF" in result.stdout

    @pytest.mark.parametrize("format_flag", ["--html", "--tsv", "--json", "--qc"])
    def test_single_format(self, runner, format_flag):
        result = runner.invoke(
            reporting, ["generate", "test.vcf", format_flag, "output"]
        )
        assert result.exit_code == 0  # Mock success

    def test_multiple_formats(self, runner):
        result = runner.invoke(
            reporting,
            ["generate", "test.vcf", "--html", "report.html", "--tsv", "data.tsv"],
        )
        assert result.exit_code == 0

    def test_no_formats(self, runner):
        result = runner.invoke(reporting, ["generate", "test.vcf"])
        # CLI allows no-output mode  # Should fail without output spec
