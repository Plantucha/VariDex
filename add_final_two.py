#!/usr/bin/env python3

def add_processing_error():
    """Add ProcessingError alias"""
    file_path = "varidex/exceptions.py"
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    if "ProcessingError =" not in content:
        # Add after ConfigurationError
        content = content.replace(
            "ConfigurationError = ValidationError  # Backward compatibility",
            "ConfigurationError = ValidationError  # Backward compatibility\nProcessingError = DataIntegrityError  # Backward compatibility"
        )
        
        # Add to __all__
        if '"ProcessingError"' not in content:
            content = content.replace(
                '"ConfigurationError",',
                '"ConfigurationError",\n    "ProcessingError",'
            )
        
        with open(file_path, 'w') as f:
            f.write(content)
        print("✓ Added ProcessingError")
    else:
        print("✓ ProcessingError already exists")

def add_validate_coordinates():
    """Add validate_coordinates function"""
    file_path = "varidex/pipeline/validators.py"
    
    code = '''

def validate_coordinates(chromosome: str, position: int, ref: str = "", alt: str = "") -> bool:
    """
    Validate genomic coordinates.
    
    Args:
        chromosome: Chromosome identifier
        position: Genomic position
        ref: Reference allele (optional)
        alt: Alternate allele (optional)
        
    Returns:
        True if coordinates are valid
        
    Raises:
        ValidationError: If coordinates are invalid
    """
    from varidex.exceptions import ValidationError
    
    # Validate chromosome
    validate_chromosome(chromosome)
    
    # Validate position
    if not isinstance(position, int) or position < 1:
        raise ValidationError(f"Invalid position: {position}")
    
    # Validate alleles if provided
    if ref and not all(c in 'ACGTN' for c in ref.upper()):
        raise ValidationError(f"Invalid reference allele: {ref}")
    
    if alt and not all(c in 'ACGTN' for c in alt.upper()):
        raise ValidationError(f"Invalid alternate allele: {alt}")
    
    return True
'''
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    if "def validate_coordinates" not in content:
        content += code
        with open(file_path, 'w') as f:
            f.write(content)
        print("✓ Added validate_coordinates")
    else:
        print("✓ validate_coordinates already exists")

def main():
    print("="*70)
    print("Adding Final Two Items")
    print("="*70)
    
    add_processing_error()
    add_validate_coordinates()
    
    print("\n✅ All done!")

if __name__ == "__main__":
    main()
