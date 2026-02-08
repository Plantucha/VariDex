"""PS1 Classifier - OPTIMIZED VERSION v2.1 with fallback

Performance improvements + defensive coding for missing protein annotations
"""

import re
import pickle
from pathlib import Path
import pandas as pd
from typing import Set, Tuple


class PS1ClassifierOptimized:
    def __init__(self, clinvar_df: pd.DataFrame):
        """Initialize with ClinVar data. Handles missing protein_change column."""
        self.clinvar_df = clinvar_df

        # Check if protein annotations available
        if "protein_change" not in clinvar_df.columns:
            print("PS1: ⚠️  No protein_change column in ClinVar - PS1 will be skipped")
            print("PS1: To enable PS1, ClinVar must include HGVS protein annotations")
            self.pathogenic_aa_changes = set()
            self.protein_data_available = False
        else:
            self.pathogenic_aa_changes = self._build_pathogenic_index()
            self.protein_data_available = True

    def _build_pathogenic_index(self) -> Set[Tuple[str, str]]:
        """Build cached index of pathogenic AA changes."""
        cache_path = Path("data/external/acmg_v2/ps1_pathogenic_cache.pkl")

        if cache_path.exists():
            print(f"PS1: Loading cached pathogenic AA changes...")
            with open(cache_path, "rb") as f:
                pathogenic_set = pickle.load(f)
            print(
                f"PS1: ✓ Loaded {len(pathogenic_set):,} pathogenic AA changes (cached)"
            )
            return pathogenic_set

        print("PS1: Building pathogenic AA change index from ClinVar...")

        # Vectorized filtering
        path_mask = self.clinvar_df["clinical_sig"].str.contains(
            "Pathogenic|Likely_pathogenic", case=False, na=False
        )

        review_mask = self.clinvar_df["review_status"].str.contains(
            "criteria_provided|reviewed_by_expert|practice_guideline",
            case=False,
            na=False,
        )

        pathogenic_df = self.clinvar_df[path_mask & review_mask].copy()

        # Extract valid protein changes
        pathogenic_set = set()
        valid_mask = (
            pathogenic_df["gene"].notna() & pathogenic_df["protein_change"].notna()
        )

        for _, row in pathogenic_df[valid_mask].iterrows():
            gene = row["gene"]
            prot = row["protein_change"]

            if prot.startswith("p."):
                prot_norm = self._normalize_protein_hgvs(prot)
                if prot_norm:
                    pathogenic_set.add((gene, prot_norm))

        # Cache for future runs
        if len(pathogenic_set) > 0:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            print(f"PS1: Saving cache to {cache_path.name}...")
            with open(cache_path, "wb") as f:
                pickle.dump(pathogenic_set, f)

        print(f"PS1: Indexed {len(pathogenic_set):,} pathogenic AA changes")
        return pathogenic_set

    def _normalize_protein_hgvs(self, hgvs: str) -> str:
        """Normalize protein HGVS to 3-letter format."""
        if not hgvs.startswith("p."):
            return ""

        # Already 3-letter: p.Arg123Gln
        match = re.match(r"p\.([A-Z][a-z]{2})(\d+)([A-Z][a-z]{2})", hgvs)
        if match:
            return hgvs

        # Convert 1-letter: p.R123Q -> p.Arg123Gln
        match = re.match(r"p\.([A-Z])(\d+)([A-Z])", hgvs)
        if match:
            ref_1, pos, alt_1 = match.groups()
            ref_3 = self._aa_1to3(ref_1)
            alt_3 = self._aa_1to3(alt_1)
            if ref_3 and alt_3:
                return f"p.{ref_3}{pos}{alt_3}"

        return ""

    def _aa_1to3(self, aa_1: str) -> str:
        """Convert 1-letter to 3-letter amino acid code."""
        aa_map = {
            "A": "Ala",
            "C": "Cys",
            "D": "Asp",
            "E": "Glu",
            "F": "Phe",
            "G": "Gly",
            "H": "His",
            "I": "Ile",
            "K": "Lys",
            "L": "Leu",
            "M": "Met",
            "N": "Asn",
            "P": "Pro",
            "Q": "Gln",
            "R": "Arg",
            "S": "Ser",
            "T": "Thr",
            "V": "Val",
            "W": "Trp",
            "Y": "Tyr",
        }
        return aa_map.get(aa_1, "")

    def apply_ps1(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply PS1 with graceful fallback if no protein data."""
        df["PS1"] = False

        if not self.protein_data_available:
            print("⭐ PS1: 0 matches (no protein annotations available)")
            return df

        if "protein_change" not in df.columns:
            print("⭐ PS1: 0 matches (no protein_change column in results)")
            return df

        # Vectorized candidate filtering
        has_gene = df["gene"].notna()
        has_protein = df["protein_change"].notna()
        is_missense = df["protein_change"].str.startswith("p.", na=False)

        candidate_mask = has_gene & has_protein & is_missense
        candidates = df[candidate_mask]

        if len(candidates) == 0:
            print("⭐ PS1: 0 exact AA matches with pathogenic variants (no candidates)")
            return df

        print(f"PS1: Checking {len(candidates):,} variants with protein changes...")

        # Apply matching
        ps1_hits = self._apply_vectorized(candidates)
        df.loc[candidate_mask, "PS1"] = ps1_hits

        ps1_count = int(df["PS1"].sum())
        ps1_pct = ps1_count / len(df) * 100

        print(
            f"⭐ PS1: {ps1_count} exact AA matches with pathogenic variants ({ps1_pct:.1f}%)"
        )

        if ps1_count > 0:
            ps1_genes = df[df["PS1"]]["gene"].value_counts().head(5)
            print(f"   Top: {', '.join([f'{g}({c})' for g, c in ps1_genes.items()])}")

        return df

    def _apply_vectorized(self, candidates: pd.DataFrame) -> pd.Series:
        """Vectorized PS1 matching."""
        result = pd.Series(False, index=candidates.index)

        for idx, row in candidates.iterrows():
            gene = row["gene"]
            prot = row["protein_change"]
            prot_norm = self._normalize_protein_hgvs(prot)

            if prot_norm and (gene, prot_norm) in self.pathogenic_aa_changes:
                result[idx] = True

        return result


# Backward compatibility
PS1Classifier = PS1ClassifierOptimized
