#!/usr/bin/env python3
"""Check what the failing tests actually do."""

import subprocess

# Show the failing test lines
print("=" * 70)
print("Examining Failing Tests")
print("=" * 70)
print()

print("Test 1 (line 179 - invalid chromosome):")
subprocess.run(["sed", "-n", "172,181p", "tests/test_pipeline_validators.py"])

print("\nTest 2 (line 213 - invalid assembly):")
subprocess.run(["sed", "-n", "206,215p", "tests/test_pipeline_validators.py"])

print("\nTest 3 (line 313 - missing fields):")
subprocess.run(["sed", "-n", "306,315p", "tests/test_pipeline_validators.py"])

print("\nTest 4 (line 345 - performance):")
subprocess.run(["sed", "-n", "327,346p", "tests/test_pipeline_validators.py"])
