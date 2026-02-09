"""
Functional scores integration for ACMG PS3 evidence code.
Supports AlphaMissense, ESM-1v, EVE, and experimental data.
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple, Union
from dataclasses import dataclass
from pathlib import Path
import pysam
import requests
from varidex.core.config import PS3_THRESHOLDS, FUNCTIONAL_SOURCES

logger = logging.getLogger(__name__)


@dataclass
class FunctionalScore:
    """Single functional prediction score."""

    source: str
    score: float
    score_type: str  # 'pathogenic', 'benign', 'logit', 'probability'
    confidence: Optional[float] = None
    evidence_level: str = "supporting"  # 'strong', 'moderate', 'supporting'


@dataclass
class PS3Evidence:
    """PS3 evidence result."""

    applied: bool
    strength: str  # 'Strong', 'Moderate', 'Supporting'
    scores: List[FunctionalScore]
    decision_rationale: str
    num_supporting_sources: int = 0
    num_conflicting_sources: int = 0


class FunctionalScoreLoader:
    """
    Load and aggregate functional scores for PS3 evidence.
    Supports multiple prediction methods and experimental data.
    """

    def __init__(self, config: Dict[str, Union[str, Path]]):
        """
        Initialize with data source paths.

        Args:
            config: Dict with keys:
                - alphamissense_tsv: AlphaMissense predictions
                - esm1v_tsv: ESM-1v scores
                - eve_scores: EVE predictions
                - experimental_db: Literature/experimental data
        """
        self.config = config
        self._alphamissense_cache = {}
        self._esm1v_cache = {}

    def load_alphamissense(self, gene: str, variant: str) -> Optional[FunctionalScore]:
        """Load AlphaMissense score (pathogenic probability 0-1)."""
        try:
            if gene not in self._alphamissense_cache:
                self._load_alphamissense_gene(gene)

            key = f"{gene}_{variant}"
            if key in self._alphamissense_cache:
                score_data = self._alphamissense_cache[key]
                if score_data["pathogenicity_score"] > PS3_THRESHOLDS["alphamissense"]:
                    return FunctionalScore(
                        source="AlphaMissense",
                        score=score_data["pathogenicity_score"],
                        score_type="probability",
                        confidence=score_data.get("confidence", None),
                    )
            return None
        except Exception as e:
            logger.warning(f"AlphaMissense load failed for {gene}:{variant}: {e}")
            return None

    def _load_alphamissense_gene(self, gene: str):
        """Load entire gene predictions into cache."""
        tsv_path = Path(self.config["alphamissense_tsv"])
        if not tsv_path.exists():
            return

        df = pd.read_csv(tsv_path, sep="\t", low_memory=False)
        gene_df = df[df["gene"] == gene]

        for _, row in gene_df.iterrows():
            variant_key = f"{row['gene']}_{row['aa_change']}"
            self._alphamissense_cache[variant_key] = {
                "pathogenicity_score": row["pathogenicity_score"],
                "confidence": row.get("confidence_score"),
            }

    def load_esm1v(self, gene: str, variant: str) -> Optional[FunctionalScore]:
        """Load ESM-1v embedding-based score (logit)."""
        try:
            tbx = pysam.TabixFile(self.config["esm1v_tsv"])
            for row in tbx.fetch(gene, parser=pysam.TabixFile):
                fields = row.split("\t")
                if len(fields) >= 4 and fields[3] == variant:
                    esm_score = float(fields[4])  # logit score
                    if esm_score > PS3_THRESHOLDS["esm1v"]:
                        return FunctionalScore(
                            source="ESM-1v", score=esm_score, score_type="logit"
                        )
            return None
        except Exception as e:
            logger.warning(f"ESM-1v load failed: {e}")
            return None

    def load_eve(self, gene: str, variant: str) -> Optional[FunctionalScore]:
        """Load EVE evolutionary conservation score."""
        try:
            # EVE scores typically in HDF5 or custom format
            # Placeholder for EVE integration
            eve_path = Path(self.config["eve_scores"])
            if not eve_path.exists():
                return None

            # Parse EVE output (format varies by implementation)
            # This is a simplified example
            with open(eve_path, "r") as f:
                for line in f:
                    if gene in line and variant in line:
                        parts = line.strip().split()
                        eve_score = float(parts[5])  # Adjust index
                        if (
                            eve_score < PS3_THRESHOLDS["eve"]
                        ):  # Lower is more deleterious
                            return FunctionalScore(
                                source="EVE", score=eve_score, score_type="conservation"
                            )
            return None
        except Exception as e:
            logger.warning(f"EVE load failed: {e}")
            return None

    def load_experimental(self, variant_id: str) -> List[FunctionalScore]:
        """Load experimental/literature evidence."""
        scores = []
        try:
            # Query literature databases (ClinVar, HGMD, PubMed)
            experimental_data = self._query_experimental_dbs(variant_id)

            for source, evidence in experimental_data.items():
                if evidence["deleterious"]:
                    scores.append(
                        FunctionalScore(
                            source=source,
                            score=evidence["strength_score"],  # 0.8-1.0
                            score_type="experimental",
                            confidence=evidence.get("confidence"),
                            evidence_level=evidence["level"],
                        )
                    )
        except Exception as e:
            logger.warning(f"Experimental data load failed: {e}")

        return scores

    def _query_experimental_dbs(self, variant_id: str) -> Dict:
        """Query ClinVar, HGMD, literature for experimental evidence."""
        # Placeholder - implement based on your data sources
        return {}

    def aggregate_scores(self, gene: str, variant: str, variant_id: str) -> PS3Evidence:
        """
        Aggregate all functional scores and make PS3 decision.

        Returns PS3Evidence object for integration with ACMG engine.
        """
        all_scores = []

        # Computational predictions
        am_score = self.load_alphamissense(gene, variant)
        if am_score:
            all_scores.append(am_score)

        esm_score = self.load_esm1v(gene, variant)
        if esm_score:
            all_scores.append(esm_score)

        eve_score = self.load_eve(gene, variant)
        if eve_score:
            all_scores.append(eve_score)

        # Experimental evidence
        exp_scores = self.load_experimental(variant_id)
        all_scores.extend(exp_scores)

        # Decision logic
        supporting = [
            s for s in all_scores if s.evidence_level in ["strong", "moderate"]
        ]
        total_sources = len(all_scores)
        supporting_sources = len(supporting)

        if supporting_sources >= 2 or any(
            s.evidence_level == "strong" for s in all_scores
        ):
            strength = "Strong"
        elif supporting_sources == 1:
            strength = "Moderate"
        else:
            strength = "None"

        applied = strength != "None"
        rationale = self._generate_rationale(all_scores, strength)

        return PS3Evidence(
            applied=applied,
            strength=strength,
            scores=all_scores,
            decision_rationale=rationale,
            num_supporting_sources=supporting_sources,
            num_conflicting_sources=total_sources - supporting_sources,
        )

    def _generate_rationale(self, scores: List[FunctionalScore], strength: str) -> str:
        """Generate human-readable decision rationale."""
        if not scores:
            return "No functional data available"

        sources = [s.source for s in scores]
        supporting = [s for s in scores if s.score > 0.7]  # Threshold for "supporting"

        if strength == "Strong":
            return f"Strong PS3: {len(supporting)}/{len(scores)} sources deleterious (AlphaMissense, ESM-1v, experimental)"
        elif strength == "Moderate":
            return f"Moderate PS3: 1+ sources deleterious ({', '.join(sources[:3])})"
        else:
            return f"No PS3: Benign predictions from {', '.join(sources)}"


# Global loader instance (singleton pattern)
_functional_loader: Optional[FunctionalScoreLoader] = None


def get_functional_loader(config: Dict) -> FunctionalScoreLoader:
    """Get singleton FunctionalScoreLoader instance."""
    global _functional_loader
    if _functional_loader is None:
        _functional_loader = FunctionalScoreLoader(config)
    return _functional_loader


def evaluate_ps3(gene: str, variant: str, variant_id: str, config: Dict) -> PS3Evidence:
    """
    Main entry point for PS3 evaluation.

    Args:
        gene: HGNC gene symbol
        variant: Protein variant (p.Arg123His)
        variant_id: Unique variant identifier
        config: Data source configuration

    Returns:
        PS3Evidence object
    """
    loader = get_functional_loader(config)
    return loader.aggregate_scores(gene, variant, variant_id)
