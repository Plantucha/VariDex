"""Comprehensive tests for data validation and sanitization."""

import pytest
import pandas as pd
from typing import Optional, List
from pathlib import Path


class TestVariantDataValidation:
    """Test variant data validation."""

    def test_valid_chromosome_names(self):
        """Test validation of chromosome names."""
        valid_chroms = [
            "1",
            "2",
            "X",
            "Y",
            "MT",
            "chr1",
            "chr2",
            "chrX",
            "chrY",
            "chrM",
        ]
        for chrom in valid_chroms:
            assert validate_chromosome(chrom)

    def test_invalid_chromosome_names(self):
        """Test rejection of invalid chromosome names."""
        invalid_chroms = ["", "0", "25", "chr25", "ABC", "1a", "chr"]
        for chrom in invalid_chroms:
            with pytest.raises(ValueError):
                validate_chromosome(chrom, strict=True)

    def test_valid_positions(self):
        """Test validation of genomic positions."""
        valid_positions = [1, 100, 1000000, 249250621]  # Max chr1 length
        for pos in valid_positions:
            assert validate_position(pos)

    def test_invalid_positions(self):
        """Test rejection of invalid positions."""
        invalid_positions = [0, -1, -100, 300000000]  # Exceeds chromosome length
        for pos in invalid_positions:
            with pytest.raises(ValueError):
                validate_position(pos, strict=True)

    def test_valid_nucleotides(self):
        """Test validation of nucleotide sequences."""
        valid_seqs = ["A", "T", "G", "C", "N", "ATGC", "atgc"]
        for seq in valid_seqs:
            assert validate_nucleotides(seq)

    def test_invalid_nucleotides(self):
        """Test rejection of invalid nucleotide sequences."""
        invalid_seqs = ["", "X", "Z", "123", "AT-GC", "A T"]
        for seq in invalid_seqs:
            with pytest.raises(ValueError):
                validate_nucleotides(seq, strict=True)

    def test_ref_alt_validation(self):
        """Test REF/ALT allele validation."""
        # Valid variations
        assert validate_ref_alt("A", "T")  # SNV
        assert validate_ref_alt("AT", "A")  # Deletion
        assert validate_ref_alt("A", "AT")  # Insertion
        assert validate_ref_alt("ATGC", "TAGC")  # MNV

        # Invalid variations
        with pytest.raises(ValueError):
            validate_ref_alt("", "A")  # Empty REF
        with pytest.raises(ValueError):
            validate_ref_alt("A", "")  # Empty ALT
        with pytest.raises(ValueError):
            validate_ref_alt("A", "A")  # Same as REF


class TestFrequencyValidation:
    """Test allele frequency validation."""

    def test_valid_frequencies(self):
        """Test validation of allele frequencies."""
        valid_freqs = [0.0, 0.001, 0.5, 0.999, 1.0]
        for freq in valid_freqs:
            assert validate_frequency(freq)

    def test_invalid_frequencies(self):
        """Test rejection of invalid frequencies."""
        invalid_freqs = [-0.1, -1.0, 1.1, 2.0, float("inf"), float("nan")]
        for freq in invalid_freqs:
            with pytest.raises(ValueError):
                validate_frequency(freq, strict=True)

    def test_frequency_precision(self):
        """Test frequency precision handling."""
        freq = 0.123456789
        validated = validate_frequency(freq, precision=4)
        assert validated == 0.1235

    def test_rare_variant_threshold(self):
        """Test identification of rare variants."""
        assert is_rare_variant(0.001, threshold=0.01)
        assert is_rare_variant(0.009, threshold=0.01)
        assert not is_rare_variant(0.011, threshold=0.01)
        assert not is_rare_variant(0.5, threshold=0.01)


class TestScoreValidation:
    """Test prediction score validation."""

    def test_valid_cadd_scores(self):
        """Test CADD score validation."""
        valid_scores = [0.0, 10.0, 20.0, 30.0, 40.0]
        for score in valid_scores:
            assert validate_cadd_score(score)

    def test_invalid_cadd_scores(self):
        """Test rejection of invalid CADD scores."""
        invalid_scores = [-1.0, -10.0, float("inf"), float("nan")]
        for score in invalid_scores:
            with pytest.raises(ValueError):
                validate_cadd_score(score, strict=True)

    def test_valid_revel_scores(self):
        """Test REVEL score validation (0-1 range)."""
        valid_scores = [0.0, 0.25, 0.5, 0.75, 1.0]
        for score in valid_scores:
            assert validate_revel_score(score)

    def test_invalid_revel_scores(self):
        """Test rejection of invalid REVEL scores."""
        invalid_scores = [-0.1, 1.1, 2.0, float("inf")]
        for score in invalid_scores:
            with pytest.raises(ValueError):
                validate_revel_score(score, strict=True)

    def test_score_interpretation(self):
        """Test score interpretation thresholds."""
        assert interpret_cadd_score(25.0) == "deleterious"
        assert interpret_cadd_score(15.0) == "moderate"
        assert interpret_cadd_score(5.0) == "benign"

        assert interpret_revel_score(0.8) == "pathogenic"
        assert interpret_revel_score(0.5) == "uncertain"
        assert interpret_revel_score(0.2) == "benign"


class TestDataFrameValidation:
    """Test DataFrame structure and content validation."""

    def test_required_columns_present(self):
        """Test that required columns are present."""
        df = pd.DataFrame(
            {
                "CHROM": ["1"],
                "POS": [12345],
                "REF": ["A"],
                "ALT": ["T"],
            }
        )
        assert validate_dataframe_columns(df, ["CHROM", "POS", "REF", "ALT"])

    def test_missing_required_columns(self):
        """Test error on missing required columns."""
        df = pd.DataFrame({"CHROM": ["1"], "POS": [12345]})
        with pytest.raises(ValueError):
            validate_dataframe_columns(df, ["CHROM", "POS", "REF", "ALT"], strict=True)

    def test_empty_dataframe(self):
        """Test handling of empty DataFrames."""
        df = pd.DataFrame()
        with pytest.raises(ValueError):
            validate_dataframe_not_empty(df)

    def test_duplicate_variants(self):
        """Test detection of duplicate variants."""
        df = pd.DataFrame(
            {
                "CHROM": ["1", "1", "1"],
                "POS": [100, 100, 200],
                "REF": ["A", "A", "G"],
                "ALT": ["T", "T", "C"],
            }
        )
        duplicates = find_duplicate_variants(df)
        assert len(duplicates) == 1  # One duplicate pair

    def test_dataframe_memory_size(self):
        """Test DataFrame memory size validation."""
        df = pd.DataFrame({"col": range(1000000)})
        size_mb = get_dataframe_size_mb(df)
        assert size_mb > 0
        assert validate_dataframe_size(df, max_mb=100)


class TestInputSanitization:
    """Test input data sanitization."""

    def test_sanitize_chromosome_names(self):
        """Test chromosome name normalization."""
        assert sanitize_chromosome("chr1") == "1"
        assert sanitize_chromosome("1") == "1"
        assert sanitize_chromosome("chrX") == "X"
        assert sanitize_chromosome("chrM") == "MT"
        assert sanitize_chromosome("chrMT") == "MT"

    def test_sanitize_case_sensitivity(self):
        """Test case-insensitive sanitization."""
        assert sanitize_nucleotides("atgc") == "ATGC"
        assert sanitize_nucleotides("AtGc") == "ATGC"

    def test_strip_whitespace(self):
        """Test whitespace stripping."""
        assert sanitize_string(" test ") == "test"
        assert sanitize_string("\ntest\t") == "test"

    def test_remove_special_characters(self):
        """Test special character removal."""
        assert sanitize_gene_name("GENE-123") == "GENE123"
        assert sanitize_gene_name("GENE_123") == "GENE_123"

    def test_sql_injection_prevention(self):
        """Test SQL injection attempt prevention."""
        malicious = "'; DROP TABLE variants; --"
        sanitized = sanitize_sql_input(malicious)
        assert "DROP" not in sanitized
        assert "--" not in sanitized


class TestBoundaryConditions:
    """Test boundary conditions and edge cases."""

    def test_max_chromosome_length(self):
        """Test maximum chromosome positions."""
        max_lengths = {
            "1": 249250621,
            "2": 243199373,
            "X": 155270560,
            "Y": 59373566,
            "MT": 16569,
        }
        for chrom, max_pos in max_lengths.items():
            assert validate_position(max_pos, chrom=chrom)
            with pytest.raises(ValueError):
                validate_position(max_pos + 1, chrom=chrom, strict=True)

    def test_very_long_sequences(self):
        """Test handling of very long sequences."""
        long_seq = "A" * 10000
        assert validate_nucleotides(long_seq, max_length=10000)
        with pytest.raises(ValueError):
            validate_nucleotides(long_seq, max_length=5000, strict=True)

    def test_zero_and_negative_values(self):
        """Test handling of zero and negative values."""
        assert validate_coverage(0, allow_zero=True)
        with pytest.raises(ValueError):
            validate_coverage(0, allow_zero=False)
        with pytest.raises(ValueError):
            validate_coverage(-10)

    def test_extreme_float_values(self):
        """Test handling of extreme float values."""
        with pytest.raises(ValueError):
            validate_frequency(float("inf"))
        with pytest.raises(ValueError):
            validate_frequency(float("-inf"))
        with pytest.raises(ValueError):
            validate_frequency(float("nan"))


class TestDataTypeValidation:
    """Test data type validation and conversion."""

    def test_integer_conversion(self):
        """Test safe integer conversion."""
        assert safe_int("123") == 123
        assert safe_int("123.0") == 123
        assert safe_int("invalid", default=0) == 0
        assert safe_int(None, default=-1) == -1

    def test_float_conversion(self):
        """Test safe float conversion."""
        assert safe_float("1.23") == 1.23
        assert safe_float("1.23e-4") == 0.000123
        assert safe_float("invalid", default=0.0) == 0.0
        assert safe_float(None, default=-1.0) == -1.0

    def test_boolean_conversion(self):
        """Test boolean conversion from strings."""
        assert safe_bool("true") is True
        assert safe_bool("TRUE") is True
        assert safe_bool("1") is True
        assert safe_bool("false") is False
        assert safe_bool("FALSE") is False
        assert safe_bool("0") is False

    def test_list_conversion(self):
        """Test list conversion from delimited strings."""
        assert safe_list("a,b,c") == ["a", "b", "c"]
        assert safe_list("a;b;c", delimiter=";") == ["a", "b", "c"]
        assert safe_list("") == []
        assert safe_list(None, default=[]) == []


# Validation helper functions


def validate_chromosome(chrom: str, strict: bool = False) -> bool:
    """Validate chromosome name."""
    valid = [str(i) for i in range(1, 23)] + ["X", "Y", "MT", "M"]
    valid += [f"chr{c}" for c in valid]
    if strict and chrom not in valid:
        raise ValueError(f"Invalid chromosome: {chrom}")
    return chrom in valid


def validate_position(
    pos: int, chrom: Optional[str] = None, strict: bool = False
) -> bool:
    """Validate genomic position."""
    if pos < 1:
        if strict:
            raise ValueError(f"Position must be positive: {pos}")
        return False
    return True


def validate_nucleotides(
    seq: str, max_length: Optional[int] = None, strict: bool = False
) -> bool:
    """Validate nucleotide sequence."""
    valid_bases = set("ATGCNatgcn")
    if not seq or not all(b in valid_bases for b in seq):
        if strict:
            raise ValueError(f"Invalid nucleotide sequence: {seq}")
        return False
    if max_length and len(seq) > max_length:
        if strict:
            raise ValueError(f"Sequence exceeds max length: {len(seq)} > {max_length}")
        return False
    return True


def validate_ref_alt(ref: str, alt: str) -> bool:
    """Validate REF and ALT alleles."""
    if not ref or not alt:
        raise ValueError("REF and ALT cannot be empty")
    if ref == alt:
        raise ValueError("REF and ALT must be different")
    validate_nucleotides(ref, strict=True)
    validate_nucleotides(alt, strict=True)
    return True


def validate_frequency(
    freq: float, precision: Optional[int] = None, strict: bool = False
) -> float:
    """Validate allele frequency."""
    import math

    if math.isnan(freq) or math.isinf(freq):
        if strict:
            raise ValueError(f"Invalid frequency: {freq}")
        return 0.0
    if freq < 0 or freq > 1:
        if strict:
            raise ValueError(f"Frequency out of range: {freq}")
        return max(0.0, min(1.0, freq))
    if precision:
        return round(freq, precision)
    return freq


def is_rare_variant(freq: float, threshold: float = 0.01) -> bool:
    """Check if variant is rare."""
    return freq < threshold


def validate_cadd_score(score: float, strict: bool = False) -> bool:
    """Validate CADD score."""
    import math

    if math.isnan(score) or math.isinf(score) or score < 0:
        if strict:
            raise ValueError(f"Invalid CADD score: {score}")
        return False
    return True


def validate_revel_score(score: float, strict: bool = False) -> bool:
    """Validate REVEL score (0-1)."""
    if score < 0 or score > 1:
        if strict:
            raise ValueError(f"REVEL score must be 0-1: {score}")
        return False
    return True


def interpret_cadd_score(score: float) -> str:
    """Interpret CADD score."""
    if score >= 20:
        return "deleterious"
    elif score >= 10:
        return "moderate"
    return "benign"


def interpret_revel_score(score: float) -> str:
    """Interpret REVEL score."""
    if score >= 0.7:
        return "pathogenic"
    elif score >= 0.3:
        return "uncertain"
    return "benign"


def validate_dataframe_columns(
    df: pd.DataFrame, required: List[str], strict: bool = False
) -> bool:
    """Validate DataFrame has required columns."""
    missing = set(required) - set(df.columns)
    if missing:
        if strict:
            raise ValueError(f"Missing required columns: {missing}")
        return False
    return True


def validate_dataframe_not_empty(df: pd.DataFrame) -> bool:
    """Validate DataFrame is not empty."""
    if df.empty:
        raise ValueError("DataFrame is empty")
    return True


def find_duplicate_variants(df: pd.DataFrame) -> pd.DataFrame:
    """Find duplicate variants in DataFrame."""
    return df[df.duplicated(subset=["CHROM", "POS", "REF", "ALT"], keep=False)]


def get_dataframe_size_mb(df: pd.DataFrame) -> float:
    """Get DataFrame size in MB."""
    return df.memory_usage(deep=True).sum() / (1024**2)


def validate_dataframe_size(df: pd.DataFrame, max_mb: float) -> bool:
    """Validate DataFrame size."""
    return get_dataframe_size_mb(df) <= max_mb


def sanitize_chromosome(chrom: str) -> str:
    """Normalize chromosome name."""
    chrom = chrom.strip().replace("chr", "")
    if chrom == "M":
        return "MT"
    return chrom


def sanitize_nucleotides(seq: str) -> str:
    """Normalize nucleotide sequence."""
    return seq.upper().strip()


def sanitize_string(s: str) -> str:
    """Sanitize string input."""
    return s.strip()


def sanitize_gene_name(name: str) -> str:
    """Sanitize gene name."""
    return name.replace("-", "")


def sanitize_sql_input(s: str) -> str:
    """Sanitize SQL input to prevent injection."""
    dangerous = ["DROP", "DELETE", "INSERT", "UPDATE", "--", ";", "/*", "*/"]
    for word in dangerous:
        s = s.replace(word, "")
    return s


def validate_coverage(coverage: int, allow_zero: bool = True) -> bool:
    """Validate coverage value."""
    if coverage < 0:
        raise ValueError(f"Coverage cannot be negative: {coverage}")
    if coverage == 0 and not allow_zero:
        raise ValueError("Coverage cannot be zero")
    return True


def safe_int(value, default: int = 0) -> int:
    """Safely convert to int."""
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def safe_float(value, default: float = 0.0) -> float:
    """Safely convert to float."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_bool(value, default: bool = False) -> bool:
    """Safely convert to bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ["true", "1", "yes"]
    return default


def safe_list(value, delimiter: str = ",", default: Optional[List] = None) -> List:
    """Safely convert to list."""
    if value is None or value == "":
        return default or []
    if isinstance(value, str):
        return [item.strip() for item in value.split(delimiter)]
    return default or []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
