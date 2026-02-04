#!/usr/bin/env python3
"""varidex/integrations/dbnsfp_client.py - dbNSFP/VEP API Client

Client for accessing computational predictions via Ensembl VEP API.
Provides SIFT, PolyPhen-2, CADD, and other algorithm predictions.

Data Sources:
  - Ensembl VEP REST API (primary, requires internet)
  - dbNSFP database (future: file-based parser for offline use)

Algorithms Supported:
  - SIFT: Sorting Intolerant From Tolerant
  - PolyPhen-2: Polymorphism Phenotyping v2
  - CADD: Combined Annotation Dependent Depletion
  - REVEL: Rare Exome Variant Ensemble Learner
  - MetaSVM: Meta-predictor using SVM

Offline Mode:
  This client requires internet connectivity to access Ensembl VEP API.
  For offline use, set enable_predictions=False in ComputationalPredictionService
  or use the graceful degradation to engine_v7 (gnomAD only) or engine_v6 (base).
  Future enhancement: Add file-based dbNSFP parser for full offline support.

Reference:
  - https://rest.ensembl.org/
  - https://sites.google.com/site/jpopgen/dbNSFP
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests

logger: logging.Logger = logging.getLogger(__name__)


@dataclass
class PredictionScore:
    """Container for computational prediction scores.

    Counts algorithms that predict deleterious vs benign effect.
    Missing algorithm scores are handled gracefully (not counted).
    """

    # SIFT (0-1, lower = more deleterious)
    sift_score: Optional[float] = None
    sift_prediction: Optional[str] = None  # 'deleterious' or 'tolerated'

    # PolyPhen-2 (0-1, higher = more deleterious)
    polyphen_score: Optional[float] = None
    polyphen_prediction: Optional[str] = None

    # CADD (1-99, higher = more deleterious)
    cadd_phred: Optional[float] = None
    cadd_raw: Optional[float] = None

    # REVEL (0-1, higher = more deleterious)
    revel_score: Optional[float] = None

    # MetaSVM
    metasvm_score: Optional[float] = None
    metasvm_prediction: Optional[str] = None  # 'D' or 'T'

    # Variant info
    variant_id: str = ""
    consequence: Optional[str] = None

    # Metadata
    source: str = "VEP"
    timestamp: datetime = field(default_factory=datetime.now)

    def count_deleterious(self) -> int:
        """Count number of algorithms predicting deleterious effect."""
        count: int = 0

        # SIFT: score < 0.05 is deleterious
        if self.sift_score is not None and self.sift_score < 0.05:
            count += 1
        elif self.sift_prediction and "deleterious" in self.sift_prediction.lower():
            count += 1

        # PolyPhen: score > 0.5 or 'damaging' prediction
        if self.polyphen_score is not None and self.polyphen_score > 0.5:
            count += 1
        elif (
            self.polyphen_prediction and "damaging" in self.polyphen_prediction.lower()
        ):
            count += 1

        # CADD: phred score >= 20
        if self.cadd_phred is not None and self.cadd_phred >= 20:
            count += 1

        # REVEL: score >= 0.5
        if self.revel_score is not None and self.revel_score >= 0.5:
            count += 1

        # MetaSVM: 'D' prediction
        if self.metasvm_prediction and self.metasvm_prediction == "D":
            count += 1

        return count

    def count_benign(self) -> int:
        """Count number of algorithms predicting benign effect."""
        count: int = 0

        # SIFT: score > 0.05 is tolerated
        if self.sift_score is not None and self.sift_score > 0.05:
            count += 1
        elif self.sift_prediction and "tolerated" in self.sift_prediction.lower():
            count += 1

        # PolyPhen: score < 0.3 or 'benign' prediction
        if self.polyphen_score is not None and self.polyphen_score < 0.3:
            count += 1
        elif self.polyphen_prediction and "benign" in self.polyphen_prediction.lower():
            count += 1

        # CADD: phred score < 15
        if self.cadd_phred is not None and self.cadd_phred < 15:
            count += 1

        # REVEL: score < 0.3
        if self.revel_score is not None and self.revel_score < 0.3:
            count += 1

        # MetaSVM: 'T' prediction
        if self.metasvm_prediction and self.metasvm_prediction == "T":
            count += 1

        return count

    def get_available_algorithms(self) -> List[str]:
        """Get list of algorithms with scores available."""
        available: List[str] = []
        if self.sift_score is not None or self.sift_prediction:
            available.append("SIFT")
        if self.polyphen_score is not None or self.polyphen_prediction:
            available.append("PolyPhen-2")
        if self.cadd_phred is not None:
            available.append("CADD")
        if self.revel_score is not None:
            available.append("REVEL")
        if self.metasvm_score is not None or self.metasvm_prediction:
            available.append("MetaSVM")
        return available

    @property
    def has_scores(self) -> bool:
        """Check if any prediction scores are available."""
        return any(
            [
                self.sift_score is not None,
                self.polyphen_score is not None,
                self.cadd_phred is not None,
                self.revel_score is not None,
                self.metasvm_score is not None,
            ]
        )

    def summary(self) -> str:
        """Generate human-readable summary."""
        deleterious: int = self.count_deleterious()
        benign: int = self.count_benign()
        algorithms: List[str] = self.get_available_algorithms()
        return (
            f"{deleterious} deleterious, {benign} benign ({len(algorithms)} algorithms)"
        )


class DbNSFPClient:
    """Client for accessing dbNSFP/VEP computational predictions.

    Uses Ensembl VEP REST API to retrieve predictions for variants.
    Supports caching and rate limiting.

    Note: Requires internet connectivity. For offline use, disable predictions
    at the service level or use engine_v7 (gnomAD only) or engine_v6 (base).

    Rate Limiting:
      Ensembl VEP has rate limits (15 requests/second for REST API).
      For bulk processing, consider:
        - Using batch endpoints (future enhancement)
        - Local VEP installation
        - Pre-caching predictions
        - Increasing cache TTL
    """

    DEFAULT_VEP_URL: str = "https://rest.ensembl.org"
    DEFAULT_TIMEOUT: int = 30
    DEFAULT_CACHE_TTL: int = 86400  # 24 hours

    def __init__(
        self,
        vep_url: str = DEFAULT_VEP_URL,
        timeout: int = DEFAULT_TIMEOUT,
        enable_cache: bool = True,
        cache_ttl: int = DEFAULT_CACHE_TTL,
        rate_limit: bool = True,
        max_requests_per_second: int = 15,  # VEP limit
    ) -> None:
        """Initialize dbNSFP/VEP client.

        Args:
            vep_url: Ensembl VEP API base URL
            timeout: Request timeout in seconds
            enable_cache: Enable in-memory caching
            cache_ttl: Cache time-to-live in seconds
            rate_limit: Enable rate limiting
            max_requests_per_second: Max requests per second

        Raises:
            Warning: If offline (no internet connectivity)
        """
        self.vep_url: str = vep_url.rstrip("/")
        self.timeout: int = timeout
        self.enable_cache: bool = enable_cache
        self.cache_ttl: timedelta = timedelta(seconds=cache_ttl)

        # Cache: variant_id -> (PredictionScore, timestamp)
        self._cache: Dict[str, Tuple[PredictionScore, datetime]] = {}

        # Rate limiting
        self.rate_limit: bool = rate_limit
        self.min_interval: float = 0.0
        self.last_request_time: float = 0.0
        if rate_limit:
            self.min_interval = 1.0 / max_requests_per_second

        # Session for connection pooling
        self.session: requests.Session = requests.Session()
        self.session.headers.update(
            {"Content-Type": "application/json", "Accept": "application/json"}
        )

        logger.info(
            f"DbNSFPClient initialized: VEP={vep_url}, cache={enable_cache}, "
            f"rate_limit={rate_limit}"
        )
        logger.info("Note: This client requires internet connectivity to function")

    def _wait_if_needed(self) -> None:
        """Wait if rate limit would be exceeded."""
        if not self.rate_limit:
            return

        current_time: float = time.time()
        time_since_last: float = current_time - self.last_request_time

        if time_since_last < self.min_interval:
            sleep_time: float = self.min_interval - time_since_last
            logger.debug(f"Rate limit: sleeping {sleep_time:.3f}s")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _get_from_cache(self, variant_id: str) -> Optional[PredictionScore]:
        """Retrieve prediction from cache if available and fresh."""
        if not self.enable_cache or variant_id not in self._cache:
            return None

        prediction, timestamp = self._cache[variant_id]
        age: timedelta = datetime.now() - timestamp

        if age < self.cache_ttl:
            logger.debug(f"Cache hit: {variant_id} (age: {age.seconds}s)")
            return prediction
        else:
            logger.debug(f"Cache expired: {variant_id} (age: {age.seconds}s)")
            del self._cache[variant_id]
            return None

    def _add_to_cache(self, variant_id: str, prediction: PredictionScore) -> None:
        """Add prediction to cache."""
        if self.enable_cache:
            self._cache[variant_id] = (prediction, datetime.now())
            logger.debug(f"Cached: {variant_id}")

    def clear_cache(self) -> None:
        """Clear all cached predictions."""
        self._cache.clear()
        logger.info("Cache cleared")

    def _parse_vep_response(
        self, data: List[Dict[str, Any]], variant_id: str
    ) -> Optional[PredictionScore]:
        """Parse VEP API response and extract predictions.

        Note: Not all algorithms may be available in VEP response.
        This is normal - VEP may not have scores for all variants/algorithms.
        Missing scores are handled gracefully.
        """
        try:
            if not data:
                return None

            # VEP returns list, usually one entry per variant
            variant_data: Dict[str, Any] = data[0] if isinstance(data, list) else data

            # Extract transcript consequences
            consequences: List[Dict[str, Any]] = variant_data.get(
                "transcript_consequences", []
            )
            if not consequences:
                logger.debug(f"No transcript consequences for {variant_id}")
                return None

            # Use first transcript (or most severe)
            transcript: Dict[str, Any] = consequences[0]

            prediction: PredictionScore = PredictionScore(
                variant_id=variant_id,
                consequence=transcript.get("consequence_terms", [""])[0],
                source="VEP",
            )

            # Extract SIFT
            if "sift_score" in transcript:
                prediction.sift_score = float(transcript["sift_score"])
            if "sift_prediction" in transcript:
                prediction.sift_prediction = transcript["sift_prediction"]

            # Extract PolyPhen
            if "polyphen_score" in transcript:
                prediction.polyphen_score = float(transcript["polyphen_score"])
            if "polyphen_prediction" in transcript:
                prediction.polyphen_prediction = transcript["polyphen_prediction"]

            # Extract CADD (if available in VEP plugins)
            if "cadd_phred" in transcript:
                prediction.cadd_phred = float(transcript["cadd_phred"])
            if "cadd_raw" in transcript:
                prediction.cadd_raw = float(transcript["cadd_raw"])

            # Extract REVEL (if available)
            if "revel" in transcript:
                prediction.revel_score = float(transcript["revel"])

            # Log available algorithms
            available: List[str] = prediction.get_available_algorithms()
            logger.info(f"Parsed predictions for {variant_id}: {prediction.summary()}")
            if len(available) < 3:
                logger.warning(
                    f"Limited algorithm coverage for {variant_id}: "
                    f"only {', '.join(available)} available"
                )

            return prediction

        except Exception as e:
            logger.error(f"Failed to parse VEP response for {variant_id}: {e}")
            return None

    def get_predictions(
        self, chromosome: str, position: int, ref: str, alt: str, species: str = "human"
    ) -> Optional[PredictionScore]:
        """Get computational predictions for a variant.

        Args:
            chromosome: Chromosome (e.g., '17', 'X')
            position: Genomic position
            ref: Reference allele
            alt: Alternate allele
            species: Species (default: 'human')

        Returns:
            PredictionScore object or None if not found/error

        Note:
            Requires internet connectivity. If offline, returns None
            and logs an error. Service will gracefully degrade.
        """
        variant_id: str = f"{chromosome}-{position}-{ref}-{alt}"

        # Check cache
        cached: Optional[PredictionScore] = self._get_from_cache(variant_id)
        if cached is not None:
            return cached

        try:
            # Rate limit
            self._wait_if_needed()

            # Construct VEP query
            # Format: /vep/human/region/17:43094692-43094692:1/A
            chrom: str = chromosome.replace("chr", "")
            url: str = (
                f"{self.vep_url}/vep/{species}/region/"
                f"{chrom}:{position}-{position}:1/{alt}"
            )

            logger.debug(f"VEP query: {url}")

            # Make request
            response: requests.Response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            data: List[Dict[str, Any]] = response.json()

            # Parse response
            prediction: Optional[PredictionScore] = self._parse_vep_response(
                data, variant_id
            )

            if prediction is None:
                logger.warning(f"No predictions found for {variant_id}")
                return None

            # Cache result
            self._add_to_cache(variant_id, prediction)

            return prediction

        except requests.exceptions.Timeout:
            logger.error(
                f"VEP request timeout for {variant_id} (offline or slow connection?)"
            )
            return None
        except requests.exceptions.ConnectionError:
            logger.error(
                f"VEP connection failed for {variant_id} (offline or VEP unavailable?)"
            )
            logger.info("Tip: For offline use, disable predictions or use engine_v7/v6")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"VEP request failed for {variant_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting predictions for {variant_id}: {e}")
            return None

    def get_statistics(self) -> Dict[str, Any]:
        """Get client statistics.

        Returns:
            Dictionary with cache and request statistics
        """
        return {
            "cache_enabled": self.enable_cache,
            "cache_size": len(self._cache),
            "cache_ttl_seconds": self.cache_ttl.seconds,
            "rate_limit_enabled": self.rate_limit,
            "vep_url": self.vep_url,
            "requires_internet": True,
        }

    def __del__(self) -> None:
        """Clean up session."""
        if hasattr(self, "session"):
            self.session.close()


if __name__ == "__main__":
    print("=" * 80)
    print("dbNSFP/VEP Client - Computational Predictions")
    print("=" * 80)
    print("\nSupported Algorithms:")
    print("  • SIFT: Sorting Intolerant From Tolerant")
    print("  • PolyPhen-2: Polymorphism Phenotyping v2")
    print("  • CADD: Combined Annotation Dependent Depletion")
    print("  • REVEL: Rare Exome Variant Ensemble Learner")
    print("  • MetaSVM: Meta-predictor using SVM")
    print("\nRequirements:")
    print("  ⚠️  Internet connectivity required")
    print("  • For offline use, disable predictions or use engine_v7/v6")
    print("\nUsage:")
    print("  client = DbNSFPClient()")
    print("  predictions = client.get_predictions('17', 43094692, 'G', 'A')")
    print("  if predictions:")
    print("      print(f'Available: {predictions.get_available_algorithms()}')")
    print("      print(f'Deleterious: {predictions.count_deleterious()}')")
    print("      print(f'Benign: {predictions.count_benign()}')")
    print("=" * 80)
else:
    logger.info("DbNSFPClient loaded - Ensembl VEP integration (requires internet)")
