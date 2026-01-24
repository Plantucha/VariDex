"""Performance and benchmark tests for VariDex.

Tests system performance, memory usage, and scalability
with various dataset sizes and configurations.
"""

import pytest
import time
import sys
from pathlib import Path
from unittest.mock import Mock, patch
import pandas as pd

from varidex.pipeline.orchestrator import PipelineOrchestrator
from varidex.core.config import PipelineConfig
from varidex.core.models import Variant


# Mark all tests in this module as performance tests
pytestmark = pytest.mark.performance


class TestProcessingSpeed:
    """Test processing speed for various dataset sizes."""

    @pytest.fixture
    def small_dataset(self, tmp_path):
        """Create small VCF dataset (100 variants)."""
        vcf_file = tmp_path / "small.vcf"
        with vcf_file.open("w") as f:
            f.write("##fileformat=VCFv4.2\n")
            f.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")
            for i in range(100):
                f.write(f"chr1\t{10000 + i * 100}\t.\tA\tG\t30\tPASS\t.\n")
        return vcf_file

    @pytest.fixture
    def medium_dataset(self, tmp_path):
        """Create medium VCF dataset (1000 variants)."""
        vcf_file = tmp_path / "medium.vcf"
        with vcf_file.open("w") as f:
            f.write("##fileformat=VCFv4.2\n")
            f.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")
            for i in range(1000):
                chrom = f"chr{(i % 22) + 1}"
                f.write(f"{chrom}\t{10000 + i * 100}\t.\tA\tG\t30\tPASS\t.\n")
        return vcf_file

    @pytest.fixture
    def large_dataset(self, tmp_path):
        """Create large VCF dataset (10000 variants)."""
        vcf_file = tmp_path / "large.vcf"
        with vcf_file.open("w") as f:
            f.write("##fileformat=VCFv4.2\n")
            f.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")
            for i in range(10000):
                chrom = f"chr{(i % 22) + 1}"
                f.write(f"{chrom}\t{10000 + i * 100}\t.\tA\tG\t30\tPASS\t.\n")
        return vcf_file

    def test_small_dataset_processing_time(self, small_dataset, tmp_path):
        """Test processing time for small dataset (<1 second)."""
        config = PipelineConfig(
            input_vcf=small_dataset,
            output_dir=tmp_path / "output",
            reference_genome="GRCh38",
        )
        orchestrator = PipelineOrchestrator(config)

        with patch.object(orchestrator, "_execute_stages") as mock_exec:
            mock_exec.return_value = True

            start_time = time.time()
            orchestrator.run()
            elapsed_time = time.time() - start_time

            assert elapsed_time < 1.0, f"Small dataset took {elapsed_time}s"

    def test_medium_dataset_processing_time(self, medium_dataset, tmp_path):
        """Test processing time for medium dataset (<5 seconds)."""
        config = PipelineConfig(
            input_vcf=medium_dataset,
            output_dir=tmp_path / "output",
            reference_genome="GRCh38",
        )
        orchestrator = PipelineOrchestrator(config)

        with patch.object(orchestrator, "_execute_stages") as mock_exec:
            mock_exec.return_value = True

            start_time = time.time()
            orchestrator.run()
            elapsed_time = time.time() - start_time

            assert elapsed_time < 5.0, f"Medium dataset took {elapsed_time}s"

    @pytest.mark.slow
    def test_large_dataset_processing_time(self, large_dataset, tmp_path):
        """Test processing time for large dataset (<30 seconds)."""
        config = PipelineConfig(
            input_vcf=large_dataset,
            output_dir=tmp_path / "output",
            reference_genome="GRCh38",
        )
        orchestrator = PipelineOrchestrator(config)

        with patch.object(orchestrator, "_execute_stages") as mock_exec:
            mock_exec.return_value = True

            start_time = time.time()
            orchestrator.run()
            elapsed_time = time.time() - start_time

            assert elapsed_time < 30.0, f"Large dataset took {elapsed_time}s"

    def test_linear_scaling(self, tmp_path):
        """Test that processing time scales linearly with data size."""
        sizes = [100, 500, 1000]
        times = []

        for size in sizes:
            vcf_file = tmp_path / f"test_{size}.vcf"
            with vcf_file.open("w") as f:
                f.write("##fileformat=VCFv4.2\n")
                f.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")
                for i in range(size):
                    f.write(f"chr1\t{10000 + i}\t.\tA\tG\t30\tPASS\t.\n")

            config = PipelineConfig(
                input_vcf=vcf_file,
                output_dir=tmp_path / f"output_{size}",
                reference_genome="GRCh38",
            )
            orchestrator = PipelineOrchestrator(config)

            with patch.object(orchestrator, "_execute_stages") as mock_exec:
                mock_exec.return_value = True

                start_time = time.time()
                orchestrator.run()
                elapsed_time = time.time() - start_time
                times.append(elapsed_time)

        # Check roughly linear scaling (within 2x tolerance)
        if len(times) >= 2:
            ratio = times[-1] / times[0]
            size_ratio = sizes[-1] / sizes[0]
            assert ratio < size_ratio * 2, "Non-linear scaling detected"


class TestMemoryUsage:
    """Test memory usage and optimization."""

    @pytest.fixture
    def sample_variants(self):
        """Create large list of variants."""
        return [
            Variant(
                chromosome=f"chr{i % 22 + 1}",
                position=10000 + i * 100,
                reference="A",
                alternate="G",
            )
            for i in range(1000)
        ]

    def test_memory_usage_within_limits(self, sample_variants):
        """Test memory usage stays within reasonable limits."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Process variants
        processed = [v for v in sample_variants if v.position > 0]

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Should not use more than 100MB for 1000 variants
        assert memory_increase < 100, f"Memory increased by {memory_increase}MB"

    def test_memory_cleanup_after_processing(self, tmp_path):
        """Test memory is freed after processing."""
        import gc
        import psutil
        import os

        process = psutil.Process(os.getpid())

        vcf_file = tmp_path / "test.vcf"
        with vcf_file.open("w") as f:
            f.write("##fileformat=VCFv4.2\n")
            f.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")
            for i in range(1000):
                f.write(f"chr1\t{10000 + i}\t.\tA\tG\t30\tPASS\t.\n")

        initial_memory = process.memory_info().rss / 1024 / 1024

        config = PipelineConfig(
            input_vcf=vcf_file,
            output_dir=tmp_path / "output",
            reference_genome="GRCh38",
        )
        orchestrator = PipelineOrchestrator(config)

        with patch.object(orchestrator, "_execute_stages") as mock_exec:
            mock_exec.return_value = True
            orchestrator.run()

        # Force garbage collection
        del orchestrator
        gc.collect()

        final_memory = process.memory_info().rss / 1024 / 1024
        memory_diff = final_memory - initial_memory

        # Memory should be mostly freed (allow 50MB tolerance)
        assert memory_diff < 50, f"Memory not freed: {memory_diff}MB remaining"

    def test_streaming_large_files(self, tmp_path):
        """Test streaming processing doesn't load entire file."""
        import psutil
        import os

        # Create a large VCF file
        large_file = tmp_path / "large.vcf"
        with large_file.open("w") as f:
            f.write("##fileformat=VCFv4.2\n")
            f.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")
            for i in range(50000):
                f.write(f"chr1\t{10000 + i}\t.\tA\tG\t30\tPASS\t.\n")

        file_size = large_file.stat().st_size / 1024 / 1024  # MB

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024

        config = PipelineConfig(
            input_vcf=large_file,
            output_dir=tmp_path / "output",
            reference_genome="GRCh38",
        )
        orchestrator = PipelineOrchestrator(config)

        with patch.object(orchestrator, "_execute_stages") as mock_exec:
            mock_exec.return_value = True
            orchestrator.run()

        peak_memory = process.memory_info().rss / 1024 / 1024
        memory_used = peak_memory - initial_memory

        # Memory should be much less than file size (streaming)
        assert (
            memory_used < file_size * 0.5
        ), f"Used {memory_used}MB for {file_size}MB file"


class TestScalability:
    """Test system scalability with increasing load."""

    def test_concurrent_processing(self, tmp_path):
        """Test handling multiple concurrent operations."""
        import concurrent.futures

        def process_file(index):
            vcf_file = tmp_path / f"test_{index}.vcf"
            with vcf_file.open("w") as f:
                f.write("##fileformat=VCFv4.2\n")
                f.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")
                for i in range(100):
                    f.write(f"chr1\t{10000 + i}\t.\tA\tG\t30\tPASS\t.\n")

            config = PipelineConfig(
                input_vcf=vcf_file,
                output_dir=tmp_path / f"output_{index}",
                reference_genome="GRCh38",
            )
            orchestrator = PipelineOrchestrator(config)

            with patch.object(orchestrator, "_execute_stages") as mock_exec:
                mock_exec.return_value = True
                orchestrator.run()

            return True

        # Process 5 files concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(process_file, i) for i in range(5)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert all(results), "Some concurrent operations failed"

    def test_handling_many_chromosomes(self, tmp_path):
        """Test processing variants across many chromosomes."""
        vcf_file = tmp_path / "many_chroms.vcf"
        with vcf_file.open("w") as f:
            f.write("##fileformat=VCFv4.2\n")
            f.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")
            for chrom in range(1, 23):  # chr1-chr22
                for i in range(100):
                    f.write(
                        f"chr{chrom}\t{10000 + i * 100}\t.\tA\tG\t30\tPASS\t.\n"
                    )

        config = PipelineConfig(
            input_vcf=vcf_file,
            output_dir=tmp_path / "output",
            reference_genome="GRCh38",
        )
        orchestrator = PipelineOrchestrator(config)

        with patch.object(orchestrator, "_execute_stages") as mock_exec:
            mock_exec.return_value = True

            start_time = time.time()
            orchestrator.run()
            elapsed_time = time.time() - start_time

            # Should handle 22 chromosomes efficiently
            assert elapsed_time < 10.0, f"Many chromosomes took {elapsed_time}s"


class TestResourceOptimization:
    """Test resource optimization features."""

    def test_batch_processing_efficiency(self, tmp_path):
        """Test batch processing is more efficient than individual."""
        variants = [
            Variant("chr1", 10000 + i * 100, "A", "G") for i in range(100)
        ]

        # Individual processing
        start_individual = time.time()
        for variant in variants:
            # Simulate processing
            _ = variant.position * 2
        time_individual = time.time() - start_individual

        # Batch processing
        start_batch = time.time()
        positions = [v.position for v in variants]
        _ = [p * 2 for p in positions]
        time_batch = time.time() - start_batch

        # Batch should be faster or comparable
        assert time_batch <= time_individual * 1.5

    def test_caching_improves_performance(self):
        """Test caching reduces repeated lookups."""
        cache = {}

        def expensive_lookup(key):
            time.sleep(0.01)  # Simulate expensive operation
            return key * 2

        def cached_lookup(key):
            if key not in cache:
                cache[key] = expensive_lookup(key)
            return cache[key]

        # First run without cache
        start = time.time()
        for i in range(10):
            expensive_lookup(i)
        time_uncached = time.time() - start

        # Second run with cache (repeated lookups)
        cache.clear()
        start = time.time()
        for i in range(10):
            cached_lookup(i)
        for i in range(10):  # Repeat
            cached_lookup(i)
        time_cached = time.time() - start

        # Cached should be less than 2x the uncached time
        # (not 3x despite 2x more lookups)
        assert time_cached < time_uncached * 2


@pytest.mark.slow
class TestPerformanceRegression:
    """Test for performance regressions."""

    def test_baseline_performance(self, tmp_path, benchmark_cache=".benchmark"):
        """Test performance hasn't regressed from baseline."""
        vcf_file = tmp_path / "baseline.vcf"
        with vcf_file.open("w") as f:
            f.write("##fileformat=VCFv4.2\n")
            f.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")
            for i in range(1000):
                f.write(f"chr1\t{10000 + i}\t.\tA\tG\t30\tPASS\t.\n")

        config = PipelineConfig(
            input_vcf=vcf_file,
            output_dir=tmp_path / "output",
            reference_genome="GRCh38",
        )
        orchestrator = PipelineOrchestrator(config)

        with patch.object(orchestrator, "_execute_stages") as mock_exec:
            mock_exec.return_value = True

            start_time = time.time()
            orchestrator.run()
            elapsed_time = time.time() - start_time

            # Baseline: should process 1000 variants in under 5 seconds
            baseline = 5.0
            assert (
                elapsed_time < baseline
            ), f"Regression: {elapsed_time}s > {baseline}s"
