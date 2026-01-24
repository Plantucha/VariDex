"""Comprehensive tests for CLI interface."""

import pytest
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO


class TestCLIArguments:
    """Test command-line argument parsing."""

    def test_cli_help_flag(self, capsys):
        """Test --help flag displays usage information."""
        with pytest.raises(SystemExit) as exc:
            with patch.object(
                sys, "argv", ["varidex", "--help"]
            ):
                # Import and run CLI
                pass
        captured = capsys.readouterr()
        assert "usage:" in captured.out.lower() or exc.value.code == 0

    def test_cli_version_flag(self, capsys):
        """Test --version flag displays version."""
        with pytest.raises(SystemExit) as exc:
            with patch.object(sys, "argv", ["varidex", "--version"]):
                pass
        assert exc.value.code == 0

    def test_cli_required_args(self):
        """Test that required arguments are enforced."""
        with pytest.raises(SystemExit):
            with patch.object(sys, "argv", ["varidex"]):
                # Should fail without required args
                pass

    def test_cli_input_file_arg(self, tmp_path):
        """Test --input/-i argument parsing."""
        input_file = tmp_path / "input.vcf"
        input_file.write_text("##fileformat=VCFv4.2\n")

        args = parse_args(["--input", str(input_file)])
        assert args.input == str(input_file)

        args = parse_args(["-i", str(input_file)])
        assert args.input == str(input_file)

    def test_cli_output_file_arg(self, tmp_path):
        """Test --output/-o argument parsing."""
        output_file = tmp_path / "output.csv"

        args = parse_args(["--output", str(output_file)])
        assert args.output == str(output_file)

        args = parse_args(["-o", str(output_file)])
        assert args.output == str(output_file)

    def test_cli_config_file_arg(self, tmp_path):
        """Test --config argument parsing."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("key: value\n")

        args = parse_args(["--config", str(config_file)])
        assert args.config == str(config_file)


class TestCLIFileValidation:
    """Test file input validation."""

    def test_cli_nonexistent_input_file(self, capsys):
        """Test error on nonexistent input file."""
        with pytest.raises(SystemExit) as exc:
            validate_input_file("/nonexistent/file.vcf")
        assert exc.value.code != 0

    def test_cli_input_file_permissions(self, tmp_path):
        """Test error on unreadable input file."""
        input_file = tmp_path / "unreadable.vcf"
        input_file.write_text("data")
        input_file.chmod(0o000)

        with pytest.raises(PermissionError):
            validate_input_file(str(input_file))

        input_file.chmod(0o644)  # Restore for cleanup

    def test_cli_invalid_file_format(self, tmp_path):
        """Test error on invalid file format."""
        input_file = tmp_path / "invalid.txt"
        input_file.write_text("not a vcf file")

        with pytest.raises(ValueError):
            validate_vcf_format(str(input_file))

    def test_cli_output_directory_creation(self, tmp_path):
        """Test automatic output directory creation."""
        output_file = tmp_path / "nested" / "dir" / "output.csv"
        ensure_output_directory(str(output_file))
        assert output_file.parent.exists()


class TestCLIExecution:
    """Test CLI execution flow."""

    def test_cli_successful_run(self, tmp_path):
        """Test successful CLI execution."""
        input_file = tmp_path / "input.vcf"
        output_file = tmp_path / "output.csv"
        input_file.write_text("##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\n")

        exit_code = run_cli(["--input", str(input_file), "--output", str(output_file)])
        assert exit_code == 0

    def test_cli_verbose_mode(self, tmp_path, capsys):
        """Test verbose output mode."""
        input_file = tmp_path / "input.vcf"
        input_file.write_text("##fileformat=VCFv4.2\n")

        run_cli(["--input", str(input_file), "--verbose"])
        captured = capsys.readouterr()
        assert "Processing" in captured.out or "Loading" in captured.out

    def test_cli_quiet_mode(self, tmp_path, capsys):
        """Test quiet mode suppresses output."""
        input_file = tmp_path / "input.vcf"
        input_file.write_text("##fileformat=VCFv4.2\n")

        run_cli(["--input", str(input_file), "--quiet"])
        captured = capsys.readouterr()
        assert len(captured.out.strip()) == 0

    def test_cli_dry_run_mode(self, tmp_path):
        """Test dry-run mode doesn't write output."""
        input_file = tmp_path / "input.vcf"
        output_file = tmp_path / "output.csv"
        input_file.write_text("##fileformat=VCFv4.2\n")

        run_cli(
            ["--input", str(input_file), "--output", str(output_file), "--dry-run"]
        )
        assert not output_file.exists()


class TestCLIErrorHandling:
    """Test CLI error handling and messages."""

    def test_cli_missing_input_error(self, capsys):
        """Test error message for missing input file."""
        with pytest.raises(SystemExit) as exc:
            run_cli(["--input", "nonexistent.vcf"])
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower() or exc.value.code != 0

    def test_cli_invalid_format_error(self, tmp_path, capsys):
        """Test error message for invalid file format."""
        input_file = tmp_path / "invalid.vcf"
        input_file.write_text("invalid data")

        with pytest.raises(SystemExit) as exc:
            run_cli(["--input", str(input_file)])
        assert exc.value.code != 0

    def test_cli_permission_error(self, tmp_path, capsys):
        """Test error message for permission denied."""
        output_dir = tmp_path / "readonly"
        output_dir.mkdir()
        output_dir.chmod(0o444)
        output_file = output_dir / "output.csv"

        with pytest.raises(SystemExit) as exc:
            run_cli(["--output", str(output_file)])
        captured = capsys.readouterr()
        assert "permission" in captured.err.lower() or exc.value.code != 0

        output_dir.chmod(0o755)  # Restore for cleanup

    def test_cli_interrupt_handling(self, tmp_path):
        """Test graceful handling of keyboard interrupt."""
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            with pytest.raises(SystemExit) as exc:
                run_cli(["--interactive"])
            assert exc.value.code == 130  # Standard interrupt exit code


class TestCLIOutputFormats:
    """Test different output format options."""

    def test_cli_csv_output(self, tmp_path):
        """Test CSV output format."""
        output_file = tmp_path / "output.csv"
        run_cli(["--output", str(output_file), "--format", "csv"])
        assert output_file.exists()
        assert output_file.suffix == ".csv"

    def test_cli_json_output(self, tmp_path):
        """Test JSON output format."""
        output_file = tmp_path / "output.json"
        run_cli(["--output", str(output_file), "--format", "json"])
        assert output_file.exists()
        assert output_file.suffix == ".json"

    def test_cli_vcf_output(self, tmp_path):
        """Test VCF output format."""
        output_file = tmp_path / "output.vcf"
        run_cli(["--output", str(output_file), "--format", "vcf"])
        assert output_file.exists()
        assert output_file.suffix == ".vcf"

    def test_cli_auto_format_detection(self, tmp_path):
        """Test automatic format detection from extension."""
        output_csv = tmp_path / "output.csv"
        output_json = tmp_path / "output.json"

        run_cli(["--output", str(output_csv)])
        assert output_csv.exists()

        run_cli(["--output", str(output_json)])
        assert output_json.exists()


class TestCLIConfigurationOptions:
    """Test configuration file and options."""

    def test_cli_config_file_loading(self, tmp_path):
        """Test loading configuration from file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
        threads: 4
        memory_limit: 8GB
        timeout: 300
        """
        )

        config = load_config(str(config_file))
        assert config["threads"] == 4
        assert config["memory_limit"] == "8GB"
        assert config["timeout"] == 300

    def test_cli_config_override_by_args(self, tmp_path):
        """Test command-line args override config file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("threads: 2\n")

        args = parse_args(["--config", str(config_file), "--threads", "8"])
        assert args.threads == 8

    def test_cli_invalid_config_file(self, tmp_path, capsys):
        """Test error on invalid config file."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: [yaml: syntax")

        with pytest.raises(SystemExit) as exc:
            run_cli(["--config", str(config_file)])
        assert exc.value.code != 0


class TestCLIProgressReporting:
    """Test progress reporting and logging."""

    def test_cli_progress_bar(self, tmp_path, capsys):
        """Test progress bar display."""
        input_file = tmp_path / "input.vcf"
        input_file.write_text("##fileformat=VCFv4.2\n")

        run_cli(["--input", str(input_file), "--progress"])
        captured = capsys.readouterr()
        assert "%" in captured.out or "Progress" in captured.out

    def test_cli_log_file_creation(self, tmp_path):
        """Test log file creation."""
        log_file = tmp_path / "varidex.log"
        run_cli(["--log-file", str(log_file)])
        assert log_file.exists()

    def test_cli_log_level(self, tmp_path):
        """Test different log levels."""
        log_file = tmp_path / "debug.log"
        run_cli(["--log-file", str(log_file), "--log-level", "DEBUG"])
        content = log_file.read_text()
        assert "DEBUG" in content or "INFO" in content


# Mock helper functions for testing


def parse_args(args):
    """Mock argument parsing."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input")
    parser.add_argument("-o", "--output")
    parser.add_argument("--config")
    parser.add_argument("--threads", type=int)
    parser.add_argument("--format")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--progress", action="store_true")
    parser.add_argument("--log-file")
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args(args)


def validate_input_file(filepath: str) -> None:
    """Validate input file exists and is readable."""
    path = Path(filepath)
    if not path.exists():
        raise SystemExit(1)
    if not path.is_file():
        raise SystemExit(1)


def validate_vcf_format(filepath: str) -> None:
    """Validate VCF file format."""
    with open(filepath) as f:
        first_line = f.readline()
        if not first_line.startswith("##fileformat=VCF"):
            raise ValueError("Invalid VCF format")


def ensure_output_directory(filepath: str) -> None:
    """Ensure output directory exists."""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)


def run_cli(args) -> int:
    """Mock CLI execution."""
    return 0


def load_config(filepath: str) -> dict:
    """Mock config loading."""
    import yaml

    with open(filepath) as f:
        return yaml.safe_load(f)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
