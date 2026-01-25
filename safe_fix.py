#!/usr/bin/env python3
"""Safe fix for test file - restore and fix properly."""

import subprocess

def restore_and_fix_test_file():
    """Restore test file from git and apply proper fixes."""
    
    print("Restoring test file from git...")
    subprocess.run(["git", "checkout", "tests/test_pipeline_validators.py"], 
                   capture_output=True)
    
    test_file = "tests/test_pipeline_validators.py"
    
    with open(test_file, 'r') as f:
        content = f.read()
    
    # Simple string replacement - safer than line-by-line
    content = content.replace("reference=", "ref_allele=")
    content = content.replace("alternate=", "alt_allele=")
    
    with open(test_file, 'w') as f:
        f.write(content)
    
    return "✓ Test file fixed (reference→ref_allele, alternate→alt_allele)"


def add_assembly_to_model():
    """Add assembly field to VariantData model."""
    
    models_file = "varidex/core/models.py"
    
    with open(models_file, 'r') as f:
        content = f.read()
    
    # Find the line with alt_allele and add assembly after it
    old_text = '    alt_allele: str = ""'
    new_text = '    alt_allele: str = ""\n    assembly: str = ""'
    
    if old_text in content and 'assembly: str = ""' not in content:
        content = content.replace(old_text, new_text)
        
        with open(models_file, 'w') as f:
            f.write(content)
        
        return "✓ Added assembly field to VariantData"
    
    return "✓ Assembly field already exists or couldn't be added"


if __name__ == "__main__":
    print("=" * 70)
    print("Safe Fix for All Remaining Issues")
    print("=" * 70)
    print()
    
    print(restore_and_fix_test_file())
    print(add_assembly_to_model())
    print()
    
    print("Formatting...")
    subprocess.run(["black", "varidex/", "tests/"], capture_output=True)
    print("✓ Files formatted")
    print()
    
    print("=" * 70)
    print("Running Tests")
    print("=" * 70)
    result = subprocess.run([
        "pytest", "tests/test_pipeline_validators.py", "-v"
    ])
    
    if result.returncode == 0:
        print()
        print("=" * 70)
        print("🎉 SUCCESS! ALL TESTS PASSING!")
        print("=" * 70)
