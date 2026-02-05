#!/usr/bin/env python3
"""
Add 13-code ACMG to existing orchestrator
"""

import sys
from pathlib import Path

orchestrator_file = Path("varidex/pipeline/orchestrator.py")

if not orchestrator_file.exists():
    print(f"❌ Orchestrator not found: {orchestrator_file}")
    print("\nLooking for orchestrator files...")
    for f in Path("varidex/pipeline").glob("*.py"):
        print(f"  {f.name}")
    sys.exit(1)

print(f"✅ Found orchestrator: {orchestrator_file}")
print("\nReading current orchestrator...")

with open(orchestrator_file, "r") as f:
    content = f.read()

print("Current orchestrator has these imports:")
for line in content.split("\n")[:30]:
    if "import" in line:
        print(f"  {line}")
