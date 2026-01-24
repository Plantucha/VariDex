#!/usr/bin/env python3

# Fix ProcessingError
with open("varidex/exceptions.py", 'r') as f:
    lines = f.readlines()

# Find ConfigurationError and add ProcessingError right after if not exists
modified = False
for i, line in enumerate(lines):
    if 'ConfigurationError = ValidationError' in line:
        # Check next few lines
        has_processing = any('ProcessingError =' in lines[j] for j in range(i, min(i+5, len(lines))))
        if not has_processing:
            lines.insert(i+1, 'ProcessingError = DataIntegrityError  # Backward compatibility\n')
            modified = True
            break

if modified:
    with open("varidex/exceptions.py", 'w') as f:
        f.writelines(lines)
    print("✓ Added ProcessingError to exceptions.py")
else:
    print("✓ ProcessingError already in exceptions.py")

# Add validate_reference_allele
with open("varidex/pipeline/validators.py", 'r') as f:
    content = f.read()

if "def validate_reference_allele" not in content:
    code = '''

def validate_reference_allele(ref: str) -> bool:
    """
    Validate reference allele sequence.
    
    Args:
        ref: Reference allele sequence
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If invalid
    """
    from varidex.exceptions import ValidationError
    
    if not ref:
        raise ValidationError("Reference allele cannot be empty")
    
    if not all(c in 'ACGTN' for c in ref.upper()):
        raise ValidationError(f"Invalid reference allele: {ref}")
    
    return True
'''
    
    content += code
    with open("varidex/pipeline/validators.py", 'w') as f:
        f.write(content)
    print("✓ Added validate_reference_allele")
else:
    print("✓ validate_reference_allele already exists")

print("\nTesting imports...")
import sys
if 'varidex.exceptions' in sys.modules:
    del sys.modules['varidex.exceptions']
if 'varidex.pipeline.validators' in sys.modules:
    del sys.modules['varidex.pipeline.validators']

try:
    from varidex.exceptions import ProcessingError
    print(f"✓ ProcessingError: {ProcessingError}")
except Exception as e:
    print(f"✗ ProcessingError failed: {e}")

try:
    from varidex.pipeline.validators import validate_reference_allele
    print(f"✓ validate_reference_allele: {validate_reference_allele}")
except Exception as e:
    print(f"✗ validate_reference_allele failed: {e}")

