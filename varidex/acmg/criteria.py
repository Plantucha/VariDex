"""
ACMG/AMP Evidence Set for Variant Classification.

This module implements the ACMG/AMP variant interpretation guidelines
for classifying genetic variants based on evidence criteria.

Version: DEVELOPMENT
Based on: Richards et al. 2015 (PMID: 25741868)
Last updated: 2026-02-08

Reference:
    Richards S, et al. (2015) Standards and guidelines for the interpretation
    of sequence variants: a joint consensus recommendation of the American
    College of Medical Genetics and Genomics and the Association for Molecular
    Pathology. Genet Med. 17(5):405-24.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple


class PathogenicityClass(Enum):
    """ACMG/AMP variant classification categories."""

    PATHOGENIC = "Pathogenic"
    LIKELY_PATHOGENIC = "Likely Pathogenic"
    UNCERTAIN = "Uncertain Significance"
    LIKELY_BENIGN = "Likely Benign"
    BENIGN = "Benign"


@dataclass
class ACMGEvidenceSet:
    """
    ACMG/AMP Evidence Set for variant classification.

    Contains all 28 ACMG criteria as boolean flags and methods for
    classification, validation, and reporting.

    Pathogenic Evidence:
        - PVS1: Very strong pathogenic evidence
        - PS1-4: Strong pathogenic evidence
        - PM1-6: Moderate pathogenic evidence
        - PP1-5: Supporting pathogenic evidence

    Benign Evidence:
        - BA1: Stand-alone benign evidence
        - BS1-4: Strong benign evidence
        - BP1-7: Supporting benign evidence

    Example:
        >>> evidence = ACMGEvidenceSet(pvs1=True, pm2=True, pp3=True)
        >>> evidence.get_classification()
        <PathogenicityClass.PATHOGENIC: 'Pathogenic'>
    """

    # Pathogenic - Very Strong
    pvs1: bool = False

    # Pathogenic - Strong
    ps1: bool = False
    ps2: bool = False
    ps3: bool = False
    ps4: bool = False

    # Pathogenic - Moderate
    pm1: bool = False
    pm2: bool = False
    pm3: bool = False
    pm4: bool = False
    pm5: bool = False
    pm6: bool = False

    # Pathogenic - Supporting
    pp1: bool = False
    pp2: bool = False
    pp3: bool = False
    pp4: bool = False
    pp5: bool = False

    # Benign - Stand-alone
    ba1: bool = False

    # Benign - Strong
    bs1: bool = False
    bs2: bool = False
    bs3: bool = False
    bs4: bool = False

    # Benign - Supporting
    bp1: bool = False
    bp2: bool = False
    bp3: bool = False
    bp4: bool = False
    bp5: bool = False
    bp6: bool = False
    bp7: bool = False

    # Optional metadata
    evidence_notes: Dict[str, str] = field(default_factory=dict)

    def count_pvs(self) -> int:
        """Count very strong pathogenic evidence."""
        return int(self.pvs1)

    def count_ps(self) -> int:
        """Count strong pathogenic evidence."""
        return sum([self.ps1, self.ps2, self.ps3, self.ps4])

    def count_pm(self) -> int:
        """Count moderate pathogenic evidence."""
        return sum([self.pm1, self.pm2, self.pm3, self.pm4, self.pm5, self.pm6])

    def count_pp(self) -> int:
        """Count supporting pathogenic evidence."""
        return sum([self.pp1, self.pp2, self.pp3, self.pp4, self.pp5])

    def count_ba(self) -> int:
        """Count stand-alone benign evidence."""
        return int(self.ba1)

    def count_bs(self) -> int:
        """Count strong benign evidence."""
        return sum([self.bs1, self.bs2, self.bs3, self.bs4])

    def count_bp(self) -> int:
        """Count supporting benign evidence."""
        return sum([self.bp1, self.bp2, self.bp3, self.bp4, self.bp5, self.bp6, self.bp7])

    def has_conflicting_evidence(self) -> bool:
        """
        Check for conflicting pathogenic and benign evidence.

        Returns:
            True if both pathogenic and benign evidence are present,
            requiring careful manual review.
        """
        has_pathogenic = (
            self.count_pvs() > 0
            or self.count_ps() > 0
            or self.count_pm() > 0
            or self.count_pp() > 0
        )

        has_benign = (
            self.count_ba() > 0 or self.count_bs() > 0 or self.count_bp() > 0
        )

        return has_pathogenic and has_benign

    def get_classification(self) -> PathogenicityClass:
        """
        Apply ACMG combination rules for final classification.

        Uses the evidence combination rules from Richards et al. 2015 Table 5
        to determine the appropriate pathogenicity classification.

        Returns:
            PathogenicityClass enum value.

        Note:
            BA1 (stand-alone benign) overrides all other evidence.
            If conflicting evidence exists, manual review is recommended.
        """
        # Stand-alone benign overrides all
        if self.ba1:
            return PathogenicityClass.BENIGN

        # Count evidence by strength
        pvs = self.count_pvs()
        ps = self.count_ps()
        pm = self.count_pm()
        pp = self.count_pp()
        bs = self.count_bs()
        bp = self.count_bp()

        # PATHOGENIC combinations (any of these)
        pathogenic_rules = [
            pvs >= 1 and ps >= 1,  # i.   PVS1 + PS1-4
            pvs >= 1 and pm >= 2,  # ii.  PVS1 + 2×PM
            pvs >= 1 and pm == 1 and pp >= 1,  # iii. PVS1 + PM + PP
            pvs >= 1 and pp >= 2,  # iv.  PVS1 + 2×PP
            ps >= 2,  # v.   2×PS
            ps >= 1 and pm >= 3,  # vi.  PS + 3×PM
            ps >= 1 and pm >= 2 and pp >= 2,  # vii. PS + 2×PM + 2×PP
            ps >= 1 and pm >= 1 and pp >= 4,  # viii.PS + PM + 4×PP
        ]

        if any(pathogenic_rules):
            return PathogenicityClass.PATHOGENIC

        # LIKELY PATHOGENIC combinations (any of these)
        likely_pathogenic_rules = [
            pvs >= 1 and pm >= 1,  # i.   PVS1 + PM
            ps >= 1 and pm >= 1,  # ii.  PS + 1-2×PM
            ps >= 1 and pp >= 2,  # iii. PS + 2×PP
            pm >= 3,  # iv.  ≥3×PM
            pm >= 2 and pp >= 2,  # v.   2×PM + 2×PP
            pm >= 1 and pp >= 4,  # vi.  PM + ≥4×PP
        ]

        if any(likely_pathogenic_rules):
            return PathogenicityClass.LIKELY_PATHOGENIC

        # BENIGN combinations
        benign_rules = [
            bs >= 2,  # i.   ≥2×BS
            bs >= 1 and bp >= 1,  # ii.  BS + BP
        ]

        if any(benign_rules):
            return PathogenicityClass.BENIGN

        # LIKELY BENIGN
        if bs >= 1 or bp >= 2:
            return PathogenicityClass.LIKELY_BENIGN

        # Default: Uncertain Significance
        return PathogenicityClass.UNCERTAIN

    def get_evidence_list(self) -> Tuple[List[str], List[str]]:
        """
        Get lists of met pathogenic and benign evidence codes.

        Returns:
            Tuple of (pathogenic_codes, benign_codes) where each is a list
            of criterion names (e.g., ['PVS1', 'PM2', 'PP3']).
        """
        pathogenic = []
        benign = []

        # Pathogenic evidence
        if self.pvs1:
            pathogenic.append("PVS1")
        for i in range(1, 5):
            if getattr(self, f"ps{i}"):
                pathogenic.append(f"PS{i}")
        for i in range(1, 7):
            if getattr(self, f"pm{i}"):
                pathogenic.append(f"PM{i}")
        for i in range(1, 6):
            if getattr(self, f"pp{i}"):
                pathogenic.append(f"PP{i}")

        # Benign evidence
        if self.ba1:
            benign.append("BA1")
        for i in range(1, 5):
            if getattr(self, f"bs{i}"):
                benign.append(f"BS{i}")
        for i in range(1, 8):
            if getattr(self, f"bp{i}"):
                benign.append(f"BP{i}")

        return pathogenic, benign

    def validate(self) -> List[str]:
        """
        Validate evidence for common contradictions and errors.

        Checks for known criterion conflicts that indicate potential
        errors in evidence assignment.

        Returns:
            List of warning messages. Empty list if no issues found.
        """
        warnings = []

        # PM2 (absent from controls) conflicts with BS1/BS2 (high frequency)
        if self.pm2 and (self.bs1 or self.bs2):
            warnings.append(
                "PM2 conflicts with BS1/BS2: population frequency contradiction"
            )

        # PS4 (prevalence increased) conflicts with BS4 (lack of segregation)
        if self.ps4 and self.bs4:
            warnings.append(
                "PS4 conflicts with BS4: case-control data contradiction"
            )

        # PP2 (missense in gene with low missense) conflicts with BP1
        if self.pp2 and self.bp1:
            warnings.append(
                "PP2 conflicts with BP1: missense mechanism contradiction"
            )

        # PS3 (functional studies supportive) conflicts with BS3
        if self.ps3 and self.bs3:
            warnings.append(
                "PS3 conflicts with BS3: functional studies contradiction"
            )

        # PM3 (in trans with pathogenic) conflicts with BP2 (in trans with benign)
        if self.pm3 and self.bp2:
            warnings.append("PM3 conflicts with BP2: phase data contradiction")

        return warnings

    def add_evidence_note(self, criterion: str, note: str) -> None:
        """
        Add documentation for why a criterion was met.

        Args:
            criterion: Evidence code (e.g., 'PM2', 'PS1')
            note: Explanation or data supporting the criterion
        """
        self.evidence_notes[criterion.upper()] = note

    def to_clinvar_format(self) -> Dict[str, any]:
        """
        Export evidence in ClinVar submission format.

        Returns:
            Dictionary compatible with ClinVar API submission format.
        """
        pathogenic, benign = self.get_evidence_list()

        return {
            "classificationReviewStatus": "criteria provided, single submitter",
            "germlineClassification": self.get_classification().value,
            "citedEvidence": {"pathogenic": pathogenic, "benign": benign},
        }

    def __str__(self) -> str:
        """
        Generate human-readable evidence summary.

        Returns:
            Multi-line string with classification and evidence lists.
        """
        pathogenic, benign = self.get_evidence_list()
        classification = self.get_classification()
        conflict = self.has_conflicting_evidence()
        validation_warnings = self.validate()

        path_str = ", ".join(pathogenic) if pathogenic else "None"
        ben_str = ", ".join(benign) if benign else "None"
        conflict_str = " ⚠️  CONFLICTING EVIDENCE" if conflict else ""

        result = [
            f"Classification: {classification.value}{conflict_str}",
            f"Pathogenic Evidence: {path_str}",
            f"Benign Evidence: {ben_str}",
        ]

        if validation_warnings:
            result.append("Warnings:")
            for warning in validation_warnings:
                result.append(f"  - {warning}")

        return "\n".join(result)


# Backward compatibility alias
ACMGCriteria = ACMGEvidenceSet
