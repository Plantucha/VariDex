#!/usr/bin/env python3
"""
Check what data/services the full ACMG implementation needs
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("=" * 80)
print("FULL ACMG DATA REQUIREMENTS")
print("=" * 80)

# Read the full implementation
acmg_full = Path("varidex/core/classifier/acmg_evidence_full.py").read_text()

print("\n📋 Required Data/Services:\n")

requirements = {
    "PVS1": "Loss-of-function intolerant genes list",
    "PS1": "Known pathogenic variants database",
    "PS2": "De novo status (parental testing)",
    "PS3": "Functional study results",
    "PS4": "Case-control prevalence data",
    "PM1": "Mutational hotspots / functional domains",
    "PM2": "gnomAD population frequency ✅ HAVE",
    "PM3": "Trans variant detection (parental testing)",
    "PM4": "Protein length change detection",
    "PM5": "Known pathogenic at same position",
    "PM6": "De novo assumption (no parental data)",
    "PP1": "Segregation data (family studies)",
    "PP2": "Missense-constrained genes",
    "PP3": "Computational predictions (SIFT, PolyPhen, CADD)",
    "PP4": "Patient phenotype specificity",
    "PP5": "Reputable source pathogenic calls",
    "BA1": "gnomAD >5% frequency ✅ HAVE",
    "BS1": "gnomAD >1% frequency ✅ HAVE",
    "BS2": "Observed in healthy adults",
    "BS3": "Functional studies show benign",
    "BS4": "Lack of segregation",
    "BP1": "Missense in LOF gene",
    "BP2": "Trans with dominant pathogenic",
    "BP3": "In-frame indel in repeat region",
    "BP4": "Computational predictions (benign)",
    "BP5": "Alternate molecular basis",
    "BP6": "Reputable source benign calls",
    "BP7": "Silent variant (no splice impact) ✅ HAVE",
}

for code, req in requirements.items():
    have = "✅ HAVE" in req
    status = "✅" if have else "❌"
    print(f"{status} {code}: {req}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

have_count = sum(1 for req in requirements.values() if "✅ HAVE" in req)
need_count = len(requirements) - have_count

print(f"""
Currently Available: {have_count}/28 criteria
  ✅ PM2 - gnomAD frequency
  ✅ BA1 - Very common (>5%)
  ✅ BS1 - Common (>1%)  
  ✅ BP7 - Silent variants

Missing Data Sources: {need_count}/28 criteria
  
🎯 Easy Additions (can implement now):
  • PM4 - Protein length (from VCF consequence)
  • BP1 - Missense in LOF gene (with gene list)
  • BP3 - Indels in repeats (simple logic)
  • PP2 - Missense constraint (with gene metrics)

📊 Need External Databases:
  • PP3/BP4 - SIFT, PolyPhen, CADD scores → dbNSFP
  • PVS1 - LOF genes → pLI scores from gnomAD
  • PM1 - Domains → UniProt/Pfam
  • PS1/PM5 - Known variants → ClinVar/HGMD

👨‍👩‍👧‍👦 Need Family Data:
  • PS2, PM3, PP1, BS4 - Requires trio/family VCFs
  
🧪 Need Experimental Data:
  • PS3, BS3 - Functional studies
  • PS4 - Case-control studies
""")
