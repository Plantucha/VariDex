"""Tests for varidex.utils helper functions.

Black formatted with 88-char line limit.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from varidex.exceptions import ValidationError
from varidex.utils.helpers import (
    ensure_directory,
    format_file_size,
    is_gzipped,
    normalize_chromosome,
    parse_genomic_position,
    sanitize_filename,
)


class TestNormalizeChromosome:
    """Test chromosome normalization."""

    def test_normalize_chromosome_with_prefix(self) -> None:
        """Test normalization adds chr prefix."""
        assert normalize_chromosome("1") == "chr1"
        assert normalize_chromosome("22") == "chr22"
        assert normalize_chromosome("X") == "chrX"
        assert normalize_chromosome("Y") == "chrY"

    def test_normalize_chromosome_already_prefixed(self) -> None:
        """Test normalization preserves existing chr prefix."""
        assert normalize_chromosome("chr1") == "chr1"
        assert normalize_chromosome("chrX") == "chrX"

    def test_normalize_chromosome_remove_prefix(self) -> None:
        """Test normalization can remove chr prefix."""
        assert normalize_chromosome("chr1", add_prefix=False) == "1"
        assert normalize_chromosome("chrX", add_prefix=False) == "X"

    def test_normalize_chromosome_mitochondrial(self) -> None:
        """Test normalization of mitochondrial chromosome."""
        assert normalize_chromosome("M") == "chrM"
        assert normalize_chromosome("MT") == "chrM"
        assert normalize_chromosome("chrMT") == "chrM"

    def test_normalize_chromosome_case_insensitive(self) -> None:
        """Test normalization is case-insensitive."""
        assert normalize_chromosome("x") == "chrX"
        assert normalize_chromosome("CHRX") == "chrX"

    def test_normalize_chromosome_invalid(self) -> None:
        """Test normalization with invalid chromosome."""
        with pytest.raises(ValidationError, match="Invalid chromosome"):
            normalize_chromosome("invalid")

    def test_normalize_chromosome_empty(self) -> None:
        """Test normalization with empty string."""
        with pytest.raises(ValidationError, match="Invalid chromosome"):
            normalize_chromosome("")


class TestParseGenomicPosition:
    """Test genomic position parsing."""

    def test_parse_genomic_position_colon_format(self) -> None:
        """Test parsing position in chr:pos format."""
        chrom, pos = parse_genomic_position("chr1:12345")
        assert chrom == "chr1"
        assert pos == 12345

    def test_parse_genomic_position_dash_format(self) -> None:
        """Test parsing position in chr-pos format."""
        chrom, pos = parse_genomic_position("chr1-12345")
        assert chrom == "chr1"
        assert pos == 12345

    def test_parse_genomic_position_underscore_format(self) -> None:
        """Test parsing position in chr_pos format."""
        chrom, pos = parse_genomic_position("chr1_12345")
        assert chrom == "chr1"
        assert pos == 12345

    def test_parse_genomic_position_no_prefix(self) -> None:
        """Test parsing position without chr prefix."""
        chrom, pos = parse_genomic_position("1:12345")
        assert chrom in ["1", "chr1"]
        assert pos == 12345

    def test_parse_genomic_position_range(self) -> None:
        """Test parsing position range."""
        chrom, start, end = parse_genomic_position("chr1:12345-12350", allow_range=True)
        assert chrom == "chr1"
        assert start == 12345
        assert end == 12350

    def test_parse_genomic_position_invalid_format(self) -> None:
        """Test parsing with invalid format."""
        with pytest.raises(ValidationError, match="Invalid position format"):
            parse_genomic_position("invalid_format")

    def test_parse_genomic_position_negative(self) -> None:
        """Test parsing with negative position."""
        with pytest.raises(ValidationError, match="Position must be positive"):
            parse_genomic_position("chr1:-100")


class TestSanitizeFilename:
    """Test filename sanitization."""

    def test_sanitize_filename_basic(self) -> None:
        """Test basic filename sanitization."""
        assert sanitize_filename("test.txt") == "test.txt"
        assert sanitize_filename("my_file.vcf.gz") == "my_file.vcf.gz"

    def test_sanitize_filename_remove_spaces(self) -> None:
        """Test sanitization removes spaces."""
        assert sanitize_filename("my file.txt") == "my_file.txt"
        assert sanitize_filename("test  file.vcf") == "test_file.vcf"

    def test_sanitize_filename_remove_special_chars(self) -> None:
        """Test sanitization removes special characters."""
        assert sanitize_filename("file@#$.txt") == "file.txt"
        assert sanitize_filename("test*file?.vcf") == "testfile.vcf"

    def test_sanitize_filename_preserve_extensions(self) -> None:
        """Test sanitization preserves file extensions."""
        assert sanitize_filename("data.vcf.gz").endswith(".vcf.gz")
        assert sanitize_filename("test.tar.bz2").endswith(".tar.bz2")

    def test_sanitize_filename_max_length(self) -> None:
        """Test sanitization respects max length."""
        long_name = "a" * 300 + ".txt"
        result = sanitize_filename(long_name, max_length=100)
        assert len(result) <= 100
        assert result.endswith(".txt")

    def test_sanitize_filename_empty(self) -> None:
        """Test sanitization with empty string."""
        result = sanitize_filename("")
        assert len(result) > 0
        assert result != ""

    def test_sanitize_filename_path_separators(self) -> None:
        """Test sanitization removes path separators."""
        assert "/" not in sanitize_filename("path/to/file.txt")
        assert "\\" not in sanitize_filename("path\\to\\file.txt")


class TestFormatFileSize:
    """Test file size formatting."""

    def test_format_file_size_bytes(self) -> None:
        """Test formatting bytes."""
        assert format_file_size(0) == "0 B"
        assert format_file_size(100) == "100 B"
        assert format_file_size(1023) == "1023 B"

    def test_format_file_size_kilobytes(self) -> None:
        """Test formatting kilobytes."""
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(2048) == "2.0 KB"
        assert format_file_size(1536) == "1.5 KB"

    def test_format_file_size_megabytes(self) -> None:
        """Test formatting megabytes."""
        assert format_file_size(1024 * 1024) == "1.0 MB"
        assert format_file_size(5 * 1024 * 1024) == "5.0 MB"

    def test_format_file_size_gigabytes(self) -> None:
        """Test formatting gigabytes."""
        assert format_file_size(1024 * 1024 * 1024) == "1.0 GB"
        assert format_file_size(2.5 * 1024 * 1024 * 1024) == "2.5 GB"

    def test_format_file_size_terabytes(self) -> None:
        """Test formatting terabytes."""
        assert format_file_size(1024 * 1024 * 1024 * 1024) == "1.0 TB"

    def test_format_file_size_precision(self) -> None:
        """Test formatting with custom precision."""
        size = 1536
        assert format_file_size(size, precision=1) == "1.5 KB"
        assert format_file_size(size, precision=2) == "1.50 KB"

    def test_format_file_size_negative(self) -> None:
        """Test formatting with negative size."""
        with pytest.raises(ValidationError, match="Size cannot be negative"):
            format_file_size(-100)


class TestIsGzipped:
    """Test gzip file detection."""

    def test_is_gzipped_by_extension(self, tmp_path: Path) -> None:
        """Test gzip detection by file extension."""
        gz_file = tmp_path / "test.vcf.gz"
        gz_file.touch()
        assert is_gzipped(gz_file) is True

    def test_is_gzipped_not_gzipped(self, tmp_path: Path) -> None:
        """Test detection of non-gzipped file."""
        vcf_file = tmp_path / "test.vcf"
        vcf_file.touch()
        assert is_gzipped(vcf_file) is False

    def test_is_gzipped_by_magic_bytes(self, tmp_path: Path) -> None:
        """Test gzip detection by magic bytes."""
        import gzip

        gz_file = tmp_path / "test.gz"
        with gzip.open(gz_file, "wb") as f:
            f.write(b"test data")

        assert is_gzipped(gz_file, check_magic=True) is True

    def test_is_gzipped_false_extension(self, tmp_path: Path) -> None:
        """Test file with .gz extension but not gzipped."""
        fake_gz = tmp_path / "test.gz"
        fake_gz.write_text("not gzipped")

        assert is_gzipped(fake_gz, check_magic=True) is False

    def test_is_gzipped_nonexistent(self) -> None:
        """Test gzip detection with nonexistent file."""
        with pytest.raises(FileNotFoundError):
            is_gzipped(Path("/nonexistent/file.gz"), check_magic=True)


class TestEnsureDirectory:
    """Test directory creation utility."""

    def test_ensure_directory_creates_new(self, tmp_path: Path) -> None:
        """Test creating new directory."""
        new_dir = tmp_path / "new_directory"
        assert not new_dir.exists()

        ensure_directory(new_dir)

        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_ensure_directory_existing(self, tmp_path: Path) -> None:
        """Test with existing directory."""
        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()

        ensure_directory(existing_dir)

        assert existing_dir.exists()
        assert existing_dir.is_dir()

    def test_ensure_directory_nested(self, tmp_path: Path) -> None:
        """Test creating nested directories."""
        nested_dir = tmp_path / "level1" / "level2" / "level3"
        assert not nested_dir.exists()

        ensure_directory(nested_dir)

        assert nested_dir.exists()
        assert nested_dir.is_dir()

    def test_ensure_directory_file_exists(self, tmp_path: Path) -> None:
        """Test when path exists as a file."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")

        with pytest.raises(FileExistsError, match="exists as a file"):
            ensure_directory(file_path)

    def test_ensure_directory_permissions(self, tmp_path: Path) -> None:
        """Test directory created with correct permissions."""
        new_dir = tmp_path / "perm_test"
        ensure_directory(new_dir, mode=0o755)

        assert new_dir.exists()
        stat_info = os.stat(new_dir)
        # Check that directory is readable and executable
        assert stat_info.st_mode & 0o555 == 0o555


class TestEdgeCases:
    """Test edge cases in utility functions."""

    def test_normalize_chromosome_unicode(self) -> None:
        """Test normalization with unicode characters."""
        with pytest.raises(ValidationError):
            normalize_chromosome("αβγ")

    def test_parse_genomic_position_very_large(self) -> None:
        """Test parsing very large position."""
        chrom, pos = parse_genomic_position("chr1:999999999")
        assert pos == 999999999

    def test_sanitize_filename_unicode(self) -> None:
        """Test sanitization with unicode characters."""
        result = sanitize_filename("file_éàü.txt")
        assert ".txt" in result

    def test_format_file_size_zero(self) -> None:
        """Test formatting zero bytes."""
        assert format_file_size(0) == "0 B"

    def test_format_file_size_very_large(self) -> None:
        """Test formatting petabyte-scale files."""
        pb = 1024**5
        result = format_file_size(pb)
        assert "PB" in result or "TB" in result
