#!/usr/bin/env python3
"""
varidex/io/loaders/gnomad.py - gnomAD Multi-Chromosome Loader v1.0.0 DEVELOPMENT

Load gnomAD population frequency data from per-chromosome VCF files.
Supports both exomes and genomes datasets with tabix indexing for fast lookups.

Author: VariDex Team
Version: 1.0.0 DEVELOPMENT
Date: 2026-01-28
"""

import pysam
import pandas as pd
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from tqdm import tqdm
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Standard chromosome list
VALID_CHROMOSOMES = [str(i) for i in range(1, 23)] + ["X", "Y", "MT"]


@dataclass
class GnomADFrequency:
    """Container for gnomAD allele frequency data."""

    # Core identifiers
    chromosome: str
    position: int
    ref_allele: str
    alt_allele: str

    # Overall frequencies
    af: Optional[float] = None  # Allele frequency
    ac: Optional[int] = None  # Allele count
    an: Optional[int] = None  # Allele number
    nhomalt: Optional[int] = None  # Number of homozygous alternates

    # Population-specific frequencies (major populations)
    af_afr: Optional[float] = None  # African/African American
    af_amr: Optional[float] = None  # Latino/Admixed American
    af_asj: Optional[float] = None  # Ashkenazi Jewish
    af_eas: Optional[float] = None  # East Asian
    af_fin: Optional[float] = None  # Finnish
    af_nfe: Optional[float] = None  # Non-Finnish European
    af_sas: Optional[float] = None  # South Asian

    # Quality flags
    filters: str = "PASS"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "chromosome": self.chromosome,
            "position": self.position,
            "ref_allele": self.ref_allele,
            "alt_allele": self.alt_allele,
            "gnomad_af": self.af,
            "gnomad_ac": self.ac,
            "gnomad_an": self.an,
            "gnomad_nhomalt": self.nhomalt,
            "gnomad_af_afr": self.af_afr,
            "gnomad_af_amr": self.af_amr,
            "gnomad_af_asj": self.af_asj,
            "gnomad_af_eas": self.af_eas,
            "gnomad_af_fin": self.af_fin,
            "gnomad_af_nfe": self.af_nfe,
            "gnomad_af_sas": self.af_sas,
            "gnomad_filters": self.filters,
        }


class GnomADLoader:
    """
    Multi-chromosome gnomAD data loader with tabix indexing.

    Handles per-chromosome VCF files (e.g., gnomad.exomes.r2.1.1.sites.1.vcf.bgz)
    Uses tabix for fast random access by genomic coordinates.
    """

    def __init__(
        self,
        gnomad_dir: Path,
        dataset: str = "exomes",
        version: str = "r2.1.1",
        auto_index: bool = True,
    ):
        """
        Initialize gnomAD loader.

        Args:
            gnomad_dir: Directory containing gnomAD chromosome files
            dataset: "exomes" or "genomes"
            version: gnomAD version (e.g., "r2.1.1", "v3.1.2")
            auto_index: Automatically create tabix indexes if missing
        """
        self.gnomad_dir = Path(gnomad_dir)
        self.dataset = dataset
        self.version = version
        self.auto_index = auto_index

        # Pattern for chromosome files
        self.file_pattern = f"gnomad.{dataset}.{version}.sites.{{chr}}.vcf.bgz"

        # Cache for open file handles
        self.vcf_handles: Dict[str, pysam.TabixFile] = {}

        # Validate directory
        if not self.gnomad_dir.exists():
            raise FileNotFoundError(f"gnomAD directory not found: {gnomad_dir}")

        logger.info(f"📂 gnomAD Loader initialized: {self.gnomad_dir}")
        logger.info(f"   Dataset: {dataset} | Version: {version}")

        # Scan for available chromosome files
        self.available_chroms = self._scan_chromosome_files()
        logger.info(
            f"   Found {len(self.available_chroms)} chromosome files: "
            f"{', '.join(sorted(self.available_chroms, key=lambda x: (not x.isdigit(), x)))}"
        )

    def _scan_chromosome_files(self) -> List[str]:
        """Scan directory for available chromosome files."""
        available = []
        for chrom in VALID_CHROMOSOMES:
            filepath = self.gnomad_dir / self.file_pattern.format(chr=chrom)
            if filepath.exists():
                available.append(chrom)

                # Check for index
                index_path = Path(str(filepath) + ".tbi")
                if not index_path.exists():
                    if self.auto_index:
                        logger.info(
                            f"🔨 Creating index for chromosome {chrom}..."
                        )
                        try:
                            pysam.tabix_index(
                                str(filepath), preset="vcf", force=True
                            )
                            logger.info(f"   ✓ Indexed chr{chrom}")
                        except Exception as e:
                            logger.warning(
                                f"   ✗ Failed to index chr{chrom}: {e}"
                            )
                    else:
                        logger.warning(
                            f"⚠️  Missing index for chr{chrom}: {index_path}"
                        )

        return available

    def _get_vcf_handle(self, chromosome: str) -> Optional[pysam.TabixFile]:
        """Get or open VCF file handle for chromosome."""
        # Normalize chromosome name
        chrom = chromosome.replace("chr", "").upper().replace("M", "MT")

        if chrom not in self.available_chroms:
            logger.debug(f"Chromosome {chrom} not available")
            return None

        # Return cached handle if exists
        if chrom in self.vcf_handles:
            return self.vcf_handles[chrom]

        # Open new handle
        filepath = self.gnomad_dir / self.file_pattern.format(chr=chrom)
        try:
            vcf = pysam.TabixFile(str(filepath))
            self.vcf_handles[chrom] = vcf
            return vcf
        except Exception as e:
            logger.error(f"Failed to open {filepath}: {e}")
            return None

    def lookup_variant(
        self, chromosome: str, position: int, ref: str, alt: str
    ) -> Optional[GnomADFrequency]:
        """
        Look up single variant frequency data.

        Args:
            chromosome: Chromosome (1-22, X, Y, MT)
            position: Genomic position
            ref: Reference allele
            alt: Alternate allele

        Returns:
            GnomADFrequency object or None if not found
        """
        vcf = self._get_vcf_handle(chromosome)
        if vcf is None:
            return None

        # Normalize chromosome for tabix query
        chrom = chromosome.replace("chr", "")

        try:
            # Query region (tabix uses 1-based coordinates)
            records = list(vcf.fetch(chrom, position - 1, position))

            for record_str in records:
                fields = record_str.split("\t")
                if len(fields) < 8:
                    continue

                rec_pos = int(fields[1])
                rec_ref = fields[3]
                rec_alt = fields[4]

                # Check if this is our variant
                if rec_pos == position and rec_ref == ref and rec_alt == alt:
                    return self._parse_variant_record(fields, chromosome)

            return None

        except Exception as e:
            logger.debug(f"Lookup failed for {chromosome}:{position}: {e}")
            return None

    def _parse_variant_record(
        self, fields: List[str], chromosome: str
    ) -> GnomADFrequency:
        """Parse VCF record fields into GnomADFrequency."""
        chrom = fields[0]
        pos = int(fields[1])
        ref = fields[3]
        alt = fields[4]
        info = fields[7]

        # Parse INFO field
        info_dict = self._parse_info_field(info)

        # Extract frequencies
        freq = GnomADFrequency(
            chromosome=chromosome,
            position=pos,
            ref_allele=ref,
            alt_allele=alt,
            af=self._safe_float(info_dict.get("AF")),
            ac=self._safe_int(info_dict.get("AC")),
            an=self._safe_int(info_dict.get("AN")),
            nhomalt=self._safe_int(info_dict.get("nhomalt")),
            af_afr=self._safe_float(info_dict.get("AF_afr")),
            af_amr=self._safe_float(info_dict.get("AF_amr")),
            af_asj=self._safe_float(info_dict.get("AF_asj")),
            af_eas=self._safe_float(info_dict.get("AF_eas")),
            af_fin=self._safe_float(info_dict.get("AF_fin")),
            af_nfe=self._safe_float(info_dict.get("AF_nfe")),
            af_sas=self._safe_float(info_dict.get("AF_sas")),
            filters=fields[6] if len(fields) > 6 else "PASS",
        )

        return freq

    def _parse_info_field(self, info: str) -> Dict[str, str]:
        """Parse VCF INFO field into dictionary."""
        info_dict = {}
        for item in info.split(";"):
            if "=" in item:
                key, value = item.split("=", 1)
                info_dict[key] = value
            else:
                info_dict[item] = "True"
        return info_dict

    def _safe_float(self, value: Optional[str]) -> Optional[float]:
        """Safely convert string to float."""
        if value is None or value == ".":
            return None
        try:
            # Handle comma-separated values (take first)
            if "," in value:
                value = value.split(",")[0]
            return float(value)
        except (ValueError, TypeError):
            return None

    def _safe_int(self, value: Optional[str]) -> Optional[int]:
        """Safely convert string to int."""
        if value is None or value == ".":
            return None
        try:
            # Handle comma-separated values (take first)
            if "," in value:
                value = value.split(",")[0]
            return int(value)
        except (ValueError, TypeError):
            return None

    def lookup_variants_batch(
        self, variants: List[Tuple[str, int, str, str]], show_progress: bool = True
    ) -> List[Optional[GnomADFrequency]]:
        """
        Batch lookup of variants.

        Args:
            variants: List of (chromosome, position, ref, alt) tuples
            show_progress: Show tqdm progress bar

        Returns:
            List of GnomADFrequency objects (None for not found)
        """
        results = []

        iterator = (
            tqdm(variants, desc="🧬 gnomAD lookup", unit="var")
            if show_progress
            else variants
        )

        for chrom, pos, ref, alt in iterator:
            result = self.lookup_variant(chrom, pos, ref, alt)
            results.append(result)

        return results

    def annotate_dataframe(
        self, df: pd.DataFrame, show_progress: bool = True
    ) -> pd.DataFrame:
        """
        Annotate DataFrame with gnomAD frequencies.

        Args:
            df: DataFrame with columns: chromosome, position, ref_allele, alt_allele
            show_progress: Show progress bar

        Returns:
            DataFrame with added gnomAD columns
        """
        required_cols = ["chromosome", "position", "ref_allele", "alt_allele"]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValueError(f"DataFrame missing required columns: {missing}")

        print(f"\n🧬 Annotating {len(df):,} variants with gnomAD frequencies...")

        # Prepare variant list
        variants = list(
            zip(
                df["chromosome"],
                df["position"],
                df["ref_allele"],
                df["alt_allele"],
            )
        )

        # Batch lookup
        frequencies = self.lookup_variants_batch(variants, show_progress)

        # Convert to records
        freq_records = [
            freq.to_dict() if freq else {} for freq in frequencies
        ]

        # Create frequency DataFrame
        freq_df = pd.DataFrame(freq_records)

        # Merge with original
        if not freq_df.empty:
            # Merge on coordinates
            result = df.merge(
                freq_df,
                on=["chromosome", "position", "ref_allele", "alt_allele"],
                how="left",
            )
        else:
            result = df.copy()
            # Add empty gnomAD columns
            for col in [
                "gnomad_af",
                "gnomad_ac",
                "gnomad_an",
                "gnomad_nhomalt",
            ]:
                result[col] = None

        # Report statistics
        found = sum(1 for f in frequencies if f is not None)
        print(
            f"  ✓ Found gnomAD data for {found:,}/{len(df):,} variants "
            f"({100*found/len(df):.1f}%)\n"
        )

        return result

    def get_statistics(self) -> Dict[str, Any]:
        """Get loader statistics."""
        return {
            "dataset": self.dataset,
            "version": self.version,
            "directory": str(self.gnomad_dir),
            "available_chromosomes": len(self.available_chroms),
            "chromosomes": sorted(
                self.available_chroms, key=lambda x: (not x.isdigit(), x)
            ),
            "open_handles": len(self.vcf_handles),
        }

    def close(self):
        """Close all open VCF handles."""
        for vcf in self.vcf_handles.values():
            vcf.close()
        self.vcf_handles.clear()
        logger.info("Closed all gnomAD file handles")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def load_gnomad_frequencies(
    variants_df: pd.DataFrame,
    gnomad_dir: Path,
    dataset: str = "exomes",
    version: str = "r2.1.1",
) -> pd.DataFrame:
    """
    Convenience function to annotate variants with gnomAD frequencies.

    Args:
        variants_df: DataFrame with variant coordinates
        gnomad_dir: Directory with gnomAD chromosome files
        dataset: "exomes" or "genomes"
        version: gnomAD version

    Returns:
        Annotated DataFrame
    """
    with GnomADLoader(gnomad_dir, dataset, version) as loader:
        return loader.annotate_dataframe(variants_df)


if __name__ == "__main__":
    # Example usage
    print("="*70)
    print("gnomAD Multi-Chromosome Loader v1.0.0 DEVELOPMENT")
    print("="*70)

    # Test initialization
    gnomad_dir = Path("./gnomad")
    if gnomad_dir.exists():
        loader = GnomADLoader(gnomad_dir, dataset="exomes", version="r2.1.1")
        print(f"\n📊 Statistics:")
        stats = loader.get_statistics()
        for key, value in stats.items():
            print(f"   {key}: {value}")

        # Test single lookup
        print(f"\n🔍 Test lookup: chr2:100000:A:G")
        result = loader.lookup_variant("2", 100000, "A", "G")
        if result:
            print(f"   ✓ Found: AF={result.af}, AC={result.ac}, AN={result.an}")
        else:
            print(f"   ✗ Not found")

        loader.close()
    else:
        print(f"\n⚠️  gnomAD directory not found: {gnomad_dir}")
        print("   Please create it and add chromosome files.")
