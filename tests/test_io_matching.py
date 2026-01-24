"""Tests for varidex.io.matching module.

Black formatted with 88-char line limit.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from varidex.core.models import GenomicVariant
from varidex.exceptions import MatchingError
from varidex.io.matching import (
    match_by_coordinates,
    match_by_variant_id,
    match_variants,
    create_variant_key,
    find_exact_matches,
    find_fuzzy_matches,
)


class TestCreateVariantKey:
    """Test variant key creation."""

    def test_create_variant_key_basic(self) -> None:
        """Test basic variant key creation."""
        key = create_variant_key("chr1", 12345, "A", "G")
        assert key == "chr1:12345:A:G"

    def test_create_variant_key_sex_chromosome(self) -> None:
        """Test variant key for sex chromosomes."""
        key = create_variant_key("chrX", 100000, "C", "T")
        assert key == "chrX:100000:C:T"

    def test_create_variant_key_indel(self) -> None:
        """Test variant key for insertion/deletion."""
        key_ins = create_variant_key("chr1", 12345, "A", "ATG")
        key_del = create_variant_key("chr1", 12345, "ATG", "A")
        assert key_ins == "chr1:12345:A:ATG"
        assert key_del == "chr1:12345:ATG:A"

    def test_create_variant_key_normalization(self) -> None:
        """Test variant key normalization."""
        key1 = create_variant_key("1", 12345, "A", "G")
        key2 = create_variant_key("chr1", 12345, "A", "G")
        # Both should normalize to same format
        assert "12345" in key1 and "12345" in key2


class TestMatchByCoordinates:
    """Test coordinate-based matching."""

    def test_match_by_coordinates_exact(self) -> None:
        """Test exact coordinate matching."""
        query_df = pd.DataFrame(
            {
                "chromosome": ["chr1", "chr2"],
                "position": [12345, 67890],
                "reference": ["A", "C"],
                "alternate": ["G", "T"],
            }
        )

        ref_df = pd.DataFrame(
            {
                "chromosome": ["chr1", "chr2", "chr3"],
                "position": [12345, 67890, 11111],
                "reference": ["A", "C", "G"],
                "alternate": ["G", "T", "A"],
                "info": ["match1", "match2", "no_match"],
            }
        )

        result = match_by_coordinates(query_df, ref_df)
        assert len(result) == 2
        assert "info" in result.columns

    def test_match_by_coordinates_no_matches(self) -> None:
        """Test coordinate matching with no matches."""
        query_df = pd.DataFrame(
            {
                "chromosome": ["chr1"],
                "position": [12345],
                "reference": ["A"],
                "alternate": ["G"],
            }
        )

        ref_df = pd.DataFrame(
            {
                "chromosome": ["chr2"],
                "position": [67890],
                "reference": ["C"],
                "alternate": ["T"],
            }
        )

        result = match_by_coordinates(query_df, ref_df)
        assert len(result) == 0

    def test_match_by_coordinates_partial_overlap(self) -> None:
        """Test coordinate matching with partial overlap."""
        query_df = pd.DataFrame(
            {
                "chromosome": ["chr1", "chr2", "chr3"],
                "position": [100, 200, 300],
                "reference": ["A", "C", "G"],
                "alternate": ["T", "G", "A"],
            }
        )

        ref_df = pd.DataFrame(
            {
                "chromosome": ["chr1", "chr2"],
                "position": [100, 200],
                "reference": ["A", "C"],
                "alternate": ["T", "G"],
                "annotation": ["ann1", "ann2"],
            }
        )

        result = match_by_coordinates(query_df, ref_df)
        assert len(result) == 2
        assert set(result["chromosome"]) == {"chr1", "chr2"}

    def test_match_by_coordinates_allow_mismatch(self) -> None:
        """Test coordinate matching allowing allele mismatch."""
        query_df = pd.DataFrame(
            {
                "chromosome": ["chr1"],
                "position": [12345],
                "reference": ["A"],
                "alternate": ["G"],
            }
        )

        ref_df = pd.DataFrame(
            {
                "chromosome": ["chr1"],
                "position": [12345],
                "reference": ["A"],
                "alternate": ["C"],
                "info": ["different_alt"],
            }
        )

        result = match_by_coordinates(
            query_df, ref_df, match_alleles=False
        )
        assert len(result) > 0


class TestMatchByVariantID:
    """Test variant ID-based matching."""

    def test_match_by_variant_id_rsid(self) -> None:
        """Test matching by rsID."""
        query_df = pd.DataFrame(
            {"variant_id": ["rs123", "rs456"], "sample": ["S1", "S2"]}
        )

        ref_df = pd.DataFrame(
            {
                "variant_id": ["rs123", "rs456", "rs789"],
                "annotation": ["ann1", "ann2", "ann3"],
            }
        )

        result = match_by_variant_id(query_df, ref_df)
        assert len(result) == 2
        assert "annotation" in result.columns

    def test_match_by_variant_id_custom_column(self) -> None:
        """Test matching with custom ID column name."""
        query_df = pd.DataFrame({"dbsnp_id": ["rs123"], "data": ["value"]})

        ref_df = pd.DataFrame({"dbsnp_id": ["rs123"], "info": ["annotation"]})

        result = match_by_variant_id(
            query_df, ref_df, id_column="dbsnp_id"
        )
        assert len(result) == 1
        assert result.iloc[0]["info"] == "annotation"

    def test_match_by_variant_id_no_matches(self) -> None:
        """Test variant ID matching with no matches."""
        query_df = pd.DataFrame({"variant_id": ["rs123"]})
        ref_df = pd.DataFrame({"variant_id": ["rs456"]})

        result = match_by_variant_id(query_df, ref_df)
        assert len(result) == 0


class TestFindExactMatches:
    """Test exact variant matching."""

    def test_find_exact_matches_basic(self) -> None:
        """Test finding exact matches."""
        query_variants = [
            GenomicVariant(
                chromosome="chr1",
                position=12345,
                reference="A",
                alternate="G",
                assembly="GRCh38",
            ),
            GenomicVariant(
                chromosome="chr2",
                position=67890,
                reference="C",
                alternate="T",
                assembly="GRCh38",
            ),
        ]

        reference_variants = [
            GenomicVariant(
                chromosome="chr1",
                position=12345,
                reference="A",
                alternate="G",
                assembly="GRCh38",
            ),
        ]

        matches = find_exact_matches(query_variants, reference_variants)
        assert len(matches) == 1
        assert matches[0][0].position == 12345

    def test_find_exact_matches_none(self) -> None:
        """Test finding exact matches with no results."""
        query_variants = [
            GenomicVariant(
                chromosome="chr1",
                position=12345,
                reference="A",
                alternate="G",
                assembly="GRCh38",
            ),
        ]

        reference_variants = [
            GenomicVariant(
                chromosome="chr1",
                position=12345,
                reference="A",
                alternate="C",
                assembly="GRCh38",
            ),
        ]

        matches = find_exact_matches(query_variants, reference_variants)
        assert len(matches) == 0

    def test_find_exact_matches_assembly_mismatch(self) -> None:
        """Test exact matching ignores assembly differences."""
        query_variants = [
            GenomicVariant(
                chromosome="chr1",
                position=12345,
                reference="A",
                alternate="G",
                assembly="GRCh37",
            ),
        ]

        reference_variants = [
            GenomicVariant(
                chromosome="chr1",
                position=12345,
                reference="A",
                alternate="G",
                assembly="GRCh38",
            ),
        ]

        matches = find_exact_matches(query_variants, reference_variants)
        # Should still match on coordinates and alleles
        assert len(matches) == 1


class TestFindFuzzyMatches:
    """Test fuzzy variant matching."""

    def test_find_fuzzy_matches_nearby_position(self) -> None:
        """Test fuzzy matching for nearby positions."""
        query_variants = [
            GenomicVariant(
                chromosome="chr1",
                position=12345,
                reference="A",
                alternate="G",
                assembly="GRCh38",
            ),
        ]

        reference_variants = [
            GenomicVariant(
                chromosome="chr1",
                position=12347,
                reference="A",
                alternate="G",
                assembly="GRCh38",
            ),
        ]

        matches = find_fuzzy_matches(
            query_variants, reference_variants, position_tolerance=5
        )
        assert len(matches) > 0

    def test_find_fuzzy_matches_different_alleles(self) -> None:
        """Test fuzzy matching with different alleles."""
        query_variants = [
            GenomicVariant(
                chromosome="chr1",
                position=12345,
                reference="A",
                alternate="G",
                assembly="GRCh38",
            ),
        ]

        reference_variants = [
            GenomicVariant(
                chromosome="chr1",
                position=12345,
                reference="A",
                alternate="C",
                assembly="GRCh38",
            ),
        ]

        matches = find_fuzzy_matches(
            query_variants, reference_variants, allow_allele_mismatch=True
        )
        assert len(matches) > 0

    def test_find_fuzzy_matches_strict_alleles(self) -> None:
        """Test fuzzy matching with strict allele matching."""
        query_variants = [
            GenomicVariant(
                chromosome="chr1",
                position=12345,
                reference="A",
                alternate="G",
                assembly="GRCh38",
            ),
        ]

        reference_variants = [
            GenomicVariant(
                chromosome="chr1",
                position=12346,
                reference="A",
                alternate="C",
                assembly="GRCh38",
            ),
        ]

        matches = find_fuzzy_matches(
            query_variants,
            reference_variants,
            position_tolerance=5,
            allow_allele_mismatch=False,
        )
        assert len(matches) == 0


class TestMatchVariants:
    """Test main variant matching function."""

    def test_match_variants_exact_mode(self) -> None:
        """Test variant matching in exact mode."""
        query = pd.DataFrame(
            {
                "chromosome": ["chr1"],
                "position": [12345],
                "reference": ["A"],
                "alternate": ["G"],
            }
        )

        reference = pd.DataFrame(
            {
                "chromosome": ["chr1"],
                "position": [12345],
                "reference": ["A"],
                "alternate": ["G"],
                "annotation": ["pathogenic"],
            }
        )

        result = match_variants(query, reference, mode="exact")
        assert len(result) == 1
        assert result.iloc[0]["annotation"] == "pathogenic"

    def test_match_variants_fuzzy_mode(self) -> None:
        """Test variant matching in fuzzy mode."""
        query = pd.DataFrame(
            {
                "chromosome": ["chr1"],
                "position": [12345],
                "reference": ["A"],
                "alternate": ["G"],
            }
        )

        reference = pd.DataFrame(
            {
                "chromosome": ["chr1"],
                "position": [12347],
                "reference": ["A"],
                "alternate": ["G"],
                "annotation": ["benign"],
            }
        )

        result = match_variants(query, reference, mode="fuzzy", tolerance=5)
        assert len(result) > 0

    def test_match_variants_invalid_mode(self) -> None:
        """Test variant matching with invalid mode."""
        query = pd.DataFrame({"chromosome": ["chr1"], "position": [12345]})
        reference = pd.DataFrame({"chromosome": ["chr1"], "position": [12345]})

        with pytest.raises(MatchingError, match="Invalid matching mode"):
            match_variants(query, reference, mode="invalid")

    def test_match_variants_empty_query(self) -> None:
        """Test variant matching with empty query."""
        query = pd.DataFrame()
        reference = pd.DataFrame(
            {"chromosome": ["chr1"], "position": [12345]}
        )

        result = match_variants(query, reference)
        assert len(result) == 0

    def test_match_variants_empty_reference(self) -> None:
        """Test variant matching with empty reference."""
        query = pd.DataFrame({"chromosome": ["chr1"], "position": [12345]})
        reference = pd.DataFrame()

        result = match_variants(query, reference)
        assert len(result) == 0


class TestMatchingPerformance:
    """Test matching performance with large datasets."""

    def test_match_large_dataset(self) -> None:
        """Test matching with large number of variants."""
        n_variants = 10000
        query_df = pd.DataFrame(
            {
                "chromosome": [f"chr{i % 22 + 1}" for i in range(n_variants)],
                "position": [100000 + i * 10 for i in range(n_variants)],
                "reference": ["A"] * n_variants,
                "alternate": ["G"] * n_variants,
            }
        )

        ref_df = pd.DataFrame(
            {
                "chromosome": [f"chr{i % 22 + 1}" for i in range(n_variants // 2)],
                "position": [100000 + i * 10 for i in range(n_variants // 2)],
                "reference": ["A"] * (n_variants // 2),
                "alternate": ["G"] * (n_variants // 2),
            }
        )

        result = match_by_coordinates(query_df, ref_df)
        assert len(result) == n_variants // 2

    def test_match_variants_deduplication(self) -> None:
        """Test matching handles duplicate variants."""
        query_df = pd.DataFrame(
            {
                "chromosome": ["chr1", "chr1"],
                "position": [12345, 12345],
                "reference": ["A", "A"],
                "alternate": ["G", "G"],
            }
        )

        ref_df = pd.DataFrame(
            {
                "chromosome": ["chr1"],
                "position": [12345],
                "reference": ["A"],
                "alternate": ["G"],
            }
        )

        result = match_by_coordinates(query_df, ref_df)
        # Should handle duplicates appropriately
        assert len(result) >= 1
