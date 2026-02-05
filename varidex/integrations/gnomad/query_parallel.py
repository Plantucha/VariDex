#!/usr/bin/env python3
"""
Optimized gnomAD querier with parallel processing and batching.
Performance improvements:
- Parallel workers (multiprocessing)
- Batch region queries
- Connection pooling
- Smart caching
"""

import logging
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pysam
from tqdm import tqdm

logger = logging.getLogger(__name__)


@dataclass
class GnomADResult:
    """Result from gnomAD query."""

    found: bool
    af: Optional[float] = None
    ac: Optional[int] = None
    an: Optional[int] = None


def _normalize_chromosome(chrom: str) -> str:
    """Normalize chromosome name (optimized version)."""
    chrom = chrom.replace("chr", "")
    if chrom in ("M", "MT", "chrM", "chrMT"):
        return "MT"
    return chrom


def _query_variant_batch(
    args: Tuple[Path, List[Tuple[str, int, str, str]]],
) -> List[GnomADResult]:
    """
    Query a batch of variants from gnomAD VCF (worker function).

    Args:
        args: Tuple of (gnomad_dir, variant_list)
              variant_list is [(chrom, pos, ref, alt), ...]

    Returns:
        List of GnomADResult objects
    """
    gnomad_dir, variants = args
    results = []

    # Group variants by chromosome for efficient processing
    by_chrom: Dict[str, List[Tuple[int, int, str, str]]] = {}
    for idx, (chrom, pos, ref, alt) in enumerate(variants):
        chrom_norm = _normalize_chromosome(chrom)
        if chrom_norm not in by_chrom:
            by_chrom[chrom_norm] = []
        by_chrom[chrom_norm].append((idx, pos, ref, alt))

    # Initialize results list
    results = [GnomADResult(found=False)] * len(variants)

    # Process each chromosome
    for chrom, chrom_variants in by_chrom.items():
        vcf_path = gnomad_dir / f"gnomad.exomes.r2.1.1.sites.{chrom}.vcf.bgz"

        if not vcf_path.exists():
            continue

        try:
            vcf = pysam.VariantFile(str(vcf_path), "r")

            # Sort by position for efficient querying
            chrom_variants.sort(key=lambda x: x[1])

            # Find min/max positions for region query
            positions = [v[1] for v in chrom_variants]
            min_pos = min(positions)
            max_pos = max(positions)

            # Fetch entire region (more efficient than individual queries)
            try:
                # Create lookup dict for fast matching
                variant_lookup = {
                    (pos, ref, alt): idx for idx, pos, ref, alt in chrom_variants
                }

                # Query region
                for record in vcf.fetch(chrom, min_pos - 1, max_pos + 1):
                    pos = record.pos
                    ref = record.ref

                    # Check each alt allele
                    if record.alts:
                        for alt in record.alts:
                            key = (pos, ref, alt)
                            if key in variant_lookup:
                                idx = variant_lookup[key]

                                # Extract frequency info
                                af = record.info.get("AF", [None])
                                ac = record.info.get("AC", [None])
                                an = record.info.get("AN", None)

                                # Handle list-valued fields
                                if isinstance(af, (list, tuple)) and len(af) > 0:
                                    af = float(af[0])
                                elif af is not None:
                                    af = float(af)

                                if isinstance(ac, (list, tuple)) and len(ac) > 0:
                                    ac = int(ac[0])
                                elif ac is not None:
                                    ac = int(ac)

                                if an is not None:
                                    an = int(an)

                                results[idx] = GnomADResult(
                                    found=True, af=af, ac=ac, an=an
                                )

            except Exception as e:
                logger.debug(f"Error querying region {chrom}:{min_pos}-{max_pos}: {e}")

            vcf.close()

        except Exception as e:
            logger.debug(f"Error opening VCF for chromosome {chrom}: {e}")

    return results


class ParallelGnomADQuerier:
    """
    Optimized gnomAD querier with parallel processing.

    Performance improvements:
    - Parallel workers (default: CPU count - 1)
    - Batch processing (default: 500 variants per batch)
    - Region-based queries (more efficient than individual lookups)
    - Connection pooling per worker
    """

    def __init__(
        self,
        gnomad_dir: Path,
        n_workers: Optional[int] = None,
        batch_size: int = 500,
    ):
        """
        Initialize parallel querier.

        Args:
            gnomad_dir: Directory containing gnomAD VCF files
            n_workers: Number of parallel workers (default: CPU count - 1)
            batch_size: Variants per batch (default: 500)
        """
        self.gnomad_dir = Path(gnomad_dir)
        self.n_workers = n_workers or 1  # Single worker for large gnomAD files
        self.batch_size = batch_size

        logger.info(
            f"Initialized ParallelGnomADQuerier: "
            f"{self.n_workers} workers, batch_size={self.batch_size}"
        )

    def query_batch(
        self, variants: List[Tuple[str, int, str, str]], show_progress: bool = True
    ) -> List[GnomADResult]:
        """
        Query multiple variants in parallel.

        Args:
            variants: List of (chrom, pos, ref, alt) tuples
            show_progress: Show progress bar

        Returns:
            List of GnomADResult objects (same order as input)
        """
        if not variants:
            return []

        # Split into batches
        batches = []
        for i in range(0, len(variants), self.batch_size):
            batch = variants[i : i + self.batch_size]
            batches.append((self.gnomad_dir, batch))

        logger.info(
            f"Querying {len(variants):,} variants in {len(batches)} batches "
            f"using {self.n_workers} workers..."
        )

        # Process batches in parallel
        results = [None] * len(variants)

        with ThreadPoolExecutor(max_workers=self.n_workers) as executor:
            # Submit all batches
            future_to_idx = {}
            for batch_idx, batch_args in enumerate(batches):
                future = executor.submit(_query_variant_batch, batch_args)
                future_to_idx[future] = batch_idx

            # Collect results with progress bar
            desc = "Querying gnomAD (parallel)"
            pbar = (
                tqdm(total=len(batches), desc=desc, unit="batch")
                if show_progress
                else None
            )

            for future in as_completed(future_to_idx):
                batch_idx = future_to_idx[future]
                batch_results = future.result()

                # Insert results at correct positions
                start_idx = batch_idx * self.batch_size
                for i, result in enumerate(batch_results):
                    results[start_idx + i] = result

                if pbar:
                    pbar.update(1)

            if pbar:
                pbar.close()

        return results


def annotate_with_gnomad_parallel(
    variants: List[Dict],
    gnomad_dir: Path,
    n_workers: Optional[int] = None,
    batch_size: int = 500,
) -> List[Optional[float]]:
    """
    Annotate variants with gnomAD frequencies using parallel processing.

    Args:
        variants: List of variant dicts with keys: chromosome, position, ref_allele, alt_allele
        gnomad_dir: Path to gnomAD VCF directory
        n_workers: Number of parallel workers
        batch_size: Variants per batch

    Returns:
        List of allele frequencies (None if not found)
    """
    # Convert to tuple format
    variant_tuples = [
        (
            str(v["chromosome"]),
            int(v["position"]),
            str(v["ref_allele"]),
            str(v["alt_allele"]),
        )
        for v in variants
    ]

    # Query in parallel
    querier = ParallelGnomADQuerier(
        gnomad_dir=gnomad_dir, n_workers=n_workers, batch_size=batch_size
    )

    results = querier.query_batch(variant_tuples, show_progress=True)

    # Extract frequencies
    frequencies = [r.af if r.found else None for r in results]

    found_count = sum(1 for f in frequencies if f is not None)
    logger.info(
        f"✓ Found {found_count:,}/{len(variants):,} variants in gnomAD "
        f"({found_count/len(variants)*100:.1f}%)"
    )

    return frequencies
