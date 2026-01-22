#!/usr/bin/env python3
"""varidex/core/schema.py - Canonical schema helpers (v6)

Defines the canonical internal schema and minimal validators.
This module MUST NOT drop columns (no feature removal). It only:
- maps aliases to canonical names
- validates required columns
- applies safe type coercions

Notes:
- Required sets are v6-minimal and should not grow without a coordinated migration.
- Optional future fields (points/gnomAD/scores) are permitted but not required.
"""

from __future__ import annotations

from typing import Dict, Optional, Sequence
import pandas as pd

from varidex.exceptions import ValidationError

# ---------------- Canonical column names ----------------

CANON_CHROM = "chromosome"
CANON_POS = "position"
CANON_RSID = "rsid"
CANON_REF = "ref_allele"
CANON_ALT = "alt_allele"
CANON_GT = "genotype"
CANON_COORD_KEY = "coord_key"

# Optional future fields (allowed, never required in v6)
CANON_ACMG_VERSION = "acmg_version"
CANON_TOTAL_POINTS = "total_points"
CANON_POINT_BREAKDOWN = "point_breakdown"
CANON_GNOMAD_AF = "gnomad_a"
CANON_POPULATION_AF = "population_a"
CANON_GNOMAD_MODE = "gnomad_mode"
CANON_IN_SILICO_SCORES = "in_silico_scores"

# ---------------- Required sets (v6 minimal) ----------------

REQUIRED_CLINVAR_DF = (CANON_CHROM, CANON_POS, CANON_REF, CANON_ALT, CANON_COORD_KEY)
REQUIRED_USER_DF = (CANON_CHROM, CANON_POS, CANON_GT)
REQUIRED_MATCHED_DF = (
    CANON_CHROM,
    CANON_POS,
    CANON_GT,
    "gene",
    "clinical_sig",
    "review_status",
    "variant_type",
    "molecular_consequence",
)

# ---------------- Alias maps (generic) ----------------

DEFAULT_ALIASES: Dict[str, str] = {
    # chromosome
    "#chrom": CANON_CHROM,
    "chrom": CANON_CHROM,
    "chr": CANON_CHROM,
    "chromosome": CANON_CHROM,
    # position
    "pos": CANON_POS,
    "position": CANON_POS,
    "start": CANON_POS,
    # identifiers
    "id": CANON_RSID,
    "rs# (dbsnp)": CANON_RSID,
    "rsid": CANON_RSID,
    # alleles
    "re": CANON_REF,
    "reference": CANON_REF,
    "ref_allele": CANON_REF,
    "alt": CANON_ALT,
    "alternate": CANON_ALT,
    "alt_allele": CANON_ALT,
    # genotype
    "gt": CANON_GT,
    "genotype": CANON_GT,
    # common ClinVar-style spellings
    "clinicalsignificance": "clinical_sig",
    "clinical significance": "clinical_sig",
    "clinical_sig": "clinical_sig",
    "reviewstatus": "review_status",
    "review status": "review_status",
    "review_status": "review_status",
    "numsubmitters": "num_submitters",
    "num_submitters": "num_submitters",
    "varianttype": "variant_type",
    "variant type": "variant_type",
    "variant_type": "variant_type",
    "molecularconsequence": "molecular_consequence",
    "molecular consequence": "molecular_consequence",
    "molecular_consequence": "molecular_consequence",
    # optional future
    "gnomad_a": CANON_GNOMAD_AF,
    "population_a": CANON_POPULATION_AF,
    "acmg_version": CANON_ACMG_VERSION,
    "total_points": CANON_TOTAL_POINTS,
    "point_breakdown": CANON_POINT_BREAKDOWN,
    "in_silico_scores": CANON_IN_SILICO_SCORES,
    "gnomad_mode": CANON_GNOMAD_MODE,
}


def _norm_header(h: str) -> str:
    return str(h).strip().lower()


def apply_aliases(df: pd.DataFrame, aliases: Optional[Dict[str, str]] = None) -> pd.DataFrame:
    """Return a copy of df with alias-based renames applied.

    - Does NOT remove columns.
    - If multiple columns map to same canonical name, the first occurrence wins.
    """
    if df is None:
        raise ValidationError("DataFrame is None", context={"stage": "schema"})

    aliases = aliases or DEFAULT_ALIASES
    rename_map: Dict[str, str] = {}
    seen_targets = set()

    for col in df.columns:
        key = _norm_header(col)
        target = aliases.get(key)
        if target and target not in seen_targets and col != target:
            rename_map[col] = target
            seen_targets.add(target)

    if not rename_map:
        return df.copy()
    return df.rename(columns=rename_map).copy()


def require_columns(df: pd.DataFrame, required: Sequence[str], stage: str) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValidationError(
            "Missing required columns",
            context={"stage": stage, "missing": missing, "present": list(df.columns)[:50]},
        )


def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    """Best-effort coercion without dropping rows."""
    out = df.copy()

    if CANON_CHROM in out.columns:
        out[CANON_CHROM] = out[CANON_CHROM].astype(str)

    if CANON_POS in out.columns:
        out[CANON_POS] = pd.to_numeric(out[CANON_POS], errors="coerce").astype("Int64")

    for c in (CANON_REF, CANON_ALT):
        if c in out.columns:
            out[c] = out[c].astype(str).str.upper()

    if CANON_RSID in out.columns:
        out[CANON_RSID] = out[CANON_RSID].astype(str)

    if CANON_GT in out.columns:
        out[CANON_GT] = out[CANON_GT].astype(str)

    # Optional AF coercions
    for c in (CANON_GNOMAD_AF, CANON_POPULATION_AF):
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")

    if CANON_TOTAL_POINTS in out.columns:
        out[CANON_TOTAL_POINTS] = pd.to_numeric(out[CANON_TOTAL_POINTS], errors="coerce").astype(
            "Int64"
        )

    return out
