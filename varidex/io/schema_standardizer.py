"""VariDex Schema Standardizer - Eliminates naming inconsistencies"""

import pandas as pd
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)


class SchemaStandardizer:
    """Standardizes column naming across all VariDex DataFrames."""

    CANONICAL_SCHEMA = {
        "coord_key": "coord_key",
        "rsid": "rsid",
        "chromosome": "chromosome",
        "position": "position",
        "ref_allele": "ref_allele",
        "alt_allele": "alt_allele",
        "gene": "gene",
        "clinical_sig": "clinical_sig",
        "review_status": "review_status",
        "variant_type": "variant_type",
        "molecular_consequence": "molecular_consequence",
        "genotype": "genotype",
        "normalized_genotype": "normalized_genotype",
        "zygosity": "zygosity",
        "acmg_classification": "acmg_classification",
    }

    COLUMN_ALIASES = {
        "coord_key": ["coordkey", "coordinate_key", "coordinatekey"],
        "rsid": ["rs_id", "rsID", "RS", "dbSNP"],
        "chromosome": ["chr", "chrom", "CHROM", "Chromosome"],
        "position": ["pos", "POS", "Position", "PositionVCF", "Start"],
        "ref_allele": ["ref", "REF", "reference", "refallele"],
        "alt_allele": ["alt", "ALT", "alternate", "altallele"],
        "gene": ["Gene", "gene_symbol", "GeneSymbol", "Genes"],
        "clinical_sig": ["clinicalsig", "ClinicalSignificance", "clinsig"],
        "review_status": ["reviewstatus", "ReviewStatus"],
        "variant_type": ["varianttype", "VariantType", "Type"],
        "molecular_consequence": ["molecularconsequence", "consequence"],
        "genotype": ["Genotype", "GT"],
        "normalized_genotype": ["normalizedgenotype", "norm_genotype"],
        "zygosity": ["Zygosity"],
        "acmg_classification": ["acmgclassification", "classification", "ACMG"],
    }

    @classmethod
    def standardize_dataframe(cls, df: pd.DataFrame, source: str = "unknown") -> pd.DataFrame:
        """Standardize all column names to canonical schema."""
        if df is None or len(df) == 0:
            logger.warning(f"Empty DataFrame from {source}")
            return df

        rename_map = {}
        for col in df.columns:
            col_lower = col.lower().replace("_", "").replace("-", "")
            for canonical, aliases in cls.COLUMN_ALIASES.items():
                alias_patterns = [a.lower().replace("_", "").replace("-", "") for a in aliases]
                if col_lower in alias_patterns:
                    rename_map[col] = canonical
                    break

        if rename_map:
            df = df.rename(columns=rename_map)
            logger.info(f"[{source}] Standardized {len(rename_map)} columns")

        return df

    @classmethod
    def validate_schema(cls, df: pd.DataFrame, required_cols: List[str]) -> Tuple[bool, List[str]]:
        """Validate DataFrame has required canonical columns."""
        if df is None:
            return False, required_cols
        missing = [col for col in required_cols if col not in df.columns]
        return len(missing) == 0, missing
