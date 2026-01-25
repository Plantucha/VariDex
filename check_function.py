#!/usr/bin/env python3
"""Check if validate_variant has the raise logic."""

# Read the validators file
with open("varidex/pipeline/validators.py", 'r') as f:
    content = f.read()

# Check if it has raise_on_error logic
if "raise_on_error=True" in content or "if raise_on_error:" in content:
    print("✓ Function has raise_on_error logic")
    
    # Count how many times
    count = content.count("if raise_on_error:")
    print(f"  Found {count} raise_on_error checks")
else:
    print("✗ Function replacement did NOT work!")
    print("  The validate_variant function still has old code")
    print()
    print("Let me extract what's actually there...")
    
    # Find the validate_variant function
    start = content.find("def validate_variant(")
    if start != -1:
        # Find the next function
        next_func = content.find("\ndef ", start + 10)
        if next_func != -1:
            func_code = content[start:next_func]
            print()
            print("=" * 70)
            print("Current validate_variant function:")
            print("=" * 70)
            print(func_code[:800])  # First 800 chars
            print("...")
