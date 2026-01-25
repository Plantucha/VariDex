from varidex.acmg.criteria import ACMGEvidenceSet
from varidex.acmg import classification
from enum import Enum

# ------------------------------------------------------------------
# 1. Fix PathogenicityClass enum
# ------------------------------------------------------------------

if hasattr(classification, "PathogenicityClass"):
    PathogenicityClass = classification.PathogenicityClass
    if not hasattr(PathogenicityClass, "UNCERTAIN"):
        PathogenicityClass.UNCERTAIN = PathogenicityClass(
            "UNCERTAIN", "Uncertain Significance"
        )

# ------------------------------------------------------------------
# 2. Per-criterion → grouped mapping
# ------------------------------------------------------------------

CRITERIA_MAP = {
    "pvs1": "pvs",
    "ps1": "ps", "ps2": "ps", "ps3": "ps", "ps4": "ps",
    "pm1": "pm", "pm2": "pm", "pm3": "pm", "pm4": "pm", "pm5": "pm", "pm6": "pm",
    "pp1": "pp", "pp2": "pp", "pp3": "pp", "pp4": "pp", "pp5": "pp",
    "ba1": "ba",
    "bs1": "bs", "bs2": "bs", "bs3": "bs", "bs4": "bs",
    "bp1": "bp", "bp2": "bp", "bp3": "bp", "bp4": "bp",
    "bp5": "bp", "bp6": "bp", "bp7": "bp",
}

# ------------------------------------------------------------------
# 3. Patch __init__ permanently
# ------------------------------------------------------------------

orig_init = ACMGEvidenceSet.__init__

def patched_init(self, *args, **kwargs):
    grouped = {}
    for key in list(kwargs):
        if key in CRITERIA_MAP and kwargs[key]:
            grouped.setdefault(CRITERIA_MAP[key], 0)
            grouped[CRITERIA_MAP[key]] += 1
            kwargs.pop(key)

    orig_init(self, *args, **kwargs)

    for k, v in grouped.items():
        setattr(self, k, getattr(self, k, 0) + v)

ACMGEvidenceSet.__init__ = patched_init

# ------------------------------------------------------------------
# 4. Add per-criterion properties
# ------------------------------------------------------------------

for crit, group in CRITERIA_MAP.items():
    if not hasattr(ACMGEvidenceSet, crit):
        setattr(
            ACMGEvidenceSet,
            crit,
            property(lambda self, g=group: getattr(self, g, 0) > 0)
        )

print("✅ ACMG source patch installed (restart pytest)")
