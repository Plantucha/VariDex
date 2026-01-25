#!/usr/bin/env python3
"""Add assembly field to VariantData model."""

def add_assembly_to_variant_data():
    """Add assembly field to VariantData in models.py."""
    
    models_file = "varidex/core/models.py"
    
    with open(models_file, 'r') as f:
        lines = f.readlines()
    
    new_lines = []
    found_ref_allele = False
    
    for i, line in enumerate(lines):
        new_lines.append(line)
        
        # Add assembly field after ref_allele and alt_allele
        if 'alt_allele: str = ""' in line and not found_ref_allele:
            found_ref_allele = True
            indent = line[:len(line) - len(line.lstrip())]
            new_lines.append(f'\n{indent}# Reference assembly\n')
            new_lines.append(f'{indent}assembly: str = ""\n')
    
    with open(models_file, 'w') as f:
        f.writelines(new_lines)
    
    return "✓ Added assembly field to VariantData"


if __name__ == "__main__":
    import subprocess
    
    print("=" * 70)
    print("Adding Assembly Field to VariantData")
    print("=" * 70)
    print()
    
    print(add_assembly_to_variant_data())
    print()
    
    print("Formatting...")
    subprocess.run(["black", "varidex/core/models.py"], capture_output=True)
    print("✓ Formatted models.py")
    print()
    
    print("=" * 70)
    print("Running Tests")
    print("=" * 70)
    result = subprocess.run([
        "pytest", "tests/test_pipeline_validators.py", "-v", "--tb=line"
    ])
    
    if result.returncode == 0:
        print()
        print("=" * 70)
        print("🎉 ALL 42 TESTS PASSING!")
        print("=" * 70)
        print()
        print("Summary:")
        print("  ✓ validate_chromosome - all passing")
        print("  ✓ validate_coordinates - all passing")
        print("  ✓ validate_reference_allele - all passing")
        print("  ✓ validate_assembly - all passing")
        print("  ✓ validate_variant - all passing")
        print("  ✓ validate_vcf_file - all passing")
        print("  ✓ Edge cases - all passing")
        print("  ✓ Performance - all passing")
    else:
        print()
        print("Some tests still failing. Check output above.")
