#!/usr/bin/env python3
"""
ClinVar XML Byte-Offset Indexer - Phase 3 (v8.2.0)

Builds and uses byte-offset index for instant chromosome-specific XML loading.
First run: 20-30 min to build index (one-time)
Subsequent runs: 30-60s, <500MB RAM
"""

import logging
import pickle
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from tqdm import tqdm

logger = logging.getLogger(__name__)


def get_index_path(xml_path: Path) -> Path:
    """
    Get path to index file for given XML file.

    Args:
        xml_path: Path to ClinVar XML file

    Returns:
        Path to corresponding .index.pkl file
    """
    # Remove .gz if present, add .index.pkl
    if xml_path.name.endswith(".xml.gz"):
        base = xml_path.name[:-7]  # Remove .xml.gz
    elif xml_path.name.endswith(".xml"):
        base = xml_path.name[:-4]  # Remove .xml
    else:
        base = xml_path.name

    index_name = f"{base}.index.pkl"
    return xml_path.parent / index_name


def _extract_chromosome_from_line(line: str) -> Optional[str]:
    """
    Extract chromosome from SPDI in XML line.

    Args:
        line: XML line containing CanonicalSPDI

    Returns:
        Chromosome (1-22, X, Y, MT) or None

    Example:
        <CanonicalSPDI>NC_000001.11:12345:A:G</CanonicalSPDI> → '1'
    """
    # Look for CanonicalSPDI tag
    match = re.search(r"<CanonicalSPDI>([^<]+)</CanonicalSPDI>", line)
    if not match:
        return None

    spdi = match.group(1)

    # Parse RefSeq accession
    if ":" not in spdi:
        return None

    refseq = spdi.split(":")[0]

    # Map RefSeq to chromosome
    return _refseq_to_chromosome(refseq)


def _refseq_to_chromosome(refseq: str) -> Optional[str]:
    """
    Convert RefSeq accession to chromosome name.

    Args:
        refseq: RefSeq accession (e.g., NC_000001.11)

    Returns:
        Chromosome name (1-22, X, Y, MT) or None
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


def build_xml_index(
    xml_path: Path,
    force_rebuild: bool = False,
) -> Dict[str, List[int]]:
    """
    Build byte-offset index for ClinVar XML file.

    Scans XML file and records byte offset of each VariationArchive element,
    grouped by chromosome. Index is cached for instant reuse.

    Args:
        xml_path: Path to UNCOMPRESSED ClinVar XML file
        force_rebuild: Force rebuild even if cached index exists

    Returns:
        Dict mapping chromosome → list of byte offsets

    Performance:
        - First run: 20-30 minutes (one-time cost)
        - Creates ~50-100MB index file
        - Subsequent loads: <1 second from cache

    Note:
        Requires UNCOMPRESSED XML. If you have .xml.gz, decompress first:
        gunzip -k ClinVarVCVRelease.xml.gz
    """
    if xml_path.name.endswith(".gz"):
        raise ValueError(
            "Indexed mode requires UNCOMPRESSED XML. "
            f"Decompress first: gunzip -k {xml_path.name}"
        )

    # Check for cached index
    index_path = get_index_path(xml_path)

    if not force_rebuild and index_path.exists():
        logger.info(f"Loading cached index: {index_path.name}")
        return load_xml_index(index_path)

    logger.info(f"Building XML index for: {xml_path.name}")
    logger.info("This is a one-time operation (20-30 minutes)")

    # Index structure: chromosome → list of byte offsets
    index: Dict[str, List[int]] = {}

    # Track statistics
    total_variants = 0
    unknown_chr = 0

    # Get file size for progress bar
    file_size = xml_path.stat().st_size

    with open(xml_path, "rb") as f:
        # Progress bar based on file position
        with tqdm(
            total=file_size,
            desc="Building index",
            unit="B",
            unit_scale=True,
        ) as pbar:
            current_offset = 0
            in_variation_archive = False
            variant_start_offset = 0
            variant_chromosome = None

            for line in f:
                line_text = line.decode("utf-8", errors="ignore")

                # Start of VariationArchive
                if "<VariationArchive" in line_text:
                    in_variation_archive = True
                    variant_start_offset = current_offset
                    variant_chromosome = None

                # Extract chromosome from SPDI
                if in_variation_archive and "<CanonicalSPDI>" in line_text:
                    variant_chromosome = _extract_chromosome_from_line(line_text)

                # End of VariationArchive
                if "</VariationArchive>" in line_text and in_variation_archive:
                    total_variants += 1

                    # Add to index if we found a chromosome
                    if variant_chromosome:
                        if variant_chromosome not in index:
                            index[variant_chromosome] = []
                        index[variant_chromosome].append(variant_start_offset)
                    else:
                        unknown_chr += 1

                    in_variation_archive = False

                # Update progress
                line_len = len(line)
                current_offset += line_len
                pbar.update(line_len)

    logger.info(f"Index built: {total_variants:,} variants")
    logger.info(f"  - Indexed: {total_variants - unknown_chr:,}")
    logger.info(f"  - Unknown chr: {unknown_chr:,}")
    logger.info(f"  - Chromosomes: {sorted(index.keys())}")

    # Save index
    logger.info(f"Saving index to: {index_path.name}")
    with open(index_path, "wb") as f:
        pickle.dump(index, f, protocol=pickle.HIGHEST_PROTOCOL)

    logger.info(f"Index saved: {index_path.stat().st_size / 1024**2:.1f} MB")

    return index


def load_xml_index(index_path: Path) -> Dict[str, List[int]]:
    """
    Load cached XML index.

    Args:
        index_path: Path to .index.pkl file

    Returns:
        Dict mapping chromosome → list of byte offsets
    """
    with open(index_path, "rb") as f:
        index = pickle.load(f)

    logger.info(
        f"Loaded index: {sum(len(v) for v in index.values()):,} variants, "
        f"{len(index)} chromosomes"
    )

    return index


def extract_variants_at_offsets(
    xml_path: Path,
    offsets: List[int],
    max_variants: Optional[int] = None,
) -> List[str]:
    """
    Extract VariationArchive XML chunks at specified byte offsets.

    Args:
        xml_path: Path to XML file
        offsets: List of byte offsets to read from
        max_variants: Optional limit on number of variants to extract

    Returns:
        List of XML strings (one per VariationArchive)

    Performance:
        - Memory efficient: Reads only requested variants
        - Fast: Direct file seeking
        - Typical: 30-60s for 100K-500K variants
    """
    if max_variants:
        offsets = offsets[:max_variants]

    logger.info(f"Extracting {len(offsets):,} variants from XML")

    variants = []

    with open(xml_path, "rb") as f:
        with tqdm(
            total=len(offsets),
            desc="Reading variants",
            unit="var",
            unit_scale=True,
        ) as pbar:
            for offset in offsets:
                # Seek to variant position
                f.seek(offset)

                # Read until end of VariationArchive
                variant_xml = []
                for line in f:
                    line_text = line.decode("utf-8", errors="ignore")
                    variant_xml.append(line_text)

                    # Stop at closing tag
                    if "</VariationArchive>" in line_text:
                        break

                variants.append("".join(variant_xml))
                pbar.update(1)

    return variants


def get_offsets_for_chromosomes(
    index: Dict[str, List[int]],
    chromosomes: Set[str],
) -> List[int]:
    """
    Get all byte offsets for specified chromosomes.

    Args:
        index: Chromosome → offsets mapping
        chromosomes: Set of chromosomes to extract

    Returns:
        Combined list of all offsets for requested chromosomes
    """
    offsets = []

    for chrom in chromosomes:
        if chrom in index:
            offsets.extend(index[chrom])
        else:
            logger.warning(f"Chromosome '{chrom}' not found in index")

    logger.info(
        f"Found {len(offsets):,} variants for chromosomes: {sorted(chromosomes)}"
    )

    return offsets


def decompress_xml_for_indexing(xml_gz_path: Path) -> Path:
    """
    Decompress .xml.gz file for indexed loading.

    Args:
        xml_gz_path: Path to compressed XML file

    Returns:
        Path to decompressed XML file

    Note:
        This creates a large file (~70GB for full ClinVar).
        Ensure you have sufficient disk space.
    """
    if not xml_gz_path.name.endswith(".xml.gz"):
        raise ValueError(f"Expected .xml.gz file, got: {xml_gz_path.name}")

    # Output path (same location, remove .gz)
    xml_path = xml_gz_path.parent / xml_gz_path.name[:-3]

    if xml_path.exists():
        logger.info(f"Decompressed XML already exists: {xml_path.name}")
        return xml_path

    logger.info(f"Decompressing {xml_gz_path.name}...")
    logger.info("This will take 5-10 minutes and use ~70GB disk space")

    import gzip
    import shutil

    with gzip.open(xml_gz_path, "rb") as f_in:
        with open(xml_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out, length=1024 * 1024 * 16)  # 16MB buffer

    logger.info(f"Decompressed: {xml_path.stat().st_size / 1024**3:.1f} GB")

    return xml_path


__all__ = [
    "build_xml_index",
    "load_xml_index",
    "get_index_path",
    "extract_variants_at_offsets",
    "get_offsets_for_chromosomes",
    "decompress_xml_for_indexing",
]
