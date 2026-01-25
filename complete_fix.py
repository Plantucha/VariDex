#!/usr/bin/env python3
"""Complete fix for all remaining test failures."""

import subprocess
import re

def fix_validators_chromosome_length():
    """Update chr1 length to 249250621."""
    validators_file = "varidex/pipeline/validators.py"
    
    with open(validators_file, 'r') as f:
        content = f.read()
    
    content = content.replace('"1": 248956422', '"1": 249250621')
    
    with open(validators_file, 'w') as f:
        f.write(content)
    
    return "✓ Chr1 length: 248956422 → 249250621"


def fix_test_parameters():
    """Fix test file to use correct parameter names and add required params."""
    test_file = "tests/test_pipeline_validators.py"
    
    with open(test_file, 'r') as f:
        lines = f.readlines()
    
    new_lines = []
    in_genomic_variant = False
    variant_lines = []
    indent = ""
    
    for line in lines:
        # Detect GenomicVariant creation
        if "GenomicVariant(" in line:
            in_genomic_variant = True
            variant_lines = [line]
            indent = line[:len(line) - len(line.lstrip())]
            continue
        
        if in_genomic_variant:
            variant_lines.append(line)
            
            # End of GenomicVariant call
            if ")" in line and not line.strip().endswith(","):
                # Process the variant call
                variant_str = "".join(variant_lines)
                
                # Fix parameter names
                variant_str = variant_str.replace("reference=", "ref_allele=")
                variant_str = variant_str.replace("alternate=", "alt_allele=")
                
                # Add required parameters if missing
                if "rsid=" not in variant_str:
                    # Insert rsid after GenomicVariant(
                    variant_str = variant_str.replace(
                        "GenomicVariant(",
                        'GenomicVariant(\n' + indent + '    rsid="test_rsid",'
                    )
                
                if "genotype=" not in variant_str:
                    # Insert genotype after rsid
                    variant_str = variant_str.replace(
                        'rsid="test_rsid",',
                        'rsid="test_rsid",\n' + indent + '    genotype="A/T",'
                    )
                
                new_lines.append(variant_str)
                in_genomic_variant = False
                variant_lines = []
                continue
        
        new_lines.append(line)
    
    with open(test_file, 'w') as f:
        f.writelines(new_lines)
    
    return "✓ Fixed test parameters (reference→ref_allele, alternate→alt_allele, added rsid/genotype)"


if __name__ == "__main__":
    print("=" * 70)
    print("Complete Fix for Remaining Test Failures")
    print("=" * 70)
    print()
    
    print(fix_validators_chromosome_length())
    print(fix_test_parameters())
    print()
    
    print("Formatting...")
    subprocess.run(["black", "varidex/pipeline/validators.py", "tests/test_pipeline_validators.py"],
                   capture_output=True)
    print("✓ Files formatted with Black")
    print()
    
    print("=" * 70)
    print("Running Tests")
    print("=" * 70)
    subprocess.run(["pytest", "tests/test_pipeline_validators.py", "-v"])
