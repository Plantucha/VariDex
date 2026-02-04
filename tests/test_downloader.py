"""Tests for varidex.downloader module.

Black formatted with 88-char line limit.
"""

import hashlib
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

from varidex.downloader import (
    ResourceDownloader,
    calculate_checksum,
    download_file,
    verify_checksum,
)
from varidex.exceptions import DownloadError, ValidationError


class TestCalculateChecksum:
    """Test checksum calculation functions."""

    def test_calculate_checksum_md5(self, tmp_path: Path) -> None:
        """Test MD5 checksum calculation."""
        test_file = tmp_path / "test.txt"
        test_content = b"Hello, VariDex!"
        test_file.write_bytes(test_content)

        expected = hashlib.md5(test_content).hexdigest()
        result = calculate_checksum(test_file, algorithm="md5")

        assert result == expected

    def test_calculate_checksum_sha256(self, tmp_path: Path) -> None:
        """Test SHA256 checksum calculation."""
        test_file = tmp_path / "test.txt"
        test_content = b"Genomic data integrity"
        test_file.write_bytes(test_content)

        expected = hashlib.sha256(test_content).hexdigest()
        result = calculate_checksum(test_file, algorithm="sha256")

        assert result == expected

    def test_calculate_checksum_nonexistent_file(self) -> None:
        """Test checksum calculation with nonexistent file."""
        with pytest.raises(FileNotFoundError):
            calculate_checksum(Path("/nonexistent/file.txt"))

    def test_calculate_checksum_invalid_algorithm(self, tmp_path: Path) -> None:
        """Test checksum calculation with invalid algorithm."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        with pytest.raises(ValueError, match="Unsupported algorithm"):
            calculate_checksum(test_file, algorithm="invalid")


class TestVerifyChecksum:
    """Test checksum verification."""

    def test_verify_checksum_valid(self, tmp_path: Path) -> None:
        """Test verification with correct checksum."""
        test_file = tmp_path / "test.txt"
        test_content = b"Variant data"
        test_file.write_bytes(test_content)

        expected = hashlib.md5(test_content).hexdigest()
        assert verify_checksum(test_file, expected, algorithm="md5") is True

    def test_verify_checksum_invalid(self, tmp_path: Path) -> None:
        """Test verification with incorrect checksum."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        wrong_checksum = "0" * 32
        assert verify_checksum(test_file, wrong_checksum, algorithm="md5") is False

    def test_verify_checksum_case_insensitive(self, tmp_path: Path) -> None:
        """Test that checksum verification is case-insensitive."""
        test_file = tmp_path / "test.txt"
        test_content = b"ClinVar data"
        test_file.write_bytes(test_content)

        expected = hashlib.md5(test_content).hexdigest()
        assert verify_checksum(test_file, expected.upper(), algorithm="md5") is True


class TestDownloadFile:
    """Test file download function."""

    @patch("varidex.downloader.requests.get")
    def test_download_file_success(self, mock_get: Mock, tmp_path: Path) -> None:
        """Test successful file download."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-length": "13"}
        mock_response.iter_content = lambda chunk_size: [b"Hello, World!"]
        mock_get.return_value.__enter__ = lambda self: mock_response
        mock_get.return_value.__exit__ = lambda self, *args: None

        dest_file = tmp_path / "downloaded.txt"
        download_file("https://example.com/file.txt", dest_file)

        assert dest_file.exists()
        assert dest_file.read_bytes() == b"Hello, World!"

    @patch("varidex.downloader.requests.get")
    def test_download_file_http_error(self, mock_get: Mock, tmp_path: Path) -> None:
        """Test download with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError("Not Found")
        mock_get.return_value.__enter__ = lambda self: mock_response
        mock_get.return_value.__exit__ = lambda self, *args: None

        dest_file = tmp_path / "failed.txt"
        with pytest.raises(DownloadError, match="HTTP error"):
            download_file("https://example.com/missing.txt", dest_file)

    @patch("varidex.downloader.requests.get")
    def test_download_file_with_progress(self, mock_get: Mock, tmp_path: Path) -> None:
        """Test download with progress callback."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-length": "100"}
        mock_response.iter_content = lambda chunk_size: [b"x" * 50, b"y" * 50]
        mock_get.return_value.__enter__ = lambda self: mock_response
        mock_get.return_value.__exit__ = lambda self, *args: None

        progress_calls = []

        def progress_callback(current: int, total: int) -> None:
            progress_calls.append((current, total))

        dest_file = tmp_path / "progress.txt"
        download_file(
            "https://example.com/file.txt",
            dest_file,
            progress_callback=progress_callback,
        )

        assert len(progress_calls) > 0
        assert progress_calls[-1][0] == 100
        assert progress_calls[-1][1] == 100

    @patch("varidex.downloader.requests.get")
    def test_download_file_network_error(self, mock_get: Mock, tmp_path: Path) -> None:
        """Test download with network error."""
        mock_get.side_effect = requests.ConnectionError("Network unreachable")

        dest_file = tmp_path / "network_error.txt"
        with pytest.raises(DownloadError, match="Network error"):
            download_file("https://example.com/file.txt", dest_file)


class TestResourceDownloader:
    """Test ResourceDownloader class."""

    def test_init_default_cache_dir(self) -> None:
        """Test initialization with default cache directory."""
        downloader = ResourceDownloader()
        assert downloader.cache_dir is not None
        assert downloader.cache_dir.name == "varidex_cache"

    def test_init_custom_cache_dir(self, tmp_path: Path) -> None:
        """Test initialization with custom cache directory."""
        cache_dir = tmp_path / "custom_cache"
        downloader = ResourceDownloader(cache_dir=cache_dir)
        assert downloader.cache_dir == cache_dir
        assert cache_dir.exists()

    @patch("varidex.downloader.download_file")
    def test_download_resource_not_cached(
        self, mock_download: Mock, tmp_path: Path
    ) -> None:
        """Test downloading resource not in cache."""
        cache_dir = tmp_path / "cache"
        downloader = ResourceDownloader(cache_dir=cache_dir)

        url = "https://example.com/clinvar.vcf.gz"
        expected_path = cache_dir / "clinvar.vcf.gz"

        def download_side_effect(url: str, dest: Path, **kwargs) -> None:
            dest.write_text("mock data")

        mock_download.side_effect = download_side_effect

        result = downloader.download_resource(url, "clinvar.vcf.gz")

        assert result == expected_path
        assert expected_path.exists()
        mock_download.assert_called_once()

    def test_download_resource_already_cached(self, tmp_path: Path) -> None:
        """Test downloading resource already in cache."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        cached_file = cache_dir / "gnomad.vcf.gz"
        cached_file.write_text("cached data")

        downloader = ResourceDownloader(cache_dir=cache_dir)
        url = "https://example.com/gnomad.vcf.gz"

        with patch("varidex.downloader.download_file") as mock_download:
            result = downloader.download_resource(url, "gnomad.vcf.gz")

            assert result == cached_file
            mock_download.assert_not_called()

    @patch("varidex.downloader.download_file")
    @patch("varidex.downloader.verify_checksum")
    def test_download_resource_with_checksum(
        self, mock_verify: Mock, mock_download: Mock, tmp_path: Path
    ) -> None:
        """Test downloading resource with checksum verification."""
        cache_dir = tmp_path / "cache"
        downloader = ResourceDownloader(cache_dir=cache_dir)

        def download_side_effect(url: str, dest: Path, **kwargs) -> None:
            dest.write_text("verified data")

        mock_download.side_effect = download_side_effect
        mock_verify.return_value = True

        url = "https://example.com/data.vcf.gz"
        checksum = "abc123"

        result = downloader.download_resource(
            url, "data.vcf.gz", expected_checksum=checksum
        )

        assert result.exists()
        mock_verify.assert_called_once()

    @patch("varidex.downloader.download_file")
    @patch("varidex.downloader.verify_checksum")
    def test_download_resource_checksum_mismatch(
        self, mock_verify: Mock, mock_download: Mock, tmp_path: Path
    ) -> None:
        """Test download fails with checksum mismatch."""
        cache_dir = tmp_path / "cache"
        downloader = ResourceDownloader(cache_dir=cache_dir)

        def download_side_effect(url: str, dest: Path, **kwargs) -> None:
            dest.write_text("corrupted data")

        mock_download.side_effect = download_side_effect
        mock_verify.return_value = False

        url = "https://example.com/corrupted.vcf.gz"
        checksum = "wrong_checksum"

        with pytest.raises(ValidationError, match="Checksum mismatch"):
            downloader.download_resource(
                url, "corrupted.vcf.gz", expected_checksum=checksum
            )

    def test_download_resource_force_redownload(self, tmp_path: Path) -> None:
        """Test forcing re-download of cached resource."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        cached_file = cache_dir / "old_data.txt"
        cached_file.write_text("old content")

        downloader = ResourceDownloader(cache_dir=cache_dir)

        with patch("varidex.downloader.download_file") as mock_download:

            def download_side_effect(url: str, dest: Path, **kwargs) -> None:
                dest.write_text("new content")

            mock_download.side_effect = download_side_effect

            result = downloader.download_resource(
                "https://example.com/data.txt", "old_data.txt", force=True
            )

            assert result.read_text() == "new content"
            mock_download.assert_called_once()

    def test_clear_cache(self, tmp_path: Path) -> None:
        """Test cache clearing."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        (cache_dir / "file1.txt").write_text("data1")
        (cache_dir / "file2.txt").write_text("data2")

        downloader = ResourceDownloader(cache_dir=cache_dir)
        downloader.clear_cache()

        assert list(cache_dir.iterdir()) == []

    def test_get_cache_size(self, tmp_path: Path) -> None:
        """Test cache size calculation."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        (cache_dir / "file1.txt").write_bytes(b"x" * 100)
        (cache_dir / "file2.txt").write_bytes(b"y" * 200)

        downloader = ResourceDownloader(cache_dir=cache_dir)
        size = downloader.get_cache_size()

        assert size == 300

    def test_list_cached_files(self, tmp_path: Path) -> None:
        """Test listing cached files."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        file1 = cache_dir / "clinvar.vcf.gz"
        file2 = cache_dir / "gnomad.vcf.gz"
        file1.write_text("data1")
        file2.write_text("data2")

        downloader = ResourceDownloader(cache_dir=cache_dir)
        cached_files = downloader.list_cached_files()

        assert len(cached_files) == 2
        assert file1 in cached_files
        assert file2 in cached_files


class TestDownloadRetry:
    """Test download retry logic."""

    @patch("varidex.downloader.requests.get")
    def test_download_retry_success_on_second_attempt(
        self, mock_get: Mock, tmp_path: Path
    ) -> None:
        """Test successful download after retry."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-length": "4"}
        mock_response.iter_content = lambda chunk_size: [b"test"]

        mock_get.side_effect = [
            requests.Timeout("First attempt timeout"),
            Mock(
                __enter__=lambda self: mock_response,
                __exit__=lambda self, *args: None,
            ),
        ]

        dest_file = tmp_path / "retry.txt"
        download_file("https://example.com/file.txt", dest_file, max_retries=2)

        assert dest_file.exists()
        assert mock_get.call_count == 2

    @patch("varidex.downloader.requests.get")
    def test_download_retry_exhausted(self, mock_get: Mock, tmp_path: Path) -> None:
        """Test download fails after all retries exhausted."""
        mock_get.side_effect = requests.Timeout("Persistent timeout")

        dest_file = tmp_path / "failed_retry.txt"
        with pytest.raises(DownloadError, match="Max retries exceeded"):
            download_file("https://example.com/file.txt", dest_file, max_retries=3)

        assert mock_get.call_count == 3
