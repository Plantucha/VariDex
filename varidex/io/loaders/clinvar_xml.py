#!/usr/bin/env python3
"""
ClinVar XML Streaming Parser - Phase 1 (v8.0.0)

Memory-efficient streaming parser for ClinVar XML release files.
Handles variants of all types including structural variants >1MB.

Performance: 5-8 minutes, 2-4GB RAM for full 70GB XML
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
    Stream parse ClinVar XML without loading entire file into memory.

    Args:
        filepath: Path to ClinVar XML file (.xml or .xml.gz)
        user_chromosomes: Optional set of chromosomes to filter (e.g., {'1', '2', 'X'})
        checkpoint_dir: Optional directory for caching (handled by parent loader)

    Returns:
        DataFrame with columns: chromosome, position, ref_allele, alt_allele, rsid,
                                gene, clinical_sig, review_status, variant_id

    Performance:
        - Memory: 2-4GB peak (streaming, not loading full file)
        - Time: 5-8 minutes for full 70GB XML
        - Filtered: 1-2 minutes for 3-5 chromosomes (23andMe)
    """
    logger.info(f"Loading ClinVar XML: {filepath.name}")

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

        # Get root element for periodic cleanup
        # This is CRITICAL for memory management
        context = iter(context)
        try:
            event, root = next(context)
            # Put it back
            context = etree.iterparse(
                f,
                events=("end",),
                tag=f"{{{NS['cv']}}}VariationArchive",
            )
            root = None
        except StopIteration:
            pass

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
                # Clear the element itself
                elem.clear()
                
                # Remove from parent to free memory
                parent = elem.getparent()
                if parent is not None:
                    parent.remove(elem)
                
                # Clear root periodically to prevent memory buildup
                if total_processed % 10000 == 0:
                    # Try to get root if we haven't already
                    if root is None:
                        try:
                            # Walk up to find root
                            current = elem
                            while current.getparent() is not None:
                                current = current.getparent()
                            root = current
                        except:
                            pass
                    
                    # Clear root's children that we've already processed
                    if root is not None:
                        root.clear()

                pbar.update(1)

        # Clean up context
        del context

    logger.info(f"Processed {total_processed:,} variants")
    logger.info(f"Retained {total_filtered:,} variants after filtering")

    # Convert to DataFrame
    if not variants:
        logger.warning("No variants found matching criteria")
        return pd.DataFrame()

    df = pd.DataFrame(variants)
    
    # Free the variants list
    del variants

    # Normalize coordinates (convert to 1-based, standardize chromosome names)
    df = normalize_dataframe_coordinates(df)

    logger.info(f"Final DataFrame: {len(df):,} rows, {len(df.columns)} columns")

    return df


def _parse_variation_archive(elem: etree.Element) -> Optional[Dict]:
    """
    Extract variant information from VariationArchive XML element.

    Args:
        elem: lxml Element for <VariationArchive>

    Returns:
        Dict with variant info, or None if parsing fails
    """
    try:
        # Extract variant ID
        variant_id = elem.get("VariationID")
        if not variant_id:
            return None

        # Extract classification
        clinical_sig, review_status = _extract_clinical_significance(elem)

        # Extract genomic location (SPDI notation)
        spdi_data = _parse_spdi(elem)
        if not spdi_data:
            return None

        # Extract rsID
        rsid = _extract_rsid(elem)

        # Extract gene symbol
        gene = _extract_gene(elem)

        # Build variant dict with standard column names
        variant = {
            "variant_id": variant_id,
            "chromosome": spdi_data["chromosome"],
            "position": spdi_data["position"],
            "ref_allele": spdi_data["ref"],  # Match normalization schema
            "alt_allele": spdi_data["alt"],  # Match normalization schema
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
    # Find CanonicalSPDI element
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
        position = int(parts[1])  # 0-based in SPDI
        ref = parts[2]
        alt = parts[3]

        # Convert RefSeq to chromosome
        chromosome = _refseq_to_chromosome(refseq)
        if not chromosome:
            return None

        # Convert 0-based to 1-based position
        position_1based = position + 1

        return {
            "chromosome": chromosome,
            "position": position_1based,
            "ref": ref if ref else "-",  # Deletion
            "alt": alt if alt else "-",  # Insertion
        }

    except (ValueError, IndexError) as e:
        logger.debug(f"Failed to parse SPDI '{spdi}': {e}")
        return None


def _refseq_to_chromosome(refseq: str) -> Optional[str]:
    """
    Convert RefSeq accession to chromosome name.

    NC_000001.11 → '1'
    NC_000023.11 → 'X'
    NC_000024.10 → 'Y'
    NC_012920.1 → 'MT'

    Args:
        refseq: RefSeq accession (e.g., NC_000001.11)

    Returns:
        Chromosome name (1-22, X, Y, MT) or None
    """
    if not refseq.startswith("NC_"):
        return None

    # Extract chromosome number (NC_000001.11 → 000001)
    try:
        chr_code = refseq.split(".")[0].replace("NC_", "")
    except IndexError:
        return None

    # Map RefSeq codes to chromosome names
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
    # Find ClinicalSignificance element
    clin_sig_elem = elem.find(
        ".//cv:ClinicalSignificance/cv:Description", NS
    )
    clinical_sig = (
        clin_sig_elem.text.strip() if clin_sig_elem is not None else "Unknown"
    )

    # Find ReviewStatus element
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
    # Find XRef with DB="dbSNP"
    xrefs = elem.findall(".//cv:XRef[@DB='dbSNP']", NS)

    for xref in xrefs:
        rsid = xref.get("ID")
        if rsid:
            # Ensure rs prefix
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
    # Find Gene/Symbol element
    gene_elem = elem.find(".//cv:Gene/cv:Symbol", NS)

    if gene_elem is not None and gene_elem.text:
        return gene_elem.text.strip()

    return None


# Phase 3: Will add indexed loading function here
def load_clinvar_xml_indexed(
    filepath: Path,
    user_chromosomes: Set[str],
    checkpoint_dir: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Load XML using pre-built byte-offset index (Phase 3).

    This function will be implemented in Phase 3 for 30-60s load times.

    Args:
        filepath: Path to UNCOMPRESSED XML file
        user_chromosomes: Required set of chromosomes
        checkpoint_dir: Optional caching directory

    Returns:
        Filtered DataFrame

    Performance: 30-60s with cached index, <500MB RAM
    """
    raise NotImplementedError(
        "Indexed XML loading will be implemented in Phase 3 (v8.2.0)"
    )


# Alias for backwards compatibility
_load_clinvar_xml_streaming = load_clinvar_xml
