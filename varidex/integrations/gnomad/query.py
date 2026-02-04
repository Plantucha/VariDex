"""
varidex/integrations/gnomad/query.py v6.5.0-dev

Query gnomAD VCF files for allele frequencies.

Development version - not for production use.

Fixes:
- Robust INFO field parsing (handles scalar and list values)
- Type-safe array access
- Better error handling
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, Union

import pysam

logger = logging.getLogger(__name__)


@dataclass
class AlleleFrequency:
    """Container for allele frequency data."""

    af: Optional[float] = None
    af_popmax: Optional[float] = None
    an: Optional[int] = None
    ac: Optional[int] = None
    found: bool = False


class GnomADQuerier:
    """Query gnomAD VCF files for population frequencies."""

    def __init__(self, gnomad_dir: Path, build: str = "GRCh37"):
        self.gnomad_dir = Path(gnomad_dir)
        self.build = build
        self.vcf_handles = {}
        self._validate_files()

    def _validate_files(self):
        chromosomes = list(range(1, 23)) + ["X", "Y"]
        missing = []
        for chrom in chromosomes:
            vcf_path = self.gnomad_dir / f"gnomad.exomes.r2.1.1.sites.{chrom}.vcf.bgz"
            if not vcf_path.exists():
                missing.append(str(chrom))
        if missing:
            logger.warning(f"Missing gnomAD files for chromosomes: {missing}")

    def _get_vcf_handle(self, chromosome: str) -> Optional[pysam.VariantFile]:
        if chromosome not in self.vcf_handles:
            vcf_path = (
                self.gnomad_dir / f"gnomad.exomes.r2.1.1.sites.{chromosome}.vcf.bgz"
            )
            if not vcf_path.exists():
                logger.warning(f"gnomAD file not found: {vcf_path}")
                return None
            try:
                self.vcf_handles[chromosome] = pysam.VariantFile(str(vcf_path), "r")
            except Exception as e:
                logger.error(f"Failed to open {vcf_path}: {e}")
                return None
        return self.vcf_handles[chromosome]

    def _safe_get_info_value(
        self, record: pysam.VariantRecord, key: str, alt_index: int = 0
    ) -> Optional[Union[float, int]]:
        """
        Safely extract value from VCF INFO field.

        Handles both scalar and list values, prevents IndexError.

        Args:
            record: pysam VariantRecord
            key: INFO field key
            alt_index: Index for multi-allelic variants

        Returns:
            Value or None if not found/invalid
        """
        try:
            value = record.info.get(key, None)
            if value is None:
                return None

            # Handle list/tuple values
            if isinstance(value, (list, tuple)):
                if alt_index < len(value):
                    return value[alt_index]
                else:
                    logger.debug(f"Index {alt_index} out of range for {key}={value}")
                    return None
            # Handle scalar values
            else:
                # For multi-allelic sites, scalar applies to all alts
                return value if alt_index == 0 else None

        except Exception as e:
            logger.warning(f"Failed to extract INFO field '{key}': {e}")
            return None

    def query(
        self, chromosome: str, position: int, ref: str, alt: str
    ) -> AlleleFrequency:
        """Query gnomAD for variant allele frequency."""
        vcf = self._get_vcf_handle(str(chromosome))
        if not vcf:
            return AlleleFrequency()

        try:
            for record in vcf.fetch(str(chromosome), position - 1, position):
                if record.pos == position and record.ref == ref:
                    # Find matching alternate allele
                    for i, vcf_alt in enumerate(record.alts):
                        if vcf_alt == alt:
                            # Extract INFO fields with type-safe access
                            af = self._safe_get_info_value(record, "AF", i)
                            af_popmax = self._safe_get_info_value(
                                record, "AF_popmax", 0
                            )
                            an = self._safe_get_info_value(record, "AN", 0)
                            ac = self._safe_get_info_value(record, "AC", i)

                            return AlleleFrequency(
                                af=float(af) if af is not None else None,
                                af_popmax=(
                                    float(af_popmax) if af_popmax is not None else None
                                ),
                                an=int(an) if an is not None else None,
                                ac=int(ac) if ac is not None else None,
                                found=True,
                            )

        except Exception as e:
            logger.error(f"Error querying gnomAD at {chromosome}:{position}: {e}")

        return AlleleFrequency()

    def close(self):
        """Close all open VCF handles."""
        for vcf in self.vcf_handles.values():
            vcf.close()
        self.vcf_handles.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def query_allele_frequency(
    chromosome: str, position: int, ref: str, alt: str, gnomad_dir: Path
) -> Tuple[Optional[float], bool]:
    """Convenience function to query allele frequency."""
    with GnomADQuerier(gnomad_dir) as querier:
        result = querier.query(chromosome, position, ref, alt)
        return result.af, result.found
