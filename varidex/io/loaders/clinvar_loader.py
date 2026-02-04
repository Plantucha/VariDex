"""ClinVar loader stub for tests."""

import pandas as pd


def load_clinvar(clinvar_path):
    return pd.DataFrame(
        {
            "chromosome": ["chr1"],
            "position": [100000],
            "reference": ["A"],
            "alternate": ["G"],
            "clinical_significance": ["Pathogenic"],
            "review_status": ["criteria provided, single submitter"],
        }
    )
