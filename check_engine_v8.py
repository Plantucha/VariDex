#!/usr/bin/env python3
"""
Examine engine_v8.py to see what's already implemented
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("=" * 80)
print("EXAMINING engine_v8.py - Most Advanced ACMG Engine")
print("=" * 80)

# Read the file
engine_v8_path = Path("varidex/core/classifier/engine_v8.py")

if not engine_v8_path.exists():
    print("❌ engine_v8.py not found!")
    sys.exit(1)

content = engine_v8_path.read_text()
lines = content.split("\n")

# Extract header info
print("\n📄 File Info:")
for i, line in enumerate(lines[:50]):
    if line.strip().startswith('"""') or line.strip().startswith("'''"):
        continue
    if "Version" in line or "version" in line.lower():
        print(f"  {line.strip()}")
    if "Evidence" in line and "codes" in line.lower():
        print(f"  {line.strip()}")

# Find all ACMG evidence codes mentioned
print("\n🧬 ACMG Evidence Codes Found:")
import re

all_codes = set()
for line in lines:
    matches = re.findall(
        r"\b(PVS1|PS[1-4]|PM[1-6]|PP[1-5]|BA1|BS[1-4]|BP[1-7])\b", line
    )
    all_codes.update(matches)

pathogenic = [c for c in sorted(all_codes) if c.startswith("P")]
benign = [c for c in sorted(all_codes) if c.startswith("B")]

print(f"  Pathogenic: {', '.join(pathogenic)} ({len(pathogenic)} codes)")
print(f"  Benign: {', '.join(benign)} ({len(benign)} codes)")
print(f"  TOTAL: {len(all_codes)}/28 codes")

# Find class definitions
print("\n📦 Classes:")
for line in lines:
    if line.strip().startswith("class "):
        print(f"  • {line.strip()}")

# Find key methods
print("\n⚙️  Key Methods:")
in_class = False
for i, line in enumerate(lines):
    if "class ACMG" in line:
        in_class = True
    if in_class and line.strip().startswith("def "):
        method_name = line.strip().split("(")[0].replace("def ", "")
        if not method_name.startswith("_"):
            print(f"  • {method_name}")
        if method_name == "classify_variant":
            # Show what it returns
            for j in range(i, min(i + 20, len(lines))):
                if "return" in lines[j]:
                    print(f"    Returns: {lines[j].strip()}")
                    break

# Check dependencies
print("\n📚 External Dependencies:")
dependencies = {
    "gnomAD": False,
    "SpliceAI": False,
    "dbNSFP": False,
    "ClinVar": False,
}

for line in lines[:100]:
    if "gnomad" in line.lower():
        dependencies["gnomAD"] = True
    if "splice" in line.lower():
        dependencies["SpliceAI"] = True
    if "dbnsfp" in line.lower():
        dependencies["dbNSFP"] = True
    if "clinvar" in line.lower() and "import" not in line.lower():
        dependencies["ClinVar"] = True

for dep, found in dependencies.items():
    status = "✅" if found else "❌"
    print(f"  {status} {dep}")

# Check what data it needs
print("\n📊 Required Data Fields:")
data_fields = set()
for line in lines:
    # Look for variant['field'] or variant.field patterns
    matches = re.findall(r"variant\['(\w+)'\]", line)
    data_fields.update(matches)
    matches = re.findall(r"variant\.(\w+)", line)
    data_fields.update(matches)

for field in sorted(data_fields)[:20]:
    print(f"  • {field}")

# Show docstring
print("\n📖 Docstring:")
in_docstring = False
docstring_lines = []
for line in lines[:100]:
    if '"""' in line or "'''" in line:
        if in_docstring:
            break
        in_docstring = True
        continue
    if in_docstring:
        docstring_lines.append(line)

for line in docstring_lines[:30]:
    print(line)

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

# Try to import it
print("\n🧪 Testing Import:")
try:
    from varidex.core.classifier.engine_v8 import ACMGClassifierV8

    print("✅ Successfully imported ACMGClassifierV8")

    # Check what it can do
    import inspect

    sig = inspect.signature(ACMGClassifierV8.__init__)
    print(f"\n  __init__ signature: {sig}")

    # Try to instantiate
    try:
        classifier = ACMGClassifierV8()
        print(f"  ✅ Instantiated successfully")
        print(f"  Type: {type(classifier)}")
    except Exception as e:
        print(f"  ⚠️  Cannot instantiate: {e}")

except ImportError as e:
    print(f"❌ Import failed: {e}")
