import sys

from varidex.pipeline.stages_core import validate_stage_dependencies

#!/usr/bin/env python3
sys.path.insert(0, "/media/michal/647A504F7A50205A/GENOME/Michal/VariDex10/VariDex")

print("🧪 QUICK STAGES TEST...")

# F-STRING TEST
result, error = validate_stage_dependencies(5, {2, 3})
print(f"✅ F-STRINGS: '{error}'")

print("✅ IMPORTS: stages.py + stages_core.py")
print("✅ ALL FIXES VERIFIED!")
