#!/usr/bin/env python3

"""
ClinVar File Downloader with Space Management
Updates: First Thursday of each month
Version: 2026-01-17-v1
"""

import os
import sys
import datetime
import shutil
import urllib.request
from pathlib import Path
from typing import List, Tuple, Optional

# Configuration
FTP_BASE = "https://ftp.ncbi.nlm.nih.gov/pub/clinvar"
SAFETY_MARGIN_GB = 5  # Keep 5GB free space buffer

# Define files to download (filename, URL, approx_unzipped_size_MB)
FILES = [
    ("variant_summary.txt.gz", f"{FTP_BASE}/tab_delimited/variant_summary.txt.gz", 3000),
    ("var_citations.txt", f"{FTP_BASE}/tab_delimited/var_citations.txt", 50),
    ("cross_references.txt", f"{FTP_BASE}/tab_delimited/cross_references.txt", 100),
    ("organization_summary.txt", f"{FTP_BASE}/tab_delimited/organization_summary.txt", 5),
    ("submission_summary.txt", f"{FTP_BASE}/tab_delimited/submission_summary.txt", 500),
    ("clinvar_GRCh37.vcf.gz", f"{FTP_BASE}/vcf_GRCh37/clinvar.vcf.gz", 1500),
    ("clinvar_GRCh38.vcf.gz", f"{FTP_BASE}/vcf_GRCh38/clinvar.vcf.gz", 1500),
    ("ClinVarVCVRelease.xml.gz", f"{FTP_BASE}/xml/ClinVarVCVRelease_00-latest.xml.gz", 8000),
    (
        "ClinVarRCVRelease.xml.gz",
        f"{FTP_BASE}/xml/RCV_release/ClinVarRCVRelease_00-latest.xml.gz",
        12000,
    ),
]

# Sort by size (smallest first)
FILES.sort(key=lambda x: x[2])


def get_first_thursday(year: int, month: int) -> datetime.date:
    """Calculate the first Thursday of a given month."""
    first_day = datetime.date(year, month, 1)
    # Thursday is weekday 3 (Monday=0)
    days_until_thursday = (3 - first_day.weekday()) % 7
    if days_until_thursday == 0 and first_day.weekday() != 3:
        days_until_thursday = 7
    return first_day + datetime.timedelta(days=days_until_thursday)


def get_expected_update_date() -> datetime.date:
    """Get the most recent first Thursday (current or previous month)."""
    today = datetime.date.today()

    # First Thursday of current month
    first_thursday_current = get_first_thursday(today.year, today.month)

    # If we haven't reached this month's first Thursday yet, use last month
    if today < first_thursday_current:
        if today.month == 1:
            prev_year, prev_month = today.year - 1, 12
        else:
            prev_year, prev_month = today.year, today.month - 1
        return get_first_thursday(prev_year, prev_month)
    else:
        return first_thursday_current


def needs_update(filepath: Path, expected_date: datetime.date) -> Tuple[bool, str]:
    """Check if file needs updating."""
    if not filepath.exists():
        return True, "missing"

    # Get file modification time
    mtime = datetime.datetime.fromtimestamp(filepath.stat().st_mtime)
    file_date = mtime.date()

    if file_date < expected_date:
        return True, f"outdated ({file_date})"
    else:
        return False, f"current ({file_date})"


def get_available_space_mb(path: Path) -> int:
    """Get available disk space in MB."""
    stat = shutil.disk_usage(path)
    return stat.free // (1024 * 1024)


def download_file(url: str, filepath: Path) -> bool:
    """Download a file with progress indication."""
    try:
        print(f"  URL: {url}")

        def reporthook(block_num, block_size, total_size):
            if total_size > 0:
                percent = min(block_num * block_size * 100 / total_size, 100)
                sys.stdout.write(f"\r  Progress: {percent:.1f}%")
                sys.stdout.flush()

        urllib.request.urlretrieve(url, filepath, reporthook)
        print()  # New line after progress
        return True
    except Exception as e:
        print(f"\n  Error: {e}")
        return False


def main():
    # Get download directory from argument or use default
    if len(sys.argv) > 1:
        clinvar_dir = Path(sys.argv[1])
    else:
        clinvar_dir = Path("./clinvar_data")

    # Create directory if needed
    clinvar_dir.mkdir(parents=True, exist_ok=True)

    # Get expected update date
    expected_date = get_expected_update_date()
    today = datetime.date.today()

    print("=== ClinVar Download Manager ===")
    print(f"Download directory: {clinvar_dir.absolute()}")
    print(f"Expected last update: {expected_date}")
    print(f"Current date: {today}")
    print()

    # Check which files need updating
    to_download = []
    to_delete = []
    total_size_needed = 0

    print("Checking existing files...")
    for filename, url, size_mb in FILES:
        filepath = clinvar_dir / filename
        needs_dl, status = needs_update(filepath, expected_date)
        print(f"  {filename}: {status}")

        if needs_dl:
            to_download.append((filename, url, size_mb))
            total_size_needed += size_mb
            if filepath.exists():
                to_delete.append(filepath)

    if not to_download:
        print()
        print("All files are up to date. Nothing to download.")
        return 0

    print()
    print(f"Files needing update: {len(to_download)}")
    print(f"Estimated unzipped space needed: {total_size_needed} MB")

    # Check available space
    available_space_mb = get_available_space_mb(clinvar_dir)
    safety_margin_mb = SAFETY_MARGIN_GB * 1024
    usable_space_mb = available_space_mb - safety_margin_mb

    print(f"Available space (with {SAFETY_MARGIN_GB}GB buffer): {usable_space_mb} MB")
    print()

    # Delete outdated files
    if to_delete:
        print("Deleting outdated files...")
        for filepath in to_delete:
            print(f"  Removing: {filepath.name}")
            filepath.unlink()
        print()

    # Download files
    if usable_space_mb >= total_size_needed:
        print("Sufficient space available. Downloading all files...")
        print()
        for filename, url, size_mb in to_download:
            print(f"Downloading: {filename} (est. {size_mb}MB unzipped)")
            filepath = clinvar_dir / filename
            success = download_file(url, filepath)
            if not success:
                print(f"  Warning: Download failed for {filename}")
            print()
        print("All downloads complete.")
    else:
        print("Insufficient space for all files. Downloading what fits (smallest first)...")
        print()
        space_used = 0
        for filename, url, size_mb in to_download:
            if space_used + size_mb <= usable_space_mb:
                print(f"Downloading: {filename} (est. {size_mb}MB unzipped)")
                filepath = clinvar_dir / filename
                success = download_file(url, filepath)
                if success:
                    space_used += size_mb
                else:
                    print(f"  Warning: Download failed for {filename}")
                print()
            else:
                print(f"Skipping: {filename} (would exceed available space)")
        print(f"Downloaded files that fit in available space ({space_used}MB used).")

    print()
    print("Download process complete.")
    print(f"Files location: {clinvar_dir.absolute()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
