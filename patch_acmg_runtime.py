"""
Runtime ACMG compatibility patch
- Adds per-criterion ACMG flags (pvs1, ps1, pm1, etc.)
- Preserves existing grouped counters (pvs, ps, pm, ...)
- Adds missing PathogenicityClass.UNCERTAIN
"""

from enum import Enum
import inspect

# ---- Locate existing ACMG module ----
from varidex.acmg import criteria as acmg_criteria_mod

ACMG = acmg_criteria_mod.ACMGEvidenceSet

# ---- Patch Enum safely ----
try:
    from varidex.acmg.classification import PathogenicityClass
except ImportError:
    PathogenicityClass = None

if PathogenicityClass and not hasattr(PathogenicityClass, "UNCERTAIN"):
    PathogenicityClass.UNCERTAIN = PathogenicityClass(
        "UNCERTAIN", "Uncertain Significance"
    )

# ---- Per-criterion map ----
CRITERIA_MAP = {
    "pvs1": "pvs",
    "ps1": "ps", "ps2": "ps", "ps3": "ps", "ps4": "ps",
    "pm1": "pm", "pm2": "pm", "pm3": "pm", "pm4": "pm", "pm5": "pm", "pm6": "pm",
    "pp1": "pp", "pp2": "pp", "pp3": "pp", "pp4": "pp", "pp5": "pp",
    "ba1": "ba",
    "bs1": "bs", "bs2": "bs", "bs3": "bs", "bs4": "bs",
    "bp1": "bp", "bp2": "bp", "bp3": "bp", "bp4": "bp", "bp5": "bp", "bp6": "bp", "bp7": "bp",
}

# ---- Patch __init__ to accept per-criterion kwargs ----
orig_init = ACMG.__init__

def patched_init(self, *args, **kwargs):
    grouped = {}
    for key, value in list(kwargs.items()):
        if key in CRITERIA_MAP and value:
            grouped.setdefault(CRITERIA_MAP[key], 0)
            grouped[CRITERIA_MAP[key]] += 1
            kwargs.pop(key)

    orig_init(self, *args, **kwargs)

    for k, v in grouped.items():
        setattr(self, k, getattr(self, k, 0) + v)

ACMG.__init__ = patched_init

# ---- Inject per-criterion properties ----
for crit, group in CRITERIA_MAP.items():
    if hasattr(ACMG, crit):
        continue

    setattr(
        ACMG,
        crit,
        property(lambda self, g=group: getattr(self, g, 0) > 0)
    )

print("✅ ACMG runtime compatibility patch applied")
