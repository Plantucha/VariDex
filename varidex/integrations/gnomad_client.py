"""gnomAD API client for allele frequency data.

This module provides a client for querying the gnomAD (Genome Aggregation Database)
API to retrieve allele frequency data for variants. Supports gnomAD v3 and v4.

Reference:
    Karczewski KJ, et al. The mutational constraint spectrum quantified from
    variation in 141,456 humans. Nature. 2020;581(7809):434-443.
    PMID: 32461654

Version: 6.5.0-dev
Fixes: Chromosome normalization, error handling
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


def normalize_chromosome(chrom: str) -> str:
    """
    Normalize chromosome name for gnomAD API.

    Converts:
    - 'chr1' → '1'
    - 'chrX' → 'X'
    - 'M' → 'MT'
    - 'chrM' → 'MT'

    Args:
        chrom: Chromosome name

    Returns:
        Normalized chromosome name
    """
    normalized = chrom.replace("chr", "").upper()
    # Convert M to MT (mitochondrial)
    if normalized == "M":
        normalized = "MT"
    return normalized


@dataclass
class GnomadVariantFrequency:
    """Container for gnomAD variant frequency data."""

    variant_id: str
    genome_af: Optional[float] = None
    genome_ac: Optional[int] = None
    genome_an: Optional[int] = None
    exome_af: Optional[float] = None
    exome_ac: Optional[int] = None
    exome_an: Optional[int] = None
    popmax_af: Optional[float] = None
    popmax_population: Optional[str] = None
    populations: Optional[Dict[str, float]] = None
    filter_status: Optional[str] = None

    @property
    def max_af(self) -> Optional[float]:
        """Get maximum allele frequency across all datasets."""
        afs = [
            af
            for af in [self.genome_af, self.exome_af, self.popmax_af]
            if af is not None
        ]
        return max(afs) if afs else None

    @property
    def is_common(self) -> bool:
        """Check if variant is common (AF > 1%)."""
        max_af = self.max_af
        return max_af is not None and max_af > 0.01

    @property
    def is_rare(self) -> bool:
        """Check if variant is rare (AF < 0.01%)."""
        max_af = self.max_af
        return max_af is None or max_af < 0.0001


class RateLimiter:
    """Simple rate limiter for API requests."""

    def __init__(self, max_requests: int = 100, time_window: int = 60) -> None:
        self.max_requests: int = max_requests
        self.time_window: int = time_window
        self.requests: List[float] = []

    def wait_if_needed(self) -> None:
        """Wait if rate limit would be exceeded."""
        now = time.time()
        self.requests = [t for t in self.requests if now - t < self.time_window]

        if len(self.requests) >= self.max_requests:
            oldest = self.requests[0]
            wait_time = self.time_window - (now - oldest)
            if wait_time > 0:
                logger.debug(f"Rate limit reached, waiting {wait_time:.1f}s")
                time.sleep(wait_time)
                self.requests = []

        self.requests.append(now)


class GnomadClient:
    """Client for gnomAD GraphQL API."""

    DEFAULT_API_URL: str = "https://gnomad.broadinstitute.org/api"
    DEFAULT_TIMEOUT: int = 30
    DEFAULT_RETRY_ATTEMPTS: int = 3
    CACHE_SIZE: int = 1000

    def __init__(
        self,
        api_url: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
        retry_attempts: int = DEFAULT_RETRY_ATTEMPTS,
        enable_cache: bool = True,
        rate_limit: bool = True,
    ) -> None:
        """Initialize gnomAD API client."""
        self.api_url: str = api_url or self.DEFAULT_API_URL
        self.timeout: int = timeout
        self.retry_attempts: int = retry_attempts
        self.enable_cache: bool = enable_cache
        self.session: requests.Session = requests.Session()
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "User-Agent": "VariDex/6.5 (genomic variant analysis)",
            }
        )
        self.rate_limiter: Optional[RateLimiter] = RateLimiter() if rate_limit else None
        self._cache: Dict[str, Tuple[GnomadVariantFrequency, datetime]] = {}
        self._cache_duration: timedelta = timedelta(hours=24)

        logger.info(f"Initialized gnomAD client: {self.api_url}")

    def _get_from_cache(self, variant_id: str) -> Optional[GnomadVariantFrequency]:
        """Retrieve variant from cache if available and not expired."""
        if not self.enable_cache:
            return None
        if variant_id in self._cache:
            result, timestamp = self._cache[variant_id]
            if datetime.now() - timestamp < self._cache_duration:
                logger.debug(f"Cache hit: {variant_id}")
                return result
            del self._cache[variant_id]
        return None

    def _add_to_cache(self, variant_id: str, result: GnomadVariantFrequency) -> None:
        """Add variant to cache, evicting old entries if needed."""
        if self.enable_cache:
            self._cache[variant_id] = (result, datetime.now())
            if len(self._cache) > self.CACHE_SIZE:
                # Evict oldest 10% of entries
                sorted_items = sorted(self._cache.items(), key=lambda x: x[1][1])
                for key, _ in sorted_items[: self.CACHE_SIZE // 10]:
                    del self._cache[key]

    def _build_graphql_query(self, variant_id: str, dataset: str = "gnomad_r4") -> str:
        """Build GraphQL query for variant frequency data."""
        query_template = """
        {{
          variant(dataset: "{dataset}", variantId: "{variant_id}") {{
            variantId
            genome {{
              ac
              an
              af
              filters
              populations {{
                id
                ac
                an
                af
              }}
            }}
            exome {{
              ac
              an
              af
              filters
              populations {{
                id
                ac
                an
                af
              }}
            }}
          }}
        }}
        """
        return query_template.format(dataset=dataset, variant_id=variant_id)

    def _execute_query(self, query: str) -> Dict[str, Any]:
        """Execute GraphQL query with retry logic."""
        if self.rate_limiter:
            self.rate_limiter.wait_if_needed()

        last_error: Optional[Exception] = None
        for attempt in range(self.retry_attempts):
            try:
                response = self.session.post(
                    self.api_url, json={"query": query}, timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()
                if "errors" in data:
                    error_msg = data["errors"][0].get("message", "Unknown error")
                    logger.warning(f"GraphQL error: {error_msg}")
                    raise ValueError(f"GraphQL error: {error_msg}")
                return data
            except (requests.RequestException, ValueError) as e:
                last_error = e
                if attempt < self.retry_attempts - 1:
                    wait_time = 2**attempt
                    logger.debug(
                        f"Retry {attempt + 1}/{self.retry_attempts} after {wait_time}s"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed after {self.retry_attempts} attempts: {e}")

        # Re-raise the last error if all retries failed
        if last_error:
            raise last_error

        # This should never be reached, but satisfies type checker
        raise RuntimeError("Query execution failed without exception")

    def _parse_response(
        self, data: Dict[str, Any], variant_id: str
    ) -> Optional[GnomadVariantFrequency]:
        """Parse GraphQL response into GnomadVariantFrequency object."""
        try:
            variant_data = data.get("data", {}).get("variant")
            if not variant_data:
                logger.debug(f"Variant not found in gnomAD: {variant_id}")
                return None

            genome = variant_data.get("genome", {})
            exome = variant_data.get("exome", {})

            populations: Dict[str, float] = {}
            popmax_af: Optional[float] = None
            popmax_pop: Optional[str] = None

            # Genome populations
            for pop in genome.get("populations", []):
                pop_id = pop.get("id")
                pop_af = pop.get("af")
                if pop_id and pop_af is not None:
                    populations[f"genome_{pop_id}"] = pop_af
                    if popmax_af is None or pop_af > popmax_af:
                        popmax_af = pop_af
                        popmax_pop = pop_id

            # Exome populations
            for pop in exome.get("populations", []):
                pop_id = pop.get("id")
                pop_af = pop.get("af")
                if pop_id and pop_af is not None:
                    populations[f"exome_{pop_id}"] = pop_af
                    if popmax_af is None or pop_af > popmax_af:
                        popmax_af = pop_af
                        popmax_pop = pop_id

            return GnomadVariantFrequency(
                variant_id=variant_id,
                genome_af=genome.get("af"),
                genome_ac=genome.get("ac"),
                genome_an=genome.get("an"),
                exome_af=exome.get("af"),
                exome_ac=exome.get("ac"),
                exome_an=exome.get("an"),
                popmax_af=popmax_af,
                popmax_population=popmax_pop,
                populations=populations if populations else None,
                filter_status=(genome.get("filters") or [None])[0],
            )
        except Exception as e:
            logger.error(f"Failed to parse gnomAD response: {e}")
            return None

    def get_variant_frequency(
        self,
        chromosome: str,
        position: int,
        ref: str,
        alt: str,
        dataset: str = "gnomad_r4",
    ) -> Optional[GnomadVariantFrequency]:
        """
        Query gnomAD for variant allele frequency.

        Args:
            chromosome: Chromosome name (1-22, X, Y, MT)
            position: Genomic position (1-based)
            ref: Reference allele
            alt: Alternate allele
            dataset: gnomAD dataset (gnomad_r4, gnomad_r3, etc.)

        Returns:
            GnomadVariantFrequency object or None if not found
        """
        # Normalize chromosome (handles chr prefix, M→MT)
        chromosome = normalize_chromosome(chromosome)
        variant_id = f"{chromosome}-{position}-{ref}-{alt}"

        # Check cache
        cached = self._get_from_cache(variant_id)
        if cached is not None:
            return cached

        # Query API
        try:
            query = self._build_graphql_query(variant_id, dataset)
            response_data = self._execute_query(query)
            result = self._parse_response(response_data, variant_id)
            if result:
                self._add_to_cache(variant_id, result)
                logger.info(f"Retrieved frequency for {variant_id}: AF={result.max_af}")
            return result
        except Exception as e:
            logger.error(f"Failed to get frequency for {variant_id}: {e}")
            return None

    def clear_cache(self) -> None:
        """Clear the variant frequency cache."""
        self._cache.clear()
        logger.info("Cache cleared")

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self.CACHE_SIZE,
        }
