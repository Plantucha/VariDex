"""Population frequency analysis service for ACMG evidence codes.

This module provides logic for interpreting population allele frequencies
to determine ACMG evidence codes PM2, BA1, and BS1.

References:
    Richards S, et al. Standards and guidelines for the interpretation of
    sequence variants. Genet Med. 2015;17(5):405-24. PMID: 25741868
"""

import logging
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from varidex.integrations.gnomad_client import GnomadVariantFrequency, GnomadClient

logger: logging.Logger = logging.getLogger(__name__)


class InheritanceMode(Enum):
    """Inheritance mode for disease."""

    DOMINANT = "dominant"
    RECESSIVE = "recessive"
    X_LINKED = "x_linked"
    UNKNOWN = "unknown"


@dataclass
class FrequencyThresholds:
    """Thresholds for population frequency evidence codes."""

    # PM2: Absent from controls (rare variant)
    pm2_dominant_threshold: float = 0.0001  # 0.01% for dominant
    pm2_recessive_threshold: float = 0.01  # 1% for recessive

    # BA1: Stand-alone benign (common polymorphism)
    ba1_threshold: float = 0.05  # 5% in any population

    # BS1: Allele frequency greater than expected
    bs1_dominant_threshold: float = 0.01  # 1% for dominant
    bs1_recessive_threshold: float = 0.02  # 2% for recessive

    # Minimum allele number for confidence
    min_allele_number: int = 2000  # Require at least 1000 individuals


@dataclass
class FrequencyEvidence:
    """Evidence from population frequency analysis."""

    pm2: bool = False  # Absent from controls
    ba1: bool = False  # Stand-alone benign
    bs1: bool = False  # Allele frequency too high

    max_af: Optional[float] = None
    max_af_population: Optional[str] = None
    genome_af: Optional[float] = None
    exome_af: Optional[float] = None

    reasoning: str = ""

    def has_evidence(self) -> bool:
        """Check if any evidence codes were triggered."""
        return self.pm2 or self.ba1 or self.bs1

    def summary(self) -> str:
        """Generate summary of evidence."""
        codes = []
        if self.pm2:
            codes.append("PM2")
        if self.ba1:
            codes.append("BA1")
        if self.bs1:
            codes.append("BS1")

        if not codes:
            return "No frequency-based evidence"

        af_str: str = (
            f"AF={self.max_af:.6f}" if self.max_af is not None else "AF=unknown"
        )
        return f"{', '.join(codes)} ({af_str})"


class PopulationFrequencyService:
    """Service for analyzing population frequencies for ACMG classification."""

    def __init__(
        self,
        gnomad_client: Optional[GnomadClient] = None,
        thresholds: Optional[FrequencyThresholds] = None,
        enable_gnomad: bool = True,
    ) -> None:
        """Initialize population frequency service.

        Args:
            gnomad_client: GnomadClient instance (created if None)
            thresholds: Custom frequency thresholds
            enable_gnomad: Enable gnomAD queries (disable for testing)
        """
        self.enable_gnomad: bool = enable_gnomad
        self.gnomad_client: Optional[GnomadClient] = (
            gnomad_client if enable_gnomad else None
        )
        self.thresholds: FrequencyThresholds = thresholds or FrequencyThresholds()

        if enable_gnomad and self.gnomad_client is None:
            self.gnomad_client = GnomadClient()

        logger.info(f"Initialized PopulationFrequencyService (gnomAD: {enable_gnomad})")

    def _check_pm2(
        self, freq: GnomadVariantFrequency, inheritance: InheritanceMode
    ) -> Tuple[bool, str]:
        """Check PM2 criteria: Absent from controls in gnomAD.

        PM2 applies when variant is absent or at extremely low frequency:
        - Dominant: AF < 0.01% (0.0001)
        - Recessive: AF < 1% (0.01)

        Args:
            freq: gnomAD frequency data
            inheritance: Inheritance mode

        Returns:
            Tuple of (evidence_applies, reasoning)
        """
        max_af: Optional[float] = freq.max_af

        # If no frequency data, assume absent (PM2 applies)
        if max_af is None:
            return True, "Variant absent from gnomAD (PM2 applies)"

        # Check thresholds based on inheritance
        if inheritance == InheritanceMode.DOMINANT:
            threshold: float = self.thresholds.pm2_dominant_threshold
            if max_af < threshold:
                return True, f"AF {max_af:.6f} < {threshold} for dominant (PM2 applies)"

        elif inheritance == InheritanceMode.RECESSIVE:
            threshold = self.thresholds.pm2_recessive_threshold
            if max_af < threshold:
                return (
                    True,
                    f"AF {max_af:.6f} < {threshold} for recessive (PM2 applies)",
                )

        else:
            # Unknown inheritance: use dominant threshold (more stringent)
            threshold = self.thresholds.pm2_dominant_threshold
            if max_af < threshold:
                return (
                    True,
                    f"AF {max_af:.6f} < {threshold} (PM2 applies, unknown inheritance)",
                )

        return False, f"AF {max_af:.6f} too high for PM2"

    def _check_ba1(self, freq: GnomadVariantFrequency) -> Tuple[bool, str]:
        """Check BA1 criteria: Allele frequency > 5% in any population.

        BA1 is a stand-alone benign evidence code.

        Args:
            freq: gnomAD frequency data

        Returns:
            Tuple of (evidence_applies, reasoning)
        """
        max_af: Optional[float] = freq.max_af

        if max_af is None:
            return False, "No frequency data for BA1"

        threshold: float = self.thresholds.ba1_threshold

        if max_af > threshold:
            pop: str = freq.popmax_population or "unknown"
            return True, f"AF {max_af:.6f} > {threshold} in {pop} (BA1 applies)"

        return False, f"AF {max_af:.6f} below BA1 threshold ({threshold})"

    def _check_bs1(
        self, freq: GnomadVariantFrequency, inheritance: InheritanceMode
    ) -> Tuple[bool, str]:
        """Check BS1 criteria: Allele frequency greater than expected for disorder.

        BS1 applies when frequency is higher than expected:
        - Dominant: AF > 1% (0.01)
        - Recessive: AF > 2% (0.02)

        Args:
            freq: gnomAD frequency data
            inheritance: Inheritance mode

        Returns:
            Tuple of (evidence_applies, reasoning)
        """
        max_af: Optional[float] = freq.max_af

        if max_af is None:
            return False, "No frequency data for BS1"

        # Determine threshold based on inheritance
        threshold: float
        if inheritance == InheritanceMode.DOMINANT:
            threshold = self.thresholds.bs1_dominant_threshold
        elif inheritance == InheritanceMode.RECESSIVE:
            threshold = self.thresholds.bs1_recessive_threshold
        else:
            # Unknown: use dominant threshold (more stringent)
            threshold = self.thresholds.bs1_dominant_threshold

        # BA1 takes precedence over BS1 (BA1 is > 5%)
        ba1_threshold: float = self.thresholds.ba1_threshold
        if max_af > ba1_threshold:
            return False, f"AF {max_af:.6f} exceeds BA1 threshold, BA1 applies instead"

        if max_af > threshold:
            mode_str: str = (
                inheritance.value
                if inheritance != InheritanceMode.UNKNOWN
                else "unknown"
            )
            return True, f"AF {max_af:.6f} > {threshold} for {mode_str} (BS1 applies)"

        return False, f"AF {max_af:.6f} below BS1 threshold ({threshold})"

    def _check_allele_number_confidence(
        self, freq: GnomadVariantFrequency
    ) -> Tuple[bool, str]:
        """Check if allele number is sufficient for confident frequency estimate.

        Args:
            freq: gnomAD frequency data

        Returns:
            Tuple of (sufficient, message)
        """
        an: Optional[int] = freq.genome_an or freq.exome_an

        if an is None:
            return False, "No allele number data"

        if an < self.thresholds.min_allele_number:
            return (
                False,
                f"Low allele number (AN={an} < {self.thresholds.min_allele_number})",
            )

        return True, f"Sufficient allele number (AN={an})"

    def analyze_frequency(
        self,
        chromosome: str,
        position: int,
        ref: str,
        alt: str,
        inheritance: InheritanceMode = InheritanceMode.UNKNOWN,
        gene: Optional[str] = None,
    ) -> FrequencyEvidence:
        """Analyze population frequency and determine evidence codes.

        Args:
            chromosome: Chromosome (1-22, X, Y)
            position: Genomic position
            ref: Reference allele
            alt: Alternate allele
            inheritance: Inheritance mode for the disorder
            gene: Gene symbol (optional, for logging)

        Returns:
            FrequencyEvidence with PM2, BA1, BS1 determinations
        """
        evidence: FrequencyEvidence = FrequencyEvidence()

        # If gnomAD disabled, return empty evidence
        if not self.enable_gnomad or self.gnomad_client is None:
            evidence.reasoning = "gnomAD integration disabled"
            logger.debug("gnomAD disabled, skipping frequency analysis")
            return evidence

        try:
            # Query gnomAD
            variant_str: str = f"{chromosome}:{position}:{ref}>{alt}"
            if gene:
                variant_str += f" ({gene})"

            logger.info(f"Querying gnomAD for {variant_str}")

            freq: Optional[GnomadVariantFrequency] = (
                self.gnomad_client.get_variant_frequency(
                    chromosome=chromosome, position=position, ref=ref, alt=alt
                )
            )

            if freq is None:
                # Not found in gnomAD - treat as absent (PM2 applies)
                evidence.pm2 = True
                evidence.reasoning = (
                    "Variant not found in gnomAD (absent - PM2 applies)"
                )
                logger.info(f"Variant not in gnomAD: PM2 applies for {variant_str}")
                return evidence

            # Store frequency info
            evidence.max_af = freq.max_af
            evidence.max_af_population = freq.popmax_population
            evidence.genome_af = freq.genome_af
            evidence.exome_af = freq.exome_af

            # Check allele number confidence
            sufficient: bool
            an_msg: str
            sufficient, an_msg = self._check_allele_number_confidence(freq)
            if not sufficient:
                logger.warning(f"Low confidence in frequency: {an_msg}")

            # Check evidence codes (order matters: BA1 > BS1 > PM2)

            # BA1: Stand-alone benign (most significant)
            ba1_applies: bool
            ba1_reason: str
            ba1_applies, ba1_reason = self._check_ba1(freq)
            if ba1_applies:
                evidence.ba1 = True
                evidence.reasoning = ba1_reason
                logger.info(f"BA1 applies for {variant_str}: {ba1_reason}")
                return evidence  # BA1 is stand-alone, no other codes needed

            # BS1: Frequency too high for disorder
            bs1_applies: bool
            bs1_reason: str
            bs1_applies, bs1_reason = self._check_bs1(freq, inheritance)
            if bs1_applies:
                evidence.bs1 = True
                evidence.reasoning = bs1_reason
                logger.info(f"BS1 applies for {variant_str}: {bs1_reason}")
                return evidence  # BS1 excludes PM2

            # PM2: Absent/rare in controls
            pm2_applies: bool
            pm2_reason: str
            pm2_applies, pm2_reason = self._check_pm2(freq, inheritance)
            if pm2_applies:
                evidence.pm2 = True
                evidence.reasoning = pm2_reason
                logger.info(f"PM2 applies for {variant_str}: {pm2_reason}")
            else:
                evidence.reasoning = f"No frequency evidence: {pm2_reason}"
                logger.debug(f"No frequency evidence for {variant_str}")

            return evidence

        except Exception as e:
            logger.error(f"Error analyzing frequency: {e}")
            evidence.reasoning = f"Error querying gnomAD: {str(e)}"
            return evidence

    def get_statistics(self) -> Dict[str, Any]:
        """Get service statistics.

        Returns:
            Dictionary with service stats
        """
        stats: Dict[str, Any] = {
            "enabled": self.enable_gnomad,
            "thresholds": {
                "pm2_dominant": self.thresholds.pm2_dominant_threshold,
                "pm2_recessive": self.thresholds.pm2_recessive_threshold,
                "ba1": self.thresholds.ba1_threshold,
                "bs1_dominant": self.thresholds.bs1_dominant_threshold,
                "bs1_recessive": self.thresholds.bs1_recessive_threshold,
            },
        }

        if self.gnomad_client:
            stats["cache"] = self.gnomad_client.get_cache_stats()

        return stats
