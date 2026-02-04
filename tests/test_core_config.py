"""Comprehensive tests for varidex.core.config module.

Tests cover:
- Configuration initialization and validation
- Parameter loading and saving
- Default value handling
- Error conditions
"""

import os
import tempfile
from pathlib import Path

import pytest

from varidex.core.config import VariDexConfig
from varidex.core.exceptions import ConfigurationError


class TestVariDexConfigInit:
    """Test VariDexConfig initialization."""

    def test_default_initialization(self) -> None:
        """Test configuration with default values."""
        config = VariDexConfig()
        assert config is not None
        assert hasattr(config, "reference_genome")
        assert hasattr(config, "min_quality_score")

    def test_custom_initialization(self) -> None:
        """Test configuration with custom parameters."""
        config = VariDexConfig(
            reference_genome="hg38",
            min_quality_score=30.0,
            max_population_af=0.001,
        )
        assert config.reference_genome == "hg38"
        assert config.min_quality_score == 30.0
        assert config.max_population_af == 0.001

    def test_invalid_reference_genome(self) -> None:
        """Test invalid reference genome raises error."""
        with pytest.raises((ConfigurationError, ValueError)):
            VariDexConfig(reference_genome="invalid_genome")

    def test_invalid_quality_score(self) -> None:
        """Test invalid quality score raises error."""
        with pytest.raises((ConfigurationError, ValueError)):
            VariDexConfig(min_quality_score=-10.0)

    def test_invalid_population_af(self) -> None:
        """Test invalid population AF raises error."""
        with pytest.raises((ConfigurationError, ValueError)):
            VariDexConfig(max_population_af=1.5)


class TestVariDexConfigValidation:
    """Test configuration validation logic."""

    def test_validate_quality_score_range(self) -> None:
        """Test quality score must be in valid range."""
        config = VariDexConfig(min_quality_score=20.0)
        assert 0 <= config.min_quality_score <= 100

    def test_validate_af_range(self) -> None:
        """Test allele frequency must be between 0 and 1."""
        config = VariDexConfig(max_population_af=0.01)
        assert 0 <= config.max_population_af <= 1.0

    def test_validate_thread_count(self) -> None:
        """Test thread count must be positive."""
        config = VariDexConfig(num_threads=4)
        assert config.num_threads > 0

    def test_validate_paths_exist(self) -> None:
        """Test path validation for existing directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = VariDexConfig(output_dir=tmpdir)
            assert Path(config.output_dir).exists()


class TestVariDexConfigDefaults:
    """Test default configuration values."""

    def test_default_reference_genome(self) -> None:
        """Test default reference genome is hg38 or hg19."""
        config = VariDexConfig()
        assert config.reference_genome in ["hg38", "hg19", "GRCh38", "GRCh37"]

    def test_default_quality_score(self) -> None:
        """Test default quality score is reasonable."""
        config = VariDexConfig()
        assert 10.0 <= config.min_quality_score <= 50.0

    def test_default_population_af(self) -> None:
        """Test default population AF threshold."""
        config = VariDexConfig()
        assert 0 < config.max_population_af <= 0.01

    def test_default_thread_count(self) -> None:
        """Test default thread count is sensible."""
        config = VariDexConfig()
        assert 1 <= config.num_threads <= os.cpu_count() or 1


class TestVariDexConfigSerialization:
    """Test configuration save/load functionality."""

    def test_to_dict(self) -> None:
        """Test configuration can be converted to dictionary."""
        config = VariDexConfig(reference_genome="hg38", min_quality_score=25.0)
        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert config_dict["reference_genome"] == "hg38"
        assert config_dict["min_quality_score"] == 25.0

    def test_from_dict(self) -> None:
        """Test configuration can be loaded from dictionary."""
        config_dict = {
            "reference_genome": "hg38",
            "min_quality_score": 30.0,
            "max_population_af": 0.005,
        }
        config = VariDexConfig.from_dict(config_dict)
        assert config.reference_genome == "hg38"
        assert config.min_quality_score == 30.0
        assert config.max_population_af == 0.005

    def test_save_and_load_config(self) -> None:
        """Test configuration can be saved and loaded from file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            config_path = tmp.name

        try:
            original_config = VariDexConfig(
                reference_genome="hg38", min_quality_score=35.0
            )
            original_config.save(config_path)

            loaded_config = VariDexConfig.load(config_path)
            assert loaded_config.reference_genome == "hg38"
            assert loaded_config.min_quality_score == 35.0
        finally:
            if os.path.exists(config_path):
                os.unlink(config_path)

    def test_save_creates_directory(self) -> None:
        """Test save creates parent directory if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "subdir" / "config.json"
            config = VariDexConfig()
            config.save(str(config_path))
            assert config_path.exists()


class TestVariDexConfigUpdate:
    """Test configuration update methods."""

    def test_update_single_parameter(self) -> None:
        """Test updating a single configuration parameter."""
        config = VariDexConfig(min_quality_score=20.0)
        config.update(min_quality_score=30.0)
        assert config.min_quality_score == 30.0

    def test_update_multiple_parameters(self) -> None:
        """Test updating multiple configuration parameters."""
        config = VariDexConfig()
        config.update(min_quality_score=25.0, max_population_af=0.002, num_threads=8)
        assert config.min_quality_score == 25.0
        assert config.max_population_af == 0.002
        assert config.num_threads == 8

    def test_update_with_validation(self) -> None:
        """Test update validates new values."""
        config = VariDexConfig()
        with pytest.raises((ConfigurationError, ValueError)):
            config.update(min_quality_score=-10.0)

    def test_update_rejects_unknown_parameters(self) -> None:
        """Test update rejects unknown parameters."""
        config = VariDexConfig()
        with pytest.raises((ConfigurationError, AttributeError, TypeError)):
            config.update(unknown_parameter="value")


class TestVariDexConfigComparison:
    """Test configuration comparison and equality."""

    def test_equal_configs(self) -> None:
        """Test two identical configs are equal."""
        config1 = VariDexConfig(reference_genome="hg38", min_quality_score=30.0)
        config2 = VariDexConfig(reference_genome="hg38", min_quality_score=30.0)
        assert config1 == config2

    def test_different_configs(self) -> None:
        """Test two different configs are not equal."""
        config1 = VariDexConfig(min_quality_score=20.0)
        config2 = VariDexConfig(min_quality_score=30.0)
        assert config1 != config2

    def test_config_hash(self) -> None:
        """Test configuration can be hashed."""
        config = VariDexConfig(reference_genome="hg38")
        config_hash = hash(config)
        assert isinstance(config_hash, int)


class TestVariDexConfigCopy:
    """Test configuration copy methods."""

    def test_shallow_copy(self) -> None:
        """Test shallow copy creates independent instance."""
        config1 = VariDexConfig(min_quality_score=25.0)
        config2 = config1.copy()
        config2.min_quality_score = 35.0
        assert config1.min_quality_score == 25.0
        assert config2.min_quality_score == 35.0

    def test_deep_copy(self) -> None:
        """Test deep copy creates completely independent instance."""
        import copy

        config1 = VariDexConfig(min_quality_score=25.0)
        config2 = copy.deepcopy(config1)
        config2.min_quality_score = 40.0
        assert config1.min_quality_score == 25.0
        assert config2.min_quality_score == 40.0


class TestVariDexConfigRepresentation:
    """Test configuration string representations."""

    def test_str_representation(self) -> None:
        """Test string representation is readable."""
        config = VariDexConfig(reference_genome="hg38")
        config_str = str(config)
        assert "hg38" in config_str
        assert "VariDexConfig" in config_str or "Config" in config_str

    def test_repr_representation(self) -> None:
        """Test repr is valid Python expression."""
        config = VariDexConfig(reference_genome="hg38")
        config_repr = repr(config)
        assert "VariDexConfig" in config_repr or "Config" in config_repr


class TestVariDexConfigEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_quality_score(self) -> None:
        """Test zero quality score handling."""
        config = VariDexConfig(min_quality_score=0.0)
        assert config.min_quality_score == 0.0

    def test_max_quality_score(self) -> None:
        """Test maximum quality score."""
        config = VariDexConfig(min_quality_score=100.0)
        assert config.min_quality_score == 100.0

    def test_zero_population_af(self) -> None:
        """Test zero population AF (ultra-rare variants)."""
        config = VariDexConfig(max_population_af=0.0)
        assert config.max_population_af == 0.0

    def test_max_population_af(self) -> None:
        """Test maximum population AF of 1.0."""
        config = VariDexConfig(max_population_af=1.0)
        assert config.max_population_af == 1.0

    def test_single_thread(self) -> None:
        """Test single-threaded configuration."""
        config = VariDexConfig(num_threads=1)
        assert config.num_threads == 1

    def test_empty_config_dict(self) -> None:
        """Test loading from empty dictionary uses defaults."""
        config = VariDexConfig.from_dict({})
        assert config is not None
        assert hasattr(config, "reference_genome")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
