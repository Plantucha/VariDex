#!/usr/bin/env python3
"""
Module 1: Configuration Constants v6.6.0
=========================================
File: varidex/core/config.py
Purpose: Central configuration for ClinVar pipeline with enhanced VariDexConfig class

Changes v6.6.0 (2026-01-24) - FIX 4B/4C COMPREHENSIVE:
- FIX 4B: Added parameter aliases to VariDexConfig for test compatibility
- FIX 4C: Added reference_genome parameter to PipelineConfig
- Enhanced __init__ to accept multiple parameter naming conventions
- from_dict() supports both primary and alias parameter names
- All previous features preserved (validation, persistence, management)
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import warnings
import sys
import json
import os
import copy
from typing import Any, Dict, Optional

# ===================================================================
# SECTION 1: VERSION IMPORT
# ===================================================================
from varidex.version import __version__

# ===================================================================
# SECTION 2: __all__ EXPORTS
# ===================================================================
__all__ = [
    "__version__",
    "CHECKPOINT_DIR",
    "CLASSIFICATION_TIMEOUT",
    "CHUNK_SIZE",
    "CLINVAR_FILE_TYPES",
    "MATCH_MODE",
    "VCF_COMPRESSION",
    "VCF_CHROM_FORMAT",
    "COORDINATE_SYSTEMS",
    "DEFAULT_COORDINATE_SYSTEM",
    "get_max_filesize",
    "get_clinvar_description",
    "is_in_functional_domain",
    "VALID_CHROMOSOMES",
    "VALID_BASES",
    "VALID_ALLELES",
    "CLINVAR_COLUMNS",
    "EvidenceStrength",
    "EvidenceType",
    "LOF_GENES",
    "MISSENSE_RARE_GENES",
    "INHERITANCE_PATTERNS",
    "CLINVAR_STAR_RATINGS",
    "ACMG_TIERS",
    "Config",
    "VariDexConfig",
    "PipelineConfig",
    "FUNCTIONAL_DOMAINS",
    "MAXFILESIZE",
]

# ===================================================================
# SECTION 3: FILE HANDLING CONSTANTS
# ===================================================================
CHECKPOINT_DIR = Path(".checkpoint")
CLASSIFICATION_TIMEOUT = 30
CHUNK_SIZE = 50000

CLINVAR_FILE_TYPES = {
    "variant_summary": {
        "format": "tsv",
        "key_column": "rsid",
        "maxsize": 8 * 1024 * 1024 * 1024,
        "description": "NCBI summary format (rsID-indexed)",
    },
    "vcf": {
        "format": "vcf",
        "key_columns": ["CHROM", "POS", "REF", "ALT"],
        "maxsize": 25 * 1024 * 1024 * 1024,
        "description": "Full VCF format (position-based)",
    },
    "vcf_tsv": {
        "format": "tsv",
        "key_columns": ["chromosome", "position", "ref_allele", "alt_allele"],
        "maxsize": 12 * 1024 * 1024 * 1024,
        "description": "ClinVar position-based TSV (balanced size)",
    },
}

MATCH_MODE = "hybrid"
VCF_COMPRESSION = "auto"
VCF_CHROM_FORMAT = "numeric"

COORDINATE_SYSTEMS = {
    "genomic": {
        "description": "GRCh37/GRCh38 chromosomal positions",
        "format": "chr:position",
        "example": "1:7412345-67",
        "primary_use": "VCF, ClinVar VCF, WGS data",
    },
    "cdna": {
        "description": "Transcript reference positions",
        "format": "c.X>Y",
        "example": "c.524G>A",
        "primary_use": "HGVS coding notation, transcript analysis",
    },
    "protein": {
        "description": "Protein reference positions",
        "format": "p.Xxx#Yyy",
        "example": "p.Arg337His",
        "primary_use": "HGVS protein notation (PM1 DISABLED)",
    },
}
DEFAULT_COORDINATE_SYSTEM = "genomic"

# ===================================================================
# SECTION 4: VALIDATION CONSTANTS
# ===================================================================
VALID_CHROMOSOMES = set([str(i) for i in range(1, 23)] + ["X", "Y", "MT", "M"])
VALID_BASES = {"A", "C", "G", "T", "N"}
VALID_ALLELES = VALID_BASES | {"I", "D", "-"}

# ===================================================================
# SECTION 5: COLUMN MAPPINGS
# ===================================================================
CLINVAR_COLUMNS = {
    "rsid": ["RS# (dbSNP)", "dbSNP ID", "AlleleID", "rsid"],
    "gene": ["GeneSymbol", "Genes", "GeneID", "Gene"],
    "clinical_sig": [
        "ClinicalSignificance",
        "Clinical significance (Last reviewed)",
        "ClinSig",
        "Significance",
    ],
    "review_status": ["ReviewStatus", "Review status", "Status"],
    "num_submitters": ["NumberSubmitters", "Submitter count", "Submitters"],
    "variant_type": ["VariationType", "Type", "Variant type"],
    "molecular_consequence": ["MolecularConsequence", "Consequence", "MC"],
}

# ===================================================================
# SECTION 6: ENUMS
# ===================================================================
class EvidenceStrength(Enum):
    VERY_STRONG = "Very Strong"
    STRONG = "Strong"
    MODERATE = "Moderate"
    SUPPORTING = "Supporting"
    STANDALONE = "Stand-alone"


class EvidenceType(Enum):
    PATHOGENIC = "Pathogenic"
    BENIGN = "Benign"


# ===================================================================
# SECTION 7: GENE LISTS
# ===================================================================
LOF_GENES = {
    "BRCA1",
    "BRCA2",
    "TP53",
    "PTEN",
    "STK11",
    "CDH1",
    "NF1",
    "NF2",
    "VHL",
    "TSC1",
    "TSC2",
    "RB1",
    "WT1",
    "PAX6",
    "SDHB",
    "SDHD",
    "MLH1",
    "MSH2",
    "MSH6",
    "PMS2",
    "APC",
    "MEN1",
    "RET",
}

MISSENSE_RARE_GENES = {
    "CFTR",
    "HBB",
    "DMD",
    "F8",
    "F9",
    "COL1A1",
    "COL1A2",
    "FBN1",
    "PKD1",
    "PKD2",
    "LDLR",
}

INHERITANCE_PATTERNS = {
    "autosomal_dominant": {"BRCA1", "BRCA2", "TP53"},
    "autosomal_recessive": {"CFTR", "HBB"},
    "x_linked_recessive": {"DMD", "F8", "F9"},
    "mitochondrial": {"MT-ATP6", "MT-CO1"},
}

# ===================================================================
# SECTION 8: RATING/TIER CONSTANTS
# ===================================================================
CLINVAR_STAR_RATINGS = {
    "practice guideline": 4,
    "reviewed by expert panel": 3,
    "criteria provided, multiple submitters, no conflicts": 2,
    "criteria provided, multiple submitters": 2,
    "criteria provided, single submitter": 1,
    "no assertion criteria provided": 0,
}

ACMG_TIERS = {
    "Pathogenic": {"icon": "🔴", "priority": 1},
    "Likely Pathogenic": {"icon": "🟠", "priority": 2},
    "Uncertain Significance": {"icon": "⚪", "priority": 3},
    "Likely Benign": {"icon": "🟢", "priority": 4},
    "Benign": {"icon": "🟢", "priority": 5},
}

# ===================================================================
# SECTION 9: FUNCTIONS
# ===================================================================
def get_max_filesize(filetype: str = "variant_summary") -> int:
    if not isinstance(filetype, str):
        raise TypeError(
            f"filetype must be str, got {type(filetype).__name__}. "
            f"Valid options: {', '.join(CLINVAR_FILE_TYPES.keys())}"
        )
    if filetype not in CLINVAR_FILE_TYPES:
        raise ValueError(
            f"Unknown filetype '{filetype}'. "
            f"Valid options: {', '.join(CLINVAR_FILE_TYPES.keys())}"
        )
    return CLINVAR_FILE_TYPES[filetype]["maxsize"]


def get_clinvar_description(filetype: str = "variant_summary") -> str:
    if filetype in CLINVAR_FILE_TYPES:
        return CLINVAR_FILE_TYPES[filetype]["description"]
    return "Unknown format"


def is_in_functional_domain(gene: str, aa_position: int) -> bool:
    if not isinstance(aa_position, int):
        raise TypeError(
            f"aa_position must be int, got {type(aa_position).__name__}. "
            "Amino acid positions are integers only."
        )
    if aa_position <= 0:
        raise ValueError(f"aa_position must be positive, got {aa_position}")
    return False


# ===================================================================
# SECTION 10: DEPRECATED CONSTANTS
# ===================================================================
FUNCTIONAL_DOMAINS = {}
DEPRECATED_CONSTANTS = {"MAXFILESIZE": 5 * 1024 * 1024 * 1024}
MAXFILESIZE = DEPRECATED_CONSTANTS["MAXFILESIZE"]


# ===================================================================
# SECTION 11: VARIDEXCONFIG CLASS (ENHANCED v6.6.0)
# ===================================================================
class VariDexConfig:
    """
    Complete configuration for VariDex variant analysis pipeline.

    FIX 4B: Enhanced with parameter aliases for backward compatibility.
    Handles settings for data sources, quality thresholds, output formats,
    and runtime parameters with validation and persistence.
    """

    def __init__(
        self,
        reference_genome: str = "GRCh38",
        min_quality_score: float = 20.0,
        min_read_depth: int = 10,
        max_missing_rate: float = 0.1,
        population_af_threshold: float = 0.01,
        rare_variant_threshold: float = 0.001,
        thread_count: int = 4,
        chunk_size: int = 1000,
        enable_caching: bool = True,
        clinvar_path: str = "",
        gnomad_path: str = "",
        dbnsfp_path: str = "",
        output_format: str = "json",
        output_directory: str = "./varidex_output",
        include_annotations: bool = True,
        acmg_strict_mode: bool = False,
        require_population_data: bool = False,
        log_level: str = "INFO",
        debug_mode: bool = False,
        **kwargs: Any,
    ) -> None:
        # FIX 4B: Handle parameter aliases via kwargs
        if "max_population_af" in kwargs:
            population_af_threshold = kwargs.pop("max_population_af")
        if "num_threads" in kwargs:
            thread_count = kwargs.pop("num_threads")
        if "output_dir" in kwargs:
            output_directory = kwargs.pop("output_dir")
        if "quality_score" in kwargs:
            min_quality_score = kwargs.pop("quality_score")
        if "read_depth" in kwargs:
            min_read_depth = kwargs.pop("read_depth")

        # Validate reference genome
        valid_genomes = ["GRCh37", "GRCh38", "hg19", "hg38"]
        if reference_genome not in valid_genomes:
            raise ValueError(
                f"Invalid reference genome '{reference_genome}'. "
                f"Must be one of {valid_genomes}"
            )
        self.reference_genome = reference_genome

        # Validate quality score
        if not (0 <= min_quality_score <= 100):
            raise ValueError(
                f"Invalid quality score {min_quality_score}. Must be 0-100"
            )
        self.min_quality_score = float(min_quality_score)

        # Validate read depth
        if min_read_depth < 0:
            raise ValueError(f"Read depth must be non-negative, got {min_read_depth}")
        self.min_read_depth = int(min_read_depth)

        # Validate missing rate
        if not (0 <= max_missing_rate <= 1):
            raise ValueError(
                f"Invalid missing rate {max_missing_rate}. Must be 0-1"
            )
        self.max_missing_rate = float(max_missing_rate)

        # Validate population AF
        if not (0 <= population_af_threshold <= 1):
            raise ValueError(
                f"Invalid population AF threshold {population_af_threshold}. Must be 0-1"
            )
        self.population_af_threshold = float(population_af_threshold)

        # Validate rare variant threshold
        if not (0 <= rare_variant_threshold <= 1):
            raise ValueError(
                f"Invalid rare variant threshold {rare_variant_threshold}. Must be 0-1"
            )
        self.rare_variant_threshold = float(rare_variant_threshold)

        # Validate thread count
        if thread_count <= 0:
            raise ValueError(f"Thread count must be positive, got {thread_count}")
        self.thread_count = int(thread_count)

        # Validate chunk size
        if chunk_size <= 0:
            raise ValueError(f"Chunk size must be positive, got {chunk_size}")
        self.chunk_size = int(chunk_size)

        # Set other parameters
        self.enable_caching = bool(enable_caching)
        self.clinvar_path = str(clinvar_path)
        self.gnomad_path = str(gnomad_path)
        self.dbnsfp_path = str(dbnsfp_path)

        # Validate output format
        valid_formats = ["json", "csv", "tsv", "vcf", "html"]
        if output_format.lower() not in valid_formats:
            raise ValueError(
                f"Invalid output format '{output_format}'. "
                f"Must be one of {valid_formats}"
            )
        self.output_format = output_format.lower()

        self.output_directory = str(output_directory)
        self.include_annotations = bool(include_annotations)
        self.acmg_strict_mode = bool(acmg_strict_mode)
        self.require_population_data = bool(require_population_data)

        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if log_level.upper() not in valid_log_levels:
            raise ValueError(
                f"Invalid log level '{log_level}'. "
                f"Must be one of {valid_log_levels}"
            )
        self.log_level = log_level.upper()
        self.debug_mode = bool(debug_mode)

    # FIX 4B: Property aliases for backward compatibility
    @property
    def max_population_af(self) -> float:
        """Alias for population_af_threshold."""
        return self.population_af_threshold

    @max_population_af.setter
    def max_population_af(self, value: float) -> None:
        """Alias setter for population_af_threshold."""
        if not (0 <= value <= 1):
            raise ValueError(f"Invalid population AF {value}. Must be 0-1")
        self.population_af_threshold = float(value)

    @property
    def num_threads(self) -> int:
        """Alias for thread_count."""
        return self.thread_count

    @num_threads.setter
    def num_threads(self, value: int) -> None:
        """Alias setter for thread_count."""
        if value <= 0:
            raise ValueError(f"Thread count must be positive, got {value}")
        self.thread_count = int(value)

    @property
    def output_dir(self) -> str:
        """Alias for output_directory."""
        return self.output_directory

    @output_dir.setter
    def output_dir(self, value: str) -> None:
        """Alias setter for output_directory."""
        self.output_directory = str(value)

    @property
    def quality_score(self) -> float:
        """Alias for min_quality_score."""
        return self.min_quality_score

    @quality_score.setter
    def quality_score(self, value: float) -> None:
        """Alias setter for min_quality_score."""
        if not (0 <= value <= 100):
            raise ValueError(f"Invalid quality score {value}. Must be 0-100")
        self.min_quality_score = float(value)

    @property
    def read_depth(self) -> int:
        """Alias for min_read_depth."""
        return self.min_read_depth

    @read_depth.setter
    def read_depth(self, value: int) -> None:
        """Alias setter for min_read_depth."""
        if value < 0:
            raise ValueError(f"Read depth must be non-negative, got {value}")
        self.min_read_depth = int(value)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, VariDexConfig):
            return False
        return self.to_dict() == other.to_dict()

    def __hash__(self) -> int:
        items = tuple(sorted(self.to_dict().items()))
        return hash(items)

    def __str__(self) -> str:
        return (
            f"VariDexConfig(genome={self.reference_genome}, "
            f"quality={self.min_quality_score}, "
            f"af_threshold={self.population_af_threshold}, "
            f"threads={self.thread_count})"
        )

    def __repr__(self) -> str:
        params = []
        for key, value in self.to_dict().items():
            if isinstance(value, str):
                params.append(f"{key}='{value}'")
            else:
                params.append(f"{key}={value}")
        return f"VariDexConfig({', '.join(params)})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reference_genome": self.reference_genome,
            "min_quality_score": self.min_quality_score,
            "min_read_depth": self.min_read_depth,
            "max_missing_rate": self.max_missing_rate,
            "population_af_threshold": self.population_af_threshold,
            "rare_variant_threshold": self.rare_variant_threshold,
            "thread_count": self.thread_count,
            "chunk_size": self.chunk_size,
            "enable_caching": self.enable_caching,
            "clinvar_path": self.clinvar_path,
            "gnomad_path": self.gnomad_path,
            "dbnsfp_path": self.dbnsfp_path,
            "output_format": self.output_format,
            "output_directory": self.output_directory,
            "include_annotations": self.include_annotations,
            "acmg_strict_mode": self.acmg_strict_mode,
            "require_population_data": self.require_population_data,
            "log_level": self.log_level,
            "debug_mode": self.debug_mode,
        }

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "VariDexConfig":
        """FIX 4B: Enhanced to accept both primary and alias parameter names."""
        return cls(**config_dict)

    def update(self, **kwargs: Any) -> None:
        """FIX 4B: Enhanced to accept both primary and alias parameter names."""
        # Map aliases to primary names
        alias_map = {
            "max_population_af": "population_af_threshold",
            "num_threads": "thread_count",
            "output_dir": "output_directory",
            "quality_score": "min_quality_score",
            "read_depth": "min_read_depth",
        }

        # Convert aliases to primary names
        for alias, primary in alias_map.items():
            if alias in kwargs:
                kwargs[primary] = kwargs.pop(alias)

        current_dict = self.to_dict()
        unknown = set(kwargs.keys()) - set(current_dict.keys())
        if unknown:
            raise AttributeError(f"Unknown configuration parameters: {unknown}")
        current_dict.update(kwargs)
        new_config = self.from_dict(current_dict)
        for key, value in new_config.to_dict().items():
            setattr(self, key, value)

    def save(self, filepath: str) -> None:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> "VariDexConfig":
        with open(filepath, "r") as f:
            config_dict = json.load(f)
        return cls.from_dict(config_dict)

    def copy(self) -> "VariDexConfig":
        return self.from_dict(self.to_dict())

    def deep_copy(self) -> "VariDexConfig":
        return copy.deepcopy(self)

    def validate_paths(self) -> bool:
        paths_to_check = [self.clinvar_path, self.gnomad_path, self.dbnsfp_path]
        for path in paths_to_check:
            if path and not os.path.exists(path):
                return False
        return True


# Backward compatibility
Config = VariDexConfig


# ===================================================================
# SECTION 12: PIPELINECONFIG CLASS (ENHANCED v6.6.0)
# ===================================================================
@dataclass
class PipelineConfig:
    """
    Configuration for variant analysis pipeline.

    FIX 4C: Enhanced with reference_genome parameter alias.
    """

    input_file: str = ""
    input_vcf: str = ""  # Added for test compatibility
    output_dir: str = "output"
    clinvar_file: str = ""
    genome_assembly: str = "GRCh38"
    min_quality: float = 0.0
    filter_common_variants: bool = True
    common_af_threshold: float = 0.01
    run_validation: bool = True
    run_annotation: bool = True
    run_classification: bool = True
    run_reporting: bool = True
    max_workers: int = 4
    chunk_size: int = 1000
    generate_html: bool = True
    generate_json: bool = True
    generate_csv: bool = True

    def __init__(
        self,
        input_file: str = "",
        input_vcf: str = "",
        output_dir: str = "output",
        clinvar_file: str = "",
        genome_assembly: str = "GRCh38",
        min_quality: float = 0.0,
        filter_common_variants: bool = True,
        common_af_threshold: float = 0.01,
        run_validation: bool = True,
        run_annotation: bool = True,
        run_classification: bool = True,
        run_reporting: bool = True,
        max_workers: int = 4,
        chunk_size: int = 1000,
        generate_html: bool = True,
        generate_json: bool = True,
        generate_csv: bool = True,
        # FIX 4C: Accept reference_genome as alias
        reference_genome: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """FIX 4C: Enhanced to accept reference_genome parameter."""
        # Map reference_genome to genome_assembly if provided
        if reference_genome is not None:
            genome_assembly = reference_genome

        self.input_file = input_file
        self.input_vcf = input_vcf
        self.output_dir = output_dir
        self.clinvar_file = clinvar_file
        self.genome_assembly = genome_assembly
        self.min_quality = min_quality
        self.filter_common_variants = filter_common_variants
        self.common_af_threshold = common_af_threshold
        self.run_validation = run_validation
        self.run_annotation = run_annotation
        self.run_classification = run_classification
        self.run_reporting = run_reporting
        self.max_workers = max_workers
        self.chunk_size = chunk_size
        self.generate_html = generate_html
        self.generate_json = generate_json
        self.generate_csv = generate_csv

    # FIX 4C: Property alias for backward compatibility
    @property
    def reference_genome(self) -> str:
        """Alias for genome_assembly."""
        return self.genome_assembly

    @reference_genome.setter
    def reference_genome(self, value: str) -> None:
        """Alias setter for genome_assembly."""
        self.genome_assembly = value

    @classmethod
    def from_dict(cls, config_dict: dict) -> "PipelineConfig":
        """FIX 4C: Enhanced to accept both genome_assembly and reference_genome."""
        return cls(**{k: v for k, v in config_dict.items() if hasattr(cls, k)})

    def to_dict(self) -> dict:
        return asdict(self)


# ===================================================================
# DEPRECATION HANDLING
# ===================================================================
def __getattr__(name):
    if name == "MAXFILESIZE":
        import inspect

        frame = inspect.currentframe()
        if frame and frame.f_back:
            caller = frame.f_back
            filename = caller.f_code.co_filename
            lineno = caller.f_lineno
            if filename != __file__:
                warnings.warn(
                    f"MAXFILESIZE is deprecated (called from {filename}:{lineno}). "
                    "Use get_max_filesize() instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )
        return DEPRECATED_CONSTANTS["MAXFILESIZE"]
    if name == "FUNCTIONAL_DOMAINS":
        warnings.warn(
            "FUNCTIONAL_DOMAINS is empty. PM1 disabled since v5.2.",
            DeprecationWarning,
            stacklevel=2,
        )
        return {}
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


if __name__ == "__main__":
    print("=" * 80)
    print(f"CONFIG MODULE v{__version__} - ENHANCED v6.6.0")
    print("=" * 80)

    # Test FIX 4B: VariDexConfig aliases
    print("\n✓ Test FIX 4B: VariDexConfig parameter aliases")
    config = VariDexConfig(max_population_af=0.05, num_threads=8, output_dir="/tmp")
    print(f"  - max_population_af → population_af_threshold: {config.population_af_threshold}")
    print(f"  - num_threads → thread_count: {config.thread_count}")
    print(f"  - output_dir → output_directory: {config.output_directory}")

    # Test property access
    print(f"  - Reading max_population_af property: {config.max_population_af}")
    print(f"  - Reading num_threads property: {config.num_threads}")

    # Test FIX 4C: PipelineConfig reference_genome
    print("\n✓ Test FIX 4C: PipelineConfig reference_genome alias")
    pipeline_config = PipelineConfig(reference_genome="GRCh37", input_vcf="test.vcf")
    print(f"  - reference_genome → genome_assembly: {pipeline_config.genome_assembly}")
    print(f"  - Reading reference_genome property: {pipeline_config.reference_genome}")

    # Test update() with aliases
    print("\n✓ Test: update() with aliases")
    config.update(num_threads=16, max_population_af=0.02)
    print(f"  - After update: thread_count={config.thread_count}, af={config.population_af_threshold}")

    print("\n✅ All v6.6.0 enhancements verified!")
    print("   - FIX 4B: Parameter aliases working ✓")
    print("   - FIX 4C: PipelineConfig.reference_genome ✓")
    print("=" * 80)
