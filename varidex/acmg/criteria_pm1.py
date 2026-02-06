"""PM1: Located in mutational hot spot and/or critical functional domain
HYBRID: Exact protein domain matching (if HGVS.p available) + gene-level fallback
"""
import gzip
import re
import xml.etree.ElementTree as ET
from pathlib import Path
import pandas as pd
import pickle


class PM1Classifier:
    def __init__(self, uniprot_path="uniprot/uniprot_sprot.xml.gz"):
        self.domains = self._load_uniprot_domains(uniprot_path)

    def _load_uniprot_domains(self, path):
        """Parse UniProt XML for functional domains (cached)"""
        cache_path = Path(path).with_suffix(".pkl")

        if cache_path.exists():
            print(f"PM1: Loading cached domains from {cache_path.name}...")
            with open(cache_path, "rb") as f:
                domains = pickle.load(f)
            print(f"PM1: ✓ Loaded {len(domains):,} genes (cached, instant)")
            return domains

        path_obj = Path(path)
        if not path_obj.exists():
            print(f"PM1: UniProt file not found at {path}, skipping")
            return {}

        print(f"PM1: Parsing UniProt SwissProt (~3 min first run)...")
        print(f"PM1: Decompressing {path_obj.name}...")

        domains = {}

        with gzip.open(path, "rb") as f:
            entries_processed = 0
            last_print = 0

            for event, elem in ET.iterparse(f, events=("end",)):
                if "}entry" in elem.tag:
                    entries_processed += 1

                    if entries_processed - last_print >= 10000:
                        print(f"PM1: Processed {entries_processed:,} entries...")
                        last_print = entries_processed

                    gene_name = None
                    for gene_elem in elem.iter():
                        if "}gene" in gene_elem.tag:
                            for name_elem in gene_elem.iter():
                                if "}name" in name_elem.tag and name_elem.get("type") == "primary":
                                    gene_name = name_elem.text
                                    break
                            if gene_name:
                                break

                    if gene_name:
                        for feature in elem.iter():
                            if "}feature" in feature.tag:
                                feat_type = feature.get("type")
                                if feat_type in [
                                    "domain", "region", "active site",
                                    "binding site", "DNA binding",
                                    "zinc finger region"
                                ]:
                                    for loc in feature.iter():
                                        if "}location" in loc.tag:
                                            begin_pos = None
                                            end_pos = None
                                            for pos_elem in loc.iter():
                                                if "}begin" in pos_elem.tag:
                                                    begin_pos = pos_elem.get("position")
                                                elif "}end" in pos_elem.tag:
                                                    end_pos = pos_elem.get("position")

                                            if begin_pos and end_pos:
                                                try:
                                                    start = int(begin_pos)
                                                    stop = int(end_pos)
                                                    domains.setdefault(gene_name, []).append(
                                                        (start, stop)
                                                    )
                                                except (ValueError, TypeError):
                                                    pass

                    elem.clear()

        total_domains = sum(len(dl) for dl in domains.values())
        print(f"PM1: ✓ Parsed {entries_processed:,} entries")
        print(f"PM1: ✓ Found {len(domains):,} genes with {total_domains:,} domains")

        print(f"PM1: Saving cache to {cache_path.name}...")
        with open(cache_path, "wb") as f:
            pickle.dump(domains, f)
        print("PM1: ✓ Cache saved (future runs instant)")

        return domains

    def _extract_protein_position(self, molecular_consequence):
        """Extract protein position from HGVS.p notation

        Examples:
          p.Arg1443Ter -> 1443
          p.Val600Glu -> 600
          p.Leu858Arg -> 858
          NP_000059.2:p.Arg1443Ter -> 1443
        """
        if pd.isna(molecular_consequence):
            return None

        cons_str = str(molecular_consequence)

        # Match p.AAAnnnnBBB pattern (where AAA=3-letter AA, nnnn=position, BBB=3-letter AA)
        # Also handles p.AAA* (stop), p.AAA= (synonymous)
        patterns = [
            r'p\.[A-Z][a-z]{2}(\d+)',  # p.Arg1443Ter
            r'p\.([A-Z][a-z]{2})(\d+)',  # Alternative
        ]

        for pattern in patterns:
            match = re.search(pattern, cons_str)
            if match:
                try:
                    # Extract the numeric group
                    pos_str = match.group(1) if match.lastindex == 1 else match.group(2)
                    return int(pos_str)
                except (ValueError, IndexError):
                    continue

        return None

    def apply_pm1(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply PM1 to variants (HYBRID approach)

        Strategy:
        1. EXACT: If molecular_consequence contains HGVS.p (e.g., p.Arg1443Ter),
           extract protein position and check against UniProt domains
        2. FALLBACK: If no protein position, flag missense/inframe in genes with domains
        """
        df["PM1"] = False
        df["PM1_method"] = None

        genes_with_domains = set(self.domains.keys())

        print(f"PM1: {len(genes_with_domains):,} genes have functional domains")

        # Try exact protein domain matching first
        exact_count = 0
        for idx, row in df.iterrows():
            gene = row.get("gene")
            cons = row.get("molecular_consequence")

            if pd.isna(gene) or gene not in self.domains:
                continue

            # Try to extract protein position
            protein_pos = self._extract_protein_position(cons)

            if protein_pos is not None:
                # Check if position falls in any domain
                for domain_start, domain_end in self.domains[gene]:
                    if domain_start <= protein_pos <= domain_end:
                        df.at[idx, "PM1"] = True
                        df.at[idx, "PM1_method"] = "exact_domain"
                        exact_count += 1
                        break

        print(f"PM1: EXACT protein domain matches: {exact_count}")

        # Fallback: gene-level for variants without protein positions
        no_protein_pos = df[df.PM1_method.isna()].index

        missense_mask = df.loc[no_protein_pos, "molecular_consequence"].str.contains(
            "missense|inframe", na=False, case=False
        )

        gene_mask = df.loc[no_protein_pos, "gene"].isin(genes_with_domains)

        fallback_mask = no_protein_pos[missense_mask & gene_mask]
        df.loc[fallback_mask, "PM1"] = True
        df.loc[fallback_mask, "PM1_method"] = "gene_level"

        fallback_count = len(fallback_mask)
        print(f"PM1: FALLBACK gene-level matches: {fallback_count}")

        pm1_count = int(df["PM1"].sum())
        pm1_pct = pm1_count / len(df) * 100

        print(f"⭐ PM1: {pm1_count} variants in critical domains ({pm1_pct:.1f}%)")
        print(f"   {exact_count} exact protein domain, {fallback_count} gene-level")

        if pm1_count > 0:
            pm1_genes = df[df.PM1 == True].gene.value_counts().head(5)
            print(f"   Top: {', '.join([f'{g}({c})' for g, c in pm1_genes.items()])}")

        # Drop temporary column
        df = df.drop(columns=["PM1_method"], errors="ignore")

        return df
