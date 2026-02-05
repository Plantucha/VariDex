#!/usr/bin/env python3
"""
Show ACMGClassifier configuration and how to enable PM2
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from varidex.core.classifier.config import ACMGConfig

print("=" * 80)
print("ACMGClassifier CONFIGURATION")
print("=" * 80)

# Default config
config = ACMGConfig()

print("\n📋 Default Feature Flags:")
print(f"  enable_pvs1: {config.enable_pvs1}")
print(f"  enable_pm2:  {config.enable_pm2}  ⚠️ DISABLED!")
print(f"  enable_bp7:  {config.enable_bp7}")

print("\n💡 To enable PM2:")
print("""
config = ACMGConfig(enable_pm2=True)
classifier = ACMGClassifier(config=config)

# Then the classifier will check gnomAD frequency for PM2
""")

print("\n" + "=" * 80)
print("CODES AVAILABLE WITH CURRENT DATA")
print("=" * 80)

available_now = {
    "PVS1": "LOF variant (uses LOF_GENES list)",
    "PM2": "Rare variant (needs gnomAD - WE HAVE THIS!)",
    "PM4": "Protein length change (from VCF consequence)",
    "PP2": "Missense in constrained gene (uses MISSENSE_RARE_GENES)",
    "BA1": "Very common >5% (needs gnomAD - WE HAVE THIS!)",
    "BS1": "Common 1-5% (needs gnomAD - WE HAVE THIS!)",
    "BP1": "Missense where LOF is mechanism",
    "BP3": "In-frame indel in repeat region",
}

print("\n✅ Can enable NOW (with existing data):")
for code, desc in available_now.items():
    have_data = "WE HAVE THIS" in desc
    marker = "✅" if have_data or "list" in desc else "⚠️"
    print(f"  {marker} {code}: {desc}")

print("\n" + "=" * 80)
print("INTEGRATION PLAN")
print("=" * 80)
print("""
Step 1: Update pipeline to use ACMGClassifier instead of frequency function
Step 2: Enable PM2 in config (we have gnomAD!)
Step 3: Benefit: 8 criteria instead of 3!

Codes we'd get:
  Current:  PM2, BA1, BS1 (3 codes)
  With ACMGClassifier: PVS1, PM2, PM4, PP2, BA1, BS1, BP1, BP3 (8 codes)
  
Improvement: +5 new evidence codes for FREE!
""")
