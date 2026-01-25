from pathlib import Path
import re

CRITERIA_FILE = Path("varidex/acmg/criteria.py")

text = CRITERIA_FILE.read_text()

# ------------------------------------------------------------
# 1. Add UNCERTAIN enum value if missing
# ------------------------------------------------------------

if "UNCERTAIN = " not in text:
    text = re.sub(
        r"(class\s+PathogenicityClass\(Enum\):)",
        r"\1\n    UNCERTAIN = \"Uncertain Significance\"",
        text,
        count=1,
    )

# ------------------------------------------------------------
# 2. Patch ACMGEvidenceSet.__init__
# ------------------------------------------------------------

if "CRITERIA_MAP =" not in text:
    injection = """
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
"""
    text += injection

# ------------------------------------------------------------
# 3. Replace __init__ to accept per-criterion flags
# ------------------------------------------------------------

if "patched_init" not in text:
    text += """
# --- Compatibility init (ACMG per-criterion flags) ---

_original_init = ACMGEvidenceSet.__init__

def _patched_init(self, *args, **kwargs):
    grouped = {}
    for k in list(kwargs):
        if k in CRITERIA_MAP and kwargs[k]:
            grouped.setdefault(CRITERIA_MAP[k], 0)
            grouped[CRITERIA_MAP[k]] += 1
            kwargs.pop(k)

    _original_init(self, *args, **kwargs)

    for g, v in grouped.items():
        setattr(self, g, getattr(self, g, 0) + v)

ACMGEvidenceSet.__init__ = _patched_init
"""

# ------------------------------------------------------------
# 4. Add per-criterion properties
# ------------------------------------------------------------

if "def _criterion_property" not in text:
    text += """
def _criterion_property(group):
    return property(lambda self: getattr(self, group, 0) > 0)

for _crit, _grp in CRITERIA_MAP.items():
    if not hasattr(ACMGEvidenceSet, _crit):
        setattr(ACMGEvidenceSet, _crit, _criterion_property(_grp))
"""

CRITERIA_FILE.write_text(text)

print("✅ varidex/acmg/criteria.py patched successfully")
