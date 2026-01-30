#!/usr/bin/env python3
"""
ClinVar XML Byte-Offset Indexer - Phase 3 (v8.2.0)

Builds and caches byte-offset indexes for instant chromosome seeking.
Enables 30-60 second loads with <500MB RAM.

Index Format:
{
    'chromosomes': {
        '1': [(byte_offset, variant_id), ...],
        '2': [(byte_offset, variant_id), ...],
        ...
    },
    'metadata': {
        'total_variants': 4300000,
        'xml_size': 70000000000,
        'index_version': '1.0',
        'created': '2026-01-29T19:00:00',
    }
}
"""

import gzip
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from lxml import etree
from tqdm import tqdm

logger = logging.getLogger(__name__)

# ClinVar XML namespace
NS = {"cv": "http://www.ncbi.nlm.nih.gov/clinvar/release"}

INDEX_VERSION = "1.0"


def build_xml_index(
    xml_path: Path,
    force_rebuild: bool = False,
) -> Dict:
    """
    Build byte-offset index for ClinVar XML file.

    Args:
        xml_path: Path to UNCOMPRESSED XML file (not .gz)
        force_rebuild: Rebuild even if cached index exists

    Returns:
        Index dict with chromosome -> [(offset, variant_id), ...]

    Performance:
        - First run: 20-30 minutes (one-time cost)
        - Subsequent runs: <1 second (loads from cache)
        - Memory: <1GB during indexing

    Note:
        Requires uncompressed XML. If you have .xml.gz, decompress first:
        gunzip -k ClinVarVCVRelease.xml.gz
    """
    logger.info(f"Building XML index for: {xml_path.name}")

    # Check if compressed
    if str(xml_path).endswith(".gz"):
        raise ValueError(
            "Indexed mode requires UNCOMPRESSED XML. "
            "Decompress first: gunzip -k yourfile.xml.gz"
        )

    # Check for cached index
    index_path = _get_index_path(xml_path)
    if index_path.exists() and not force_rebuild:
        logger.info(f"Loading cached index from: {index_path.name}")
        return load_xml_index(xml_path)

    # Build new index
    logger.info("Building new index (this will take 20-30 minutes)...")

    index = {
        "chromosomes": {},
        "metadata": {
            "xml_file": xml_path.name,
            "xml_size": xml_path.stat().st_size,
            "index_version": INDEX_VERSION,
            "created": datetime.now().isoformat(),
        },
    }

    total_variants = 0
    chromosome_counts = {}

    with open(xml_path, "rb") as f:
        # Estimate total variants for progress bar
        file_size = xml_path.stat().st_size
        estimated_variants = 4_300_000  # Typical ClinVar size

        with tqdm(
            total=estimated_variants,
            desc="Indexing XML",
            unit="var",
            unit_scale=True,
        ) as pbar:
            # Use iterparse to get byte offsets
            for event, elem in etree.iterparse(
                f,
                events=("end",),
                tag=f"{{{NS['cv']}}}VariationArchive",
            ):
                # Get byte offset BEFORE processing
                # Note: f.tell() gives position after element
                byte_offset = f.tell()

                # Extract variant ID and chromosome
                variant_id = elem.get("VariationID")
                chromosome = _extract_chromosome_for_index(elem)

                if variant_id and chromosome:
                    # Add to index
                    if chromosome not in index["chromosomes"]:
                        index["chromosomes"][chromosome] = []
                        chromosome_counts[chromosome] = 0

                    index["chromosomes"][chromosome].append(
                        (byte_offset, variant_id)
                    )
                    chromosome_counts[chromosome] += 1
                    total_variants += 1

                # Clean up memory
                elem.clear()
                while elem.getprevious() is not None:
                    del elem.getparent()[0]

                pbar.update(1)

    # Update metadata
    index["metadata"]["total_variants"] = total_variants
    index["metadata"]["chromosome_counts"] = chromosome_counts

    logger.info(f"Index built: {total_variants:,} variants across {len(index['chromosomes'])} chromosomes")
    for chrom in sorted(index["chromosomes"].keys()):
        count = len(index["chromosomes"][chrom])
        logger.info(f"  Chr {chrom}: {count:,} variants")

    # Save index to cache
    save_xml_index(xml_path, index)

    return index


def load_xml_index(xml_path: Path) -> Dict:
    """
    Load cached XML index.

    Args:
        xml_path: Path to XML file (index is stored alongside)

    Returns:
        Index dict

    Raises:
        FileNotFoundError: If index doesn't exist
    """
    index_path = _get_index_path(xml_path)

    if not index_path.exists():
        raise FileNotFoundError(
            f"Index not found: {index_path}. "
            "Run build_xml_index() first."
        )

    logger.info(f"Loading index from: {index_path.name}")

    with gzip.open(index_path, "rt") as f:
        index = json.load(f)

    # Convert string keys back to chromosome names
    # and tuple strings back to tuples
    if "chromosomes" in index:
        for chrom in index["chromosomes"]:
            # Convert list of lists to list of tuples
            index["chromosomes"][chrom] = [
                tuple(item) for item in index["chromosomes"][chrom]
            ]

    logger.info(
        f"Index loaded: {index['metadata']['total_variants']:,} variants, "
        f"{len(index['chromosomes'])} chromosomes"
    )

    return index


def save_xml_index(xml_path: Path, index: Dict) -> None:
    """
    Save XML index to cache.

    Args:
        xml_path: Path to XML file
        index: Index dict to save
    """
    index_path = _get_index_path(xml_path)
    index_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Saving index to: {index_path}")

    # Convert tuples to lists for JSON serialization
    index_copy = index.copy()
    if "chromosomes" in index_copy:
        index_copy["chromosomes"] = {
            chrom: [list(item) for item in offsets]
            for chrom, offsets in index_copy["chromosomes"].items()
        }

    with gzip.open(index_path, "wt") as f:
        json.dump(index_copy, f, indent=2)

    size_mb = index_path.stat().st_size / 1024 / 1024
    logger.info(f"Index saved: {size_mb:.1f} MB")


def _get_index_path(xml_path: Path) -> Path:
    """
    Get path for cached index file.

    Args:
        xml_path: Path to XML file

    Returns:
        Path to index file (.xml.index.json.gz)
    """
    # Store in same directory as XML
    return xml_path.parent / f"{xml_path.name}.index.json.gz"


def _extract_chromosome_for_index(elem: etree.Element) -> Optional[str]:
    """
    Extract chromosome from VariationArchive element (fast version for indexing).

    Args:
        elem: VariationArchive element

    Returns:
        Chromosome name (1-22, X, Y, MT) or None
    """
    # Find CanonicalSPDI
    spdi_elem = elem.find(".//cv:CanonicalSPDI", NS)
    if spdi_elem is None or not spdi_elem.text:
        return None

    spdi = spdi_elem.text.strip()

    # Parse SPDI: NC_000001.11:12345:A:G
    try:
        parts = spdi.split(":")
        if len(parts) < 4:
            return None

        refseq = parts[0]  # NC_000001.11

        # Quick chromosome extraction
        chromosome = _refseq_to_chromosome(refseq)
        return chromosome

    except (ValueError, IndexError):
        return None


def _refseq_to_chromosome(refseq: str) -> Optional[str]:
    """
    Convert RefSeq to chromosome (fast version for indexing).

    Args:
        refseq: RefSeq accession (e.g., NC_000001.11)

    Returns:
        Chromosome name or None
    """
    if not refseq.startswith("NC_"):
        return None

    try:
        chr_code = refseq.split(".")[0].replace("NC_", "")
    except IndexError:
        return None

    chr_map = {
        "000001": "1",
        "000002": "2",
        "000003": "3",
        "000004": "4",
        "000005": "5",
        "000006": "6",
        "000007": "7",
        "000008": "8",
        "000009": "9",
        "000010": "10",
        "000011": "11",
        "000012": "12",
        "000013": "13",
        "000014": "14",
        "000015": "15",
        "000016": "16",
        "000017": "17",
        "000018": "18",
        "000019": "19",
        "000020": "20",
        "000021": "21",
        "000022": "22",
        "000023": "X",
        "000024": "Y",
        "012920": "MT",
    }

    return chr_map.get(chr_code)


def get_chromosome_offsets(
    index: Dict,
    chromosomes: Set[str],
) -> List[Tuple[int, str]]:
    """
    Get byte offsets for specific chromosomes.

    Args:
        index: Index dict from build_xml_index()
        chromosomes: Set of chromosome names to extract

    Returns:
        List of (byte_offset, variant_id) tuples
    """
    offsets = []

    for chrom in chromosomes:
        if chrom in index.get("chromosomes", {}):
            offsets.extend(index["chromosomes"][chrom])

    # Sort by byte offset for sequential reading
    offsets.sort(key=lambda x: x[0])

    return offsets


def decompress_xml_if_needed(xml_gz_path: Path) -> Path:
    """
    Decompress .xml.gz to .xml if needed for indexed mode.

    Args:
        xml_gz_path: Path to .xml.gz file

    Returns:
        Path to decompressed .xml file

    Note:
        This is a helper for users who only have .xml.gz files.
        Indexed mode requires uncompressed XML for seeking.
    """
    if not str(xml_gz_path).endswith(".gz"):
        # Already uncompressed
        return xml_gz_path

    xml_path = Path(str(xml_gz_path).replace(".gz", ""))

    if xml_path.exists():
        logger.info(f"Using existing decompressed file: {xml_path.name}")
        return xml_path

    logger.info(
        f"Decompressing {xml_gz_path.name} to {xml_path.name} "
        "(this will take 10-15 minutes, one-time operation)..."
    )

    file_size = xml_gz_path.stat().st_size

    with gzip.open(xml_gz_path, "rb") as f_in:
        with open(xml_path, "wb") as f_out:
            with tqdm(
                total=file_size,
                desc="Decompressing",
                unit="B",
                unit_scale=True,
            ) as pbar:
                while True:
                    chunk = f_in.read(1024 * 1024)  # 1MB chunks
                    if not chunk:
                        break
                    f_out.write(chunk)
                    pbar.update(len(chunk))

    logger.info(f"Decompression complete: {xml_path}")
    return xml_path


__all__ = [
    "build_xml_index",
    "load_xml_index",
    "save_xml_index",
    "get_chromosome_offsets",
    "decompress_xml_if_needed",
]
