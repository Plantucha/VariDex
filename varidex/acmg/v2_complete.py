# varidex/acmg/v2_complete.py
class ACMG28Classifier:
    def __init__(self):
        self.revel = pd.read_table("data/external/acmg_v2/revel.tsv")
        self.uniprot = parse_uniprot("data/external/acmg_v2/uniprot_sprot.xml.gz")

    def pm1(self, df):
        """PM1: Hotspot/functional domain"""
        return df.apply(
            lambda row: any(
                d.contains(row["position"]) for d in self.uniprot[row["gene"]]
            ),
            axis=1,
        )

    def pp3_bp4(self, df):
        """PP3: REVEL>0.5, BP4: REVEL<0.5"""
        revel_scores = self.revel.set_index("rsid").revel_score
        df["PP3"] = revel_scores[df.rsid].fillna(0) > 0.5
        df["BP4"] = revel_scores[df.rsid].fillna(0) < 0.5
        return df

    # Add 13 more methods...
