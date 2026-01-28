"""
varidex/integrations/gnomad/query.py v6.4.0-dev

Query gnomAD VCF files for allele frequencies.

Development version - not for production use.
"""

import pysam
from pathlib import Path
from typing import Optional, Dict, Tuple
import logging
from dataclasses import dataclass

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

    def query(
        self, chromosome: str, position: int, ref: str, alt: str
    ) -> AlleleFrequency:
        vcf = self._get_vcf_handle(str(chromosome))
        if not vcf:
            return AlleleFrequency()
        try:
            for record in vcf.fetch(str(chromosome), position - 1, position):
                if record.pos == position and record.ref == ref:
                    for i, vcf_alt in enumerate(record.alts):
                        if vcf_alt == alt:
                            af = record.info.get("AF", [None])[i]
                            af_popmax = record.info.get("AF_popmax", None)
                            an = record.info.get("AN", None)
                            ac = record.info.get("AC", [None])[i]
                            return AlleleFrequency(
                                af=af if af is not None else None,
                                af_popmax=af_popmax,
                                an=an,
                                ac=ac if ac is not None else None,
                                found=True,
                            )
        except Exception as e:
            logger.error(f"Error querying gnomAD at {chromosome}:{position}: {e}")
        return AlleleFrequency()

    def close(self):
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
    with GnomADQuerier(gnomad_dir) as querier:
        result = querier.query(chromosome, position, ref, alt)
        return result.af, result.found
