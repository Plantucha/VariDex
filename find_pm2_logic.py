#!/usr/bin/env python3
"""
Find where PM2 is actually implemented
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 80)
print("SEARCHING FOR PM2 IMPLEMENTATION")
print("=" * 80)

# Check all classifier files
files = [
    'varidex/core/classifier/engine.py',
    'varidex/core/classifier/evidence_assignment.py',
    'varidex/core/classifier/acmg_evidence_pathogenic.py',
    'varidex/acmg/frequency_criteria.py',
]

for filepath in files:
    path = Path(filepath)
    if not path.exists():
        continue
    
    print(f"\n📄 {filepath}:")
    content = path.read_text()
    lines = content.split('\n')
    
    pm2_found = False
    for i, line in enumerate(lines):
        if 'PM2' in line or 'pm2' in line:
            pm2_found = True
            # Show context
            start = max(0, i-2)
            end = min(len(lines), i+5)
            if i-2 >= 0:
                print(f"  ...")
            for j in range(start, end):
                marker = ">>>" if j == i else "   "
                print(f"  {marker} {j+1}: {lines[j]}")
            print()
    
    if not pm2_found:
        print("  (no PM2 references)")

# Check acmg_evidence_pathogenic for check_pm2 method
print("\n" + "=" * 80)
print("CHECKING acmg_evidence_pathogenic.py")
print("=" * 80)

path = Path("varidex/core/classifier/acmg_evidence_pathogenic.py")
if path.exists():
    import re
    content = path.read_text()
    
    # Find check_pm2 method
    pm2_match = re.search(r'def check_pm2.*?(?=\n    def |\nclass |\Z)', content, re.DOTALL)
    if pm2_match:
        print("\n✅ Found check_pm2 method:")
        print(pm2_match.group(0)[:500])
    else:
        print("\n❌ No check_pm2 method found")
        
        # Check what methods exist
        methods = re.findall(r'def (check_\w+)', content)
        print(f"\nAvailable check methods: {', '.join(methods)}")

