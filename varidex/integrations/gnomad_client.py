"""gnomAD API client for allele frequency data.

This module provides a client for querying the gnomAD (Genome Aggregation Database)
API to retrieve allele frequency data for variants. Supports gnomAD v3 and v4.

Reference:
    Karczewski KJ, et al. The mutational constraint spectrum quantified from
    variation in 141,456 humans. Nature. 2020;581(7809):434-443.
    PMID: 32461654
"""

import logging
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import requests
from functools import lru_cache

logger = logging.getLogger(__name__)


@dataclass
class GnomadVariantFrequency:
    """Container for gnomAD variant frequency data."""

    variant_id: str
    genome_af: Optional[float] = None  # Genome allele frequency
    genome_ac: Optional[int] = None  # Genome allele count
    genome_an: Optional[int] = None  # Genome allele number
    exome_af: Optional[float] = None  # Exome allele frequency
    exome_ac: Optional[int] = None  # Exome allele count
    exome_an: Optional[int] = None  # Exome allele number
    popmax_af: Optional[float] = None  # Maximum population frequency
    popmax_population: Optional[str] = None  # Population with max frequency
    populations: Optional[Dict[str, float]] = None  # Per-population frequencies
    filter_status: Optional[str] = None  # Filter status (PASS, etc.)

    @property
    def max_af(self) -> Optional[float]:
        """Return maximum allele frequency across all datasets."""
        afs = [af for af in [self.genome_af, self.exome_af, self.popmax_af] if af is not None]
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

    def __init__(self, max_requests: int = 100, time_window: int = 60):
        """Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed in time window
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: List[float] = []

    def wait_if_needed(self) -> None:
        """Wait if rate limit would be exceeded."""
        now = time.time()
        # Remove old requests outside time window
        self.requests = [t for t in self.requests if now - t < self.time_window]

        if len(self.requests) >= self.max_requests:
            # Calculate wait time
            oldest = self.requests[0]
            wait_time = self.time_window - (now - oldest)
            if wait_time > 0:
                logger.debug(f"Rate limit reached, waiting {wait_time:.1f}s")
                time.sleep(wait_time)
                # Clear after wait
                self.requests = []

        self.requests.append(now)


class GnomadClient:
    """Client for gnomAD GraphQL API."""

    DEFAULT_API_URL = "https://gnomad.broadinstitute.org/api"
    DEFAULT_TIMEOUT = 30  # seconds
    DEFAULT_RETRY_ATTEMPTS = 3
    CACHE_SIZE = 1000  # LRU cache size

    def __init__(
        self,
        api_url: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
        retry_attempts: int = DEFAULT_RETRY_ATTEMPTS,
        enable_cache: bool = True,
        rate_limit: bool = True,
    ):
        """Initialize gnomAD client.

        Args:
            api_url: gnomAD API endpoint URL
            timeout: Request timeout in seconds
            retry_attempts: Number of retry attempts on failure
            enable_cache: Enable response caching
            rate_limit: Enable rate limiting (100 req/min)
        """
        self.api_url = api_url or self.DEFAULT_API_URL
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.enable_cache = enable_cache
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "User-Agent": "VariDex/6.0 (genomic variant analysis)",
            }
        )
        self.rate_limiter = RateLimiter() if rate_limit else None
        self._cache: Dict[str, tuple[GnomadVariantFrequency, datetime]] = {}
        self._cache_duration = timedelta(hours=24)  # Cache for 24 hours

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
            else:
                # Expired, remove from cache
                del self._cache[variant_id]

        return None

    def _add_to_cache(self, variant_id: str, result: GnomadVariantFrequency) -> None:
        """Add variant result to cache."""
        if self.enable_cache:
            self._cache[variant_id] = (result, datetime.now())
            # Simple cache size management
            if len(self._cache) > self.CACHE_SIZE:
                # Remove oldest 10% of entries
                sorted_items = sorted(self._cache.items(), key=lambda x: x[1][1])
                for key, _ in sorted_items[: self.CACHE_SIZE // 10]:
                    del self._cache[key]

    def _build_graphql_query(self, variant_id: str, dataset: str = "gnomad_r4") -> str:
        """Build GraphQL query for variant lookup.

        Args:
            variant_id: Variant ID in format "chr-pos-ref-alt" (e.g., "1-55516888-G-A")
            dataset: Dataset version (gnomad_r3, gnomad_r4)

        Returns:
            GraphQL query string
        """
        query = f"""
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
        return query

    def _execute_query(self, query: str) -> Dict[str, Any]:
        """Execute GraphQL query with retries.

        Args:
            query: GraphQL query string

        Returns:
            Response data dictionary

        Raises:
            requests.RequestException: If request fails after all retries
        """
        if self.rate_limiter:
            self.rate_limiter.wait_if_needed()

        last_error = None
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
                    wait_time = 2**attempt  # Exponential backoff
                    logger.debug(f"Retry {attempt + 1}/{self.retry_attempts} after {wait_time}s")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed after {self.retry_attempts} attempts: {e}")

        raise last_error

    def _parse_response(
        self, data: Dict[str, Any], variant_id: str
    ) -> Optional[GnomadVariantFrequency]:
        """Parse gnomAD API response into GnomadVariantFrequency object.

        Args:
            data: Response data from API
            variant_id: Variant ID for lookup

        Returns:
            GnomadVariantFrequency object or None if variant not found
        """
        try:
            variant_data = data.get("data", {}).get("variant")
            if not variant_data:
                logger.debug(f"Variant not found in gnomAD: {variant_id}")
                return None

            genome = variant_data.get("genome", {})
            exome = variant_data.get("exome", {})

            # Extract population data
            populations = {}
            popmax_af = None
            popmax_pop = None

            # Check genome populations
            if genome and "populations" in genome:
                for pop in genome["populations"]:
                    pop_id = pop.get("id")
                    pop_af = pop.get("af")
                    if pop_id and pop_af is not None:
                        populations[f"genome_{pop_id}"] = pop_af
                        if popmax_af is None or pop_af > popmax_af:
                            popmax_af = pop_af
                            popmax_pop = pop_id

            # Check exome populations
            if exome and "populations" in exome:
                for pop in exome["populations"]:
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
                filter_status=genome.get("filters", [""])[0] if genome.get("filters") else None,
            )

        except (KeyError, TypeError, IndexError) as e:
            logger.error(f"Failed to parse gnomAD response: {e}")
            return None

    def get_variant_frequency(
        self, chromosome: str, position: int, ref: str, alt: str, dataset: str = "gnomad_r4"
    ) -> Optional[GnomadVariantFrequency]:
        """Get allele frequency data for a variant.

        Args:
            chromosome: Chromosome (1-22, X, Y)
            position: Genomic position (1-based)
            ref: Reference allele
            alt: Alternate allele
            dataset: gnomAD dataset version (gnomad_r3, gnomad_r4)

        Returns:
            GnomadVariantFrequency object or None if not found or on error
        """
        # Normalize chromosome
        chrom = chromosome.replace("chr", "")

        # Build variant ID
        variant_id = f"{chrom}-{position}-{ref}-{alt}"

        # Check cache first
        cached = self._get_from_cache(variant_id)
        if cached is not None:
            return cached

        try:
            # Build and execute query
            query = self._build_graphql_query(variant_id, dataset)
            response_data = self._execute_query(query)

            # Parse response
            result = self._parse_response(response_data, variant_id)

            if result:
                self._add_to_cache(variant_id, result)
                logger.info(f"Retrieved frequency for {variant_id}: AF={result.max_af}")

            return result

        except Exception as e:
            logger.error(f"Failed to get frequency for {variant_id}: {e}")
            return None

    def clear_cache(self) -> None:
        """Clear the response cache."""
        self._cache.clear()
        logger.info("Cache cleared")

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with cache size and other stats
        """
        return {
            "size": len(self._cache),
            "max_size": self.CACHE_SIZE,
        }
