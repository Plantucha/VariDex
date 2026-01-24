#!/usr/bin/env python3

with open("varidex/exceptions.py", 'r') as f:
    lines = f.readlines()

# Find line 169 (DataProcessingError) and add ProcessingError after it
for i, line in enumerate(lines):
    if i == 168 and "DataProcessingError = DataIntegrityError" in line:
        # Add ProcessingError on the next line
        if i+1 < len(lines) and "ProcessingError =" not in lines[i+1]:
            lines.insert(i+1, "ProcessingError = DataIntegrityError  # Generic alias\n")
            print(f"✓ Inserted ProcessingError at line {i+2}")
            break

with open("varidex/exceptions.py", 'w') as f:
    f.writelines(lines)

# Add validate_vcf_file
with open("varidex/pipeline/validators.py", 'r') as f:
    content = f.read()

if "def validate_vcf_file" not in content:
    code = '''

def validate_vcf_file(filepath: str) -> bool:
    """
    Validate VCF file exists and is readable.
    
    Args:
        filepath: Path to VCF file
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If invalid
    """
    from pathlib import Path
    from varidex.exceptions import ValidationError
    
    path = Path(filepath)
    
    if not path.exists():
        raise ValidationError(f"VCF file not found: {filepath}")
    
    if not path.is_file():
        raise ValidationError(f"Not a file: {filepath}")
    
    if not path.suffix.lower() in ['.vcf', '.vcf.gz']:
        raise ValidationError(f"Not a VCF file: {filepath}")
    
    return True
'''
    
    content += code
    with open("varidex/pipeline/validators.py", 'w') as f:
        f.write(content)
    print("✓ Added validate_vcf_file")

