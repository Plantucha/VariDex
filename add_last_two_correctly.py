#!/usr/bin/env python3

# Add ProcessingError (different from DataProcessingError!)
with open("varidex/exceptions.py", 'r') as f:
    content = f.read()

if "ProcessingError =" not in content:
    # Add it after DataProcessingError
    content = content.replace(
        "DataProcessingError = DataIntegrityError",
        "DataProcessingError = DataIntegrityError\nProcessingError = DataIntegrityError  # Alias"
    )
    
    # Add to __all__
    if '"ProcessingError"' not in content:
        content = content.replace(
            '"DataProcessingError",',
            '"DataProcessingError",\n    "ProcessingError",'
        )
    
    with open("varidex/exceptions.py", 'w') as f:
        f.write(content)
    print("✓ Added ProcessingError")
else:
    print("✓ ProcessingError already exists")

# Add validate_variant
with open("varidex/pipeline/validators.py", 'r') as f:
    content = f.read()

if "def validate_variant(" not in content:
    code = '''

def validate_variant(variant_data: dict) -> bool:
    """
    Validate complete variant data.
    
    Args:
        variant_data: Dictionary with variant information
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If invalid
    """
    from varidex.exceptions import ValidationError
    
    required_fields = ["chromosome", "position"]
    for field in required_fields:
        if field not in variant_data:
            raise ValidationError(f"Missing required field: {field}")
    
    # Validate coordinates
    validate_coordinates(
        variant_data["chromosome"],
        variant_data["position"],
        variant_data.get("ref", ""),
        variant_data.get("alt", "")
    )
    
    return True
'''
    
    content += code
    with open("varidex/pipeline/validators.py", 'w') as f:
        f.write(content)
    print("✓ Added validate_variant")
else:
    print("✓ validate_variant already exists")

# Test imports
print("\nTesting imports...")
import sys
for mod in ['varidex.exceptions', 'varidex.pipeline.validators']:
    if mod in sys.modules:
        del sys.modules[mod]

try:
    from varidex.exceptions import ProcessingError
    print(f"✓ ProcessingError: {ProcessingError}")
except Exception as e:
    print(f"✗ ProcessingError: {e}")

try:
    from varidex.pipeline.validators import validate_variant
    print(f"✓ validate_variant: {validate_variant}")
except Exception as e:
    print(f"✗ validate_variant: {e}")

