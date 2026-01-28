#!/usr/bin/env python3

"""
varidex/pipeline/file_utils.py - File Utilities v1.0.0-dev
File detection, validation, and freshness checking.
Development version - not for production use.
"""

import gzip
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

logger: logging.Logger = logging.getLogger(__name__)


class FileTypeDetectionError(Exception):
    """Raised when file type cannot be determined."""


def validate_input_path(path: Path, name: str) -> Path:
    """Validate and resolve input file path for security."""
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as e:
        raise FileNotFoundError(f"{name} not found: {path}") from e
    if not resolved.is_file():
        raise ValueError(f"{name} is not a file: {resolved}")
    if resolved.is_symlink():
        logger.warning(f"⚠️ Symbolic link detected: {name}")
    logger.debug(f"✓ Validated {name}: {resolved}")
    return resolved


def detect_data_file_type(file_path: Path, strict: bool = True) -> str:
    """Auto-detect genomic data format: vcf, 23andme, or position_tsv."""
    logger.info(f"  Detecting format: {file_path.name}")
    try:
        if str(file_path).endswith(".gz"):
            with gzip.open(file_path, "rt", encoding="utf-8") as f:
                first_line: str = f.readline().lower()
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                first_line = f.readline().lower()

        if first_line.startswith("##fileformat=vcf") or first_line.startswith("#chrom"):
            logger.info("  → VCF format")
            return "vcf"

        if "rsid" in first_line and "chromosome" in first_line and "genotype" in first_line:
            logger.info("  → 23andMe format")
            return "23andme"

        if "chromosome" in first_line and "position" in first_line:
            logger.info("  → Position TSV format")
            return "position_tsv"

        if strict:
            raise FileTypeDetectionError(
                f"Cannot determine file type: {file_path.name}\n"
                f"Expected: VCF, 23andMe, or Position TSV format\n"
                f"Solution: Use --format vcf|23andme|tsv"
            )

        logger.warning("  → Defaulting to 23andMe (AMBIGUOUS)")
        return "23andme"

    except IOError as e:
        if strict:
            raise FileTypeDetectionError(f"Cannot read file: {e}") from e
        logger.warning(f"Detection failed: {e}, defaulting to 23andMe")
        return "23andme"


def check_clinvar_freshness(
    file_path: Path,
    max_age_days: int = 45,
    force: bool = False,
    interactive: bool = True,
) -> bool:
    """Check if ClinVar database file is recent enough."""
    if max_age_days < 0:
        raise ValueError(f"max_age_days must be positive, got {max_age_days}")

    if force:
        logger.info("  ⚡ Skipping freshness check (--force)")
        return True

    try:
        mtime: datetime = datetime.fromtimestamp(file_path.stat().st_mtime)
        days_old: int = (datetime.now() - mtime).days
    except OSError as e:
        logger.error(f"Cannot access file: {e}")
        if not force:
            raise
        return True

    if days_old > max_age_days:
        msg = (
            f"⚠️ ClinVar is {days_old} days old (max: {max_age_days})\n"
            f"   Download latest: ftp://ftp.ncbi.nlm.nih.gov/pub/clinvar/"
        )
        logger.warning(msg)

        if not interactive:
            raise ValueError(f"ClinVar too old. Use --force to override.")

        print(msg)
        response: str = input("  Continue? (type 'yes'): ").strip()
        if response.lower() != "yes":
            logger.info("User declined to continue")
            return False
    else:
        logger.info(f"  ✓ ClinVar OK ({days_old} days)")

    return True
