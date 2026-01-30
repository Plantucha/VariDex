#!/usr/bin/env python3
"""
ClinVar XML Parser - Phase 3 Complete (v8.2.0)

Memory-efficient streaming parser with optional indexed mode.

Performance:
- Streaming: 5-8 minutes, 2-4GB RAM (Phase 1)
- Indexed: 30-60 seconds, <500MB RAM (Phase 3)
"""

import gzip
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd
from lxml import etree
from tqdm import tqdm

from varidex.io.normalization import normalize_dataframe_coordinates

logger = logging.getLogger(__name__)

# ClinVar XML namespace
NS = {"cv": "http://www.ncbi.nlm.nih.gov/clinvar/release"}


def load_clinvar_xml(
    filepath: Path,
    user_chromosomes: Optional[Set[str]] = None,
    checkpoint_dir: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Load ClinVar XML with smart mode selection.

    Automatically chooses best loading strategy:
    - Indexed mode: If uncompressed XML + chromosomes specified (30-60s, <500MB)
    - Streaming mode: Otherwise (5-8min, 2-4GB)

    Args:
        filepath: Path to ClinVar XML file (.xml or .xml.gz)
        user_chromosomes: Optional set of chromosomes to filter
        checkpoint_dir: Optional directory for caching

    Returns:
        DataFrame with variant data
    """
    # Check if indexed mode is possible
    can_use_indexed = (
        not str(filepath).endswith(".gz")  # Must be uncompressed
        and user_chromosomes is not None  # Must have chromosome filter
        and len(user_chromosomes) > 0
    )

    if can_use_indexed:
        logger.info("Using indexed mode (fast, low memory)")
        try:
            return load_clinvar_xml_indexed(
                filepath,
                user_chromosomes,
                checkpoint_dir,
            )
        except Exception as e:
            logger.warning(
                f"Indexed mode failed ({e}), falling back to streaming"
            )

    # Fall back to streaming mode
    logger.info("Using streaming mode")
    return _load_clinvar_xml_streaming(
        filepath,
        user_chromosomes,
        checkpoint_dir,
    )


def _load_clinvar_xml_streaming(
    filepath: Path,
    user_chromosomes: Optional[Set[str]] = None,
    checkpoint_dir: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Stream parse ClinVar XML without loading entire file into memory.

    Args:
        filepath: Path to ClinVar XML file (.xml or .xml.gz)
        user_chromosomes: Optional set of chromosomes to filter
        checkpoint_dir: Optional directory for caching

    Returns:
        DataFrame with variant data

    Performance: 5-8 minutes, 2-4GB RAM
    """
    logger.info(f"Loading ClinVar XML (streaming): {filepath.name}")

    if user_chromosomes:
        logger.info(
            f"Filtering to {len(user_chromosomes)} chromosomes: "
            f"{sorted(user_chromosomes)}"
        )

    # Open file (gzipped or plain)
    if str(filepath).endswith(".gz"):
        opener = gzip.open(filepath, "rb")
    else:
        opener = open(filepath, "rb")

    variants = []
    total_processed = 0
    total_filtered = 0

    with opener as f:
        # Set up streaming parser
        context = etree.iterparse(
            f,
            events=("end",),
            tag=f"{{{NS['cv']}}}VariationArchive",
        )

        root = None

        # Progress bar (estimated 4.3M variants)
        with tqdm(
            total=4_300_000,
            desc="Parsing XML",
            unit="var",
            unit_scale=True,
        ) as pbar:
            for event, elem in context:
                total_processed += 1

                # Parse variant from XML element
                variant = _parse_variation_archive(elem)

                # Filter by chromosome if specified
                if variant:
                    if not user_chromosomes or variant["chromosome"] in user_chromosomes:
                        variants.append(variant)
                        total_filtered += 1

                # CRITICAL: Aggressive memory cleanup
                elem.clear()
                parent = elem.getparent()
                if parent is not None:
                    parent.remove(elem)

                # Clear root periodically
                if total_processed % 10000 == 0:
                    if root is None:
                        try:
                            current = elem
                            while current.getparent() is not None:
                                current = current.getparent()
                            root = current
                        except:
                            pass
                    if root is not None:
                        root.clear()

                pbar.update(1)

        del context

    logger.info(f"Processed {total_processed:,} variants")
    logger.info(f"Retained {total_filtered:,} variants after filtering")

    if not variants:
        logger.warning("No variants found matching criteria")
        return pd.DataFrame()

    df = pd.DataFrame(variants)
    del variants

    df = normalize_dataframe_coordinates(df)

    logger.info(f"Final DataFrame: {len(df):,} rows, {len(df.columns)} columns")

    return df


def load_clinvar_xml_indexed(
    filepath: Path,
    user_chromosomes: Set[str],
    checkpoint_dir: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Load XML using pre-built byte-offset index (Phase 3).

    Args:
        filepath: Path to UNCOMPRESSED XML file
        user_chromosomes: Required set of chromosomes
        checkpoint_dir: Optional caching directory

    Returns:
        Filtered DataFrame

    Performance: 30-60s with cached index, <500MB RAM
    """
    from varidex.io.indexers.clinvar_xml_index import (
        build_xml_index,
        get_chromosome_offsets,
    )

    logger.info(f"Loading ClinVar XML (indexed): {filepath.name}")
    logger.info(
        f"Target chromosomes: {sorted(user_chromosomes)} "
        f"({len(user_chromosomes)} total)"
    )

    # Build or load index
    index = build_xml_index(filepath)

    # Get byte offsets for target chromosomes
    offsets = get_chromosome_offsets(index, user_chromosomes)

    if not offsets:
        logger.warning("No variants found for specified chromosomes")
        return pd.DataFrame()

    logger.info(f"Found {len(offsets):,} variants to load")

    # Load variants using byte offsets
    variants = []

    with open(filepath, "rb") as f:
        with tqdm(
            total=len(offsets),
            desc="Loading variants",
            unit="var",
            unit_scale=True,
        ) as pbar:
            for byte_offset, variant_id in offsets:
                # Seek to byte offset
                f.seek(byte_offset)

                # Read and parse element at this position
                # Note: We need to read backwards to find element start
                variant = _read_variant_at_offset(f, byte_offset)

                if variant:
                    variants.append(variant)

                pbar.update(1)

    logger.info(f"Loaded {len(variants):,} variants")

    if not variants:
        return pd.DataFrame()

    df = pd.DataFrame(variants)
    del variants

    df = normalize_dataframe_coordinates(df)

    logger.info(f"Final DataFrame: {len(df):,} rows, {len(df.columns)} columns")

    return df


def _read_variant_at_offset(f, byte_offset: int) -> Optional[Dict]:
    """
    Read and parse variant element at specific byte offset.

    Args:
        f: Open file handle
        byte_offset: Byte position in file

    Returns:
        Variant dict or None
    """
    # Seek backwards to find element start
    # Look for <VariationArchive
    chunk_size = 50000  # Read 50KB chunks
    search_start = max(0, byte_offset - chunk_size)

    f.seek(search_start)
    chunk = f.read(chunk_size + 10000)  # Read a bit extra

    # Find element start
    tag_start = chunk.rfind(b"<VariationArchive")
    if tag_start == -1:
        return None

    # Find element end (after our byte offset)
    tag_end = chunk.find(b"</VariationArchive>", tag_start)
    if tag_end == -1:
        return None

    # Extract element XML
    element_xml = chunk[tag_start : tag_end + len(b"</VariationArchive>")]

    # Parse element
    try:
        elem = etree.fromstring(element_xml)
        variant = _parse_variation_archive(elem)
        elem.clear()
        return variant
    except Exception as e:
        logger.debug(f"Failed to parse variant at offset {byte_offset}: {e}")
        return None


def _parse_variation_archive(elem: etree.Element) -> Optional[Dict]:
    """
    Extract variant information from VariationArchive XML element.

    Args:
        elem: lxml Element for <VariationArchive>

    Returns:
        Dict with variant info, or None if parsing fails
    """
    try:
        variant_id = elem.get("VariationID")
        if not variant_id:
            return None

        clinical_sig, review_status = _extract_clinical_significance(elem)
        spdi_data = _parse_spdi(elem)
        if not spdi_data:
            return None

        rsid = _extract_rsid(elem)
        gene = _extract_gene(elem)

        variant = {
            "variant_id": variant_id,
            "chromosome": spdi_data["chromosome"],
            "position": spdi_data["position"],
            "ref_allele": spdi_data["ref"],
            "alt_allele": spdi_data["alt"],
            "rsid": rsid,
            "gene": gene,
            "clinical_sig": clinical_sig,
            "review_status": review_status,
        }

        return variant

    except Exception as e:
        logger.debug(f"Failed to parse variant: {e}")
        return None


def _parse_spdi(elem: etree.Element) -> Optional[Dict]:
    """
    Parse SPDI notation and convert to standard chromosome coordinates.

    SPDI format: NC_000001.11:12345:A:G
    Converts to: chr=1, pos=12346 (1-based), ref=A, alt=G

    Args:
        elem: VariationArchive element

    Returns:
        Dict with chromosome, position, ref, alt or None
    """
    spdi_elem = elem.find(".//cv:CanonicalSPDI", NS)
    if spdi_elem is None or not spdi_elem.text:
        return None

    spdi = spdi_elem.text.strip()

    try:
        parts = spdi.split(":")
        if len(parts) < 4:
            return None

        refseq = parts[0]
        position = int(parts[1])
        ref = parts[2]
        alt = parts[3]

        chromosome = _refseq_to_chromosome(refseq)
        if not chromosome:
            return None

        position_1based = position + 1

        return {
            "chromosome": chromosome,
            "position": position_1based,
            "ref": ref if ref else "-",
            "alt": alt if alt else "-",
        }

    except (ValueError, IndexError) as e:
        logger.debug(f"Failed to parse SPDI '{spdi}': {e}")
        return None


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


def _extract_clinical_significance(elem: etree.Element) -> Tuple[str, str]:
    """
    Extract clinical significance and review status.

    Args:
        elem: VariationArchive element

    Returns:
        Tuple of (clinical_sig, review_status)
    """
    clin_sig_elem = elem.find(
        ".//cv:ClinicalSignificance/cv:Description", NS
    )
    clinical_sig = (
        clin_sig_elem.text.strip() if clin_sig_elem is not None else "Unknown"
    )

    review_elem = elem.find(
        ".//cv:ClinicalSignificance/cv:ReviewStatus", NS
    )
    review_status = (
        review_elem.text.strip() if review_elem is not None else "Unknown"
    )

    return clinical_sig, review_status


def _extract_rsid(elem: etree.Element) -> Optional[str]:
    """
    Extract dbSNP rsID.

    Args:
        elem: VariationArchive element

    Returns:
        rsID string (e.g., 'rs123456') or None
    """
    xrefs = elem.findall(".//cv:XRef[@DB='dbSNP']", NS)

    for xref in xrefs:
        rsid = xref.get("ID")
        if rsid:
            if not rsid.startswith("rs"):
                rsid = f"rs{rsid}"
            return rsid

    return None


def _extract_gene(elem: etree.Element) -> Optional[str]:
    """
    Extract gene symbol.

    Args:
        elem: VariationArchive element

    Returns:
        Gene symbol string or None
    """
    gene_elem = elem.find(".//cv:Gene/cv:Symbol", NS)

    if gene_elem is not None and gene_elem.text:
        return gene_elem.text.strip()

    return None
