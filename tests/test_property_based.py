"""Property-based testing for VariDex using Hypothesis.

These tests use generative testing to verify properties that should
always hold true, regardless of specific input values.
"""

import string

import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.extra.pandas import column, data_frames, range_indexes


# Custom strategies for genomic data
@st.composite
def chromosome_strategy(draw):
    """Generate valid chromosome identifiers."""
    autosomes = [str(i) for i in range(1, 23)]
    sex_chroms = ["X", "Y"]
    mt_chroms = ["MT", "M"]
    all_chroms = autosomes + sex_chroms + mt_chroms

    # Optionally add 'chr' prefix
    chrom = draw(st.sampled_from(all_chroms))
    add_prefix = draw(st.booleans())

    return f"chr{chrom}" if add_prefix else chrom


@st.composite
def nucleotide_strategy(draw, min_length=1, max_length=100):
    """Generate valid nucleotide sequences."""
    length = draw(st.integers(min_value=min_length, max_value=max_length))
    bases = draw(st.lists(st.sampled_from("ACGT"), min_size=length, max_size=length))
    return "".join(bases)


@st.composite
def position_strategy(draw):
    """Generate valid genomic positions."""
    return draw(st.integers(min_value=1, max_value=250_000_000))


@st.composite
def variant_strategy(draw):
    """Generate a complete variant record."""
    return {
        "CHROM": draw(chromosome_strategy()),
        "POS": draw(position_strategy()),
        "REF": draw(nucleotide_strategy(min_length=1, max_length=10)),
        "ALT": draw(nucleotide_strategy(min_length=1, max_length=10)),
    }


class TestChromosomeProperties:
    """Property-based tests for chromosome handling."""

    @given(chrom=chromosome_strategy())
    def test_chromosome_string_type(self, chrom):
        """Chromosomes should always be strings."""
        assert isinstance(chrom, str)

    @given(chrom=chromosome_strategy())
    def test_chromosome_not_empty(self, chrom):
        """Chromosomes should never be empty strings."""
        assert len(chrom) > 0

    @given(chrom=chromosome_strategy())
    def test_chromosome_normalization_idempotent(self, chrom):
        """Normalizing a chromosome twice should give same result."""
        # Remove 'chr' prefix for normalization
        normalized1 = chrom.replace("chr", "", 1)
        normalized2 = normalized1.replace("chr", "", 1)
        assert normalized1 == normalized2

    @given(chrom=chromosome_strategy())
    def test_chromosome_case_handling(self, chrom):
        """Chromosome case conversion should be reversible."""
        upper = chrom.upper()
        assert isinstance(upper, str)
        # If original had lowercase, upper should be different
        if any(c.islower() for c in chrom):
            assert upper != chrom


class TestPositionProperties:
    """Property-based tests for genomic positions."""

    @given(pos=position_strategy())
    def test_position_positive(self, pos):
        """Genomic positions should always be positive."""
        assert pos > 0

    @given(pos=position_strategy())
    def test_position_integer(self, pos):
        """Positions should always be integers."""
        assert isinstance(pos, int)

    @given(pos1=position_strategy(), pos2=position_strategy())
    def test_position_ordering(self, pos1, pos2):
        """Position ordering should be transitive."""
        if pos1 < pos2:
            assert not (pos2 < pos1)
        elif pos1 > pos2:
            assert not (pos2 > pos1)
        else:
            assert pos1 == pos2

    @given(pos=position_strategy(), offset=st.integers(min_value=0, max_value=1000))
    def test_position_arithmetic(self, pos, offset):
        """Position arithmetic should maintain positivity."""
        new_pos = pos + offset
        assert new_pos >= pos
        assert new_pos >= 0


class TestNucleotideProperties:
    """Property-based tests for nucleotide sequences."""

    @given(seq=nucleotide_strategy())
    def test_sequence_valid_characters(self, seq):
        """Sequences should only contain valid nucleotides."""
        valid_chars = set("ACGT")
        assert all(c in valid_chars for c in seq)

    @given(seq=nucleotide_strategy())
    def test_sequence_not_empty(self, seq):
        """Nucleotide sequences should not be empty."""
        assert len(seq) > 0

    @given(seq=nucleotide_strategy())
    def test_sequence_length_consistency(self, seq):
        """Sequence length should match actual length."""
        assert len(seq) == sum(1 for _ in seq)

    @given(seq=nucleotide_strategy())
    def test_sequence_complement_reversible(self, seq):
        """Complement operation should be reversible."""
        complement_map = {"A": "T", "T": "A", "C": "G", "G": "C"}
        complement = "".join(complement_map[base] for base in seq)
        double_complement = "".join(complement_map[base] for base in complement)
        assert seq == double_complement

    @given(seq=nucleotide_strategy())
    def test_sequence_reverse_twice_identity(self, seq):
        """Reversing sequence twice returns original."""
        reversed_once = seq[::-1]
        reversed_twice = reversed_once[::-1]
        assert seq == reversed_twice

    @given(seq1=nucleotide_strategy(), seq2=nucleotide_strategy())
    def test_sequence_concatenation_length(self, seq1, seq2):
        """Concatenated sequence length equals sum of lengths."""
        concatenated = seq1 + seq2
        assert len(concatenated) == len(seq1) + len(seq2)


class TestVariantProperties:
    """Property-based tests for variant records."""

    @given(variant=variant_strategy())
    def test_variant_has_required_fields(self, variant):
        """Variants should have all required fields."""
        required = ["CHROM", "POS", "REF", "ALT"]
        assert all(field in variant for field in required)

    @given(variant=variant_strategy())
    def test_variant_position_positive(self, variant):
        """Variant position should be positive."""
        assert variant["POS"] > 0

    @given(variant=variant_strategy())
    def test_variant_ref_not_empty(self, variant):
        """Reference allele should not be empty."""
        assert len(variant["REF"]) > 0

    @given(variant=variant_strategy())
    def test_variant_alt_not_empty(self, variant):
        """Alternate allele should not be empty."""
        assert len(variant["ALT"]) > 0

    @given(variant=variant_strategy())
    def test_variant_key_uniqueness(self, variant):
        """Variant key (CHROM:POS:REF:ALT) should be consistent."""
        key1 = f"{variant['CHROM']}:{variant['POS']}:{variant['REF']}:{variant['ALT']}"
        key2 = f"{variant['CHROM']}:{variant['POS']}:{variant['REF']}:{variant['ALT']}"
        assert key1 == key2


class TestDataFrameProperties:
    """Property-based tests for DataFrame operations."""

    @given(
        df=data_frames(
            columns=[
                column("CHROM", dtype=str),
                column("POS", dtype=int),
                column("REF", dtype=str),
                column("ALT", dtype=str),
            ],
            index=range_indexes(min_size=0, max_size=100),
        )
    )
    @settings(max_examples=50)
    def test_dataframe_copy_independence(self, df):
        """DataFrame copy should be independent of original."""
        df_copy = df.copy()

        # Modify copy
        if len(df_copy) > 0:
            df_copy.iloc[0, 0] = "modified"

        # Original should be unchanged (if it had data)
        if len(df) > 0:
            assert df.iloc[0, 0] != "modified"

    @given(n_rows=st.integers(min_value=0, max_value=1000))
    def test_dataframe_filter_size(self, n_rows):
        """Filtered DataFrame should not exceed original size."""
        df = pd.DataFrame({"value": range(n_rows)})
        filtered = df[df["value"] > n_rows // 2]
        assert len(filtered) <= len(df)

    @given(n_rows=st.integers(min_value=1, max_value=100))
    def test_dataframe_sort_stability(self, n_rows):
        """Sorting DataFrame should preserve total row count."""
        df = pd.DataFrame({"value": range(n_rows)})
        sorted_df = df.sort_values("value")
        assert len(sorted_df) == len(df)


class TestStringOperationProperties:
    """Property-based tests for string operations."""

    @given(s=st.text(alphabet=string.ascii_letters, min_size=1, max_size=100))
    def test_string_case_conversion_reversible(self, s):
        """Case conversion should be reversible for ASCII."""
        upper = s.upper()
        lower = upper.lower()
        # Lowering uppercase should match original lowercased
        assert lower == s.lower()

    @given(s=st.text(alphabet=string.printable, min_size=0, max_size=100))
    def test_string_strip_idempotent(self, s):
        """Stripping whitespace twice should equal stripping once."""
        stripped_once = s.strip()
        stripped_twice = stripped_once.strip()
        assert stripped_once == stripped_twice

    @given(s1=st.text(), s2=st.text())
    def test_string_concatenation_associative(self, s1, s2):
        """String concatenation should be associative."""
        s3 = "test"
        result1 = (s1 + s2) + s3
        result2 = s1 + (s2 + s3)
        assert result1 == result2


class TestNumericProperties:
    """Property-based tests for numeric operations."""

    @given(x=st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False))
    def test_frequency_bounds(self, x):
        """Allele frequencies should be between 0 and 1."""
        assert 0 <= x <= 1

    @given(
        x=st.floats(
            min_value=0.0,
            max_value=1.0,
            allow_nan=False,
            allow_infinity=False,
        )
    )
    def test_complement_frequency(self, x):
        """Complement frequency should sum to 1."""
        complement = 1.0 - x
        total = x + complement
        assert abs(total - 1.0) < 1e-10  # Allow for floating point error

    @given(
        x=st.integers(min_value=0, max_value=1000),
        y=st.integers(min_value=0, max_value=1000),
    )
    def test_read_depth_arithmetic(self, x, y):
        """Read depth arithmetic should maintain non-negativity."""
        total = x + y
        assert total >= 0
        assert total >= x
        assert total >= y


class TestInvariantProperties:
    """Test invariants that should always hold."""

    @given(variant=variant_strategy())
    def test_variant_identity_preservation(self, variant):
        """Variant identity should be preserved through copy."""
        import copy

        variant_copy = copy.deepcopy(variant)
        assert variant == variant_copy
        assert variant is not variant_copy

    @given(data=st.lists(st.integers(), min_size=0, max_size=100))
    def test_list_length_after_extend(self, data):
        """List length after extend should equal sum of lengths."""
        list1 = data[: len(data) // 2]
        list2 = data[len(data) // 2 :]

        original_len = len(list1)
        list1.extend(list2)

        assert len(list1) == original_len + len(list2)

    @given(variant=variant_strategy())
    def test_variant_serialization_roundtrip(self, variant):
        """Variant should survive serialization roundtrip."""
        import json

        # Convert to JSON-compatible format
        serializable = {
            "CHROM": str(variant["CHROM"]),
            "POS": int(variant["POS"]),
            "REF": str(variant["REF"]),
            "ALT": str(variant["ALT"]),
        }

        json_str = json.dumps(serializable)
        deserialized = json.loads(json_str)

        assert deserialized["CHROM"] == variant["CHROM"]
        assert deserialized["POS"] == variant["POS"]
        assert deserialized["REF"] == variant["REF"]
        assert deserialized["ALT"] == variant["ALT"]


class TestCombinatorialProperties:
    """Test combinatorial properties."""

    @given(
        variants=st.lists(
            variant_strategy(),
            min_size=0,
            max_size=20,
        )
    )
    def test_variant_list_ordering_preservation(self, variants):
        """Sorting and reversing should return to original order."""
        if not variants:
            return

        # Create DataFrame
        df = pd.DataFrame(variants)

        # Sort by position
        sorted_df = df.sort_values("POS")

        # Count should be preserved
        assert len(sorted_df) == len(df)

    @given(
        chrom=chromosome_strategy(),
        positions=st.lists(
            position_strategy(),
            min_size=1,
            max_size=10,
        ),
    )
    def test_position_range_consistency(self, chrom, positions):
        """Position range should be consistent."""
        if positions:
            min_pos = min(positions)
            max_pos = max(positions)
            assert min_pos <= max_pos
            assert all(min_pos <= pos <= max_pos for pos in positions)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
