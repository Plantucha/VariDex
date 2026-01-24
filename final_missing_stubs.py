#!/usr/bin/env python3

def force_add_configuration_error():
    """Force add ConfigurationError to exceptions.py"""
    file_path = "varidex/exceptions.py"
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Find the line with ACMGConfigurationError and add ConfigurationError after it
    modified = False
    for i, line in enumerate(lines):
        if 'ACMGConfigurationError = ValidationError' in line and not modified:
            # Check if ConfigurationError already exists nearby
            has_config = any('ConfigurationError =' in l for l in lines[max(0,i-5):i+5])
            if not has_config:
                lines.insert(i+1, 'ConfigurationError = ValidationError\n')
                modified = True
                break
    
    if modified:
        with open(file_path, 'w') as f:
            f.writelines(lines)
        print("✓ Forced ConfigurationError alias into exceptions.py")
    else:
        print("✓ ConfigurationError already exists or couldn't add")

def add_output_stage():
    """Add OutputStage to stages.py"""
    file_path = "varidex/pipeline/stages.py"
    
    code = '''

class OutputStage:
    """Pipeline output stage stub."""
    
    def __init__(self, output_format: str = "csv"):
        """Initialize with output format."""
        self.output_format = output_format
    
    def execute(self, data):
        """Execute output generation."""
        return data

'''
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    if "class OutputStage" not in content:
        content += code
        with open(file_path, 'w') as f:
            f.write(content)
        print("✓ Added OutputStage to stages.py")

def force_add_validate_chromosome():
    """Force add validate_chromosome to validators.py"""
    file_path = "varidex/pipeline/validators.py"
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    if "def validate_chromosome" not in content:
        code = '''

def validate_chromosome(chromosome: str) -> bool:
    """
    Validate chromosome identifier.
    
    Args:
        chromosome: Chromosome identifier (e.g., "1", "chr1", "X")
        
    Returns:
        True if valid chromosome
        
    Raises:
        ValidationError: If chromosome is invalid
    """
    from varidex.exceptions import ValidationError
    
    chrom = str(chromosome).upper().replace("CHR", "")
    valid = [str(i) for i in range(1, 23)] + ["X", "Y", "M", "MT"]
    
    if chrom not in valid:
        raise ValidationError(f"Invalid chromosome: {chromosome}")
    
    return True

'''
        content += code
        with open(file_path, 'w') as f:
            f.write(content)
        print("✓ Added validate_chromosome to validators.py")

def add_tsv_formatter():
    """Add TSVFormatter to formatters.py"""
    file_path = "varidex/reports/formatters.py"
    
    code = '''

class TSVFormatter(CSVFormatter):
    """Format reports as TSV (tab-separated)."""
    
    def __init__(self):
        """Initialize TSV formatter with tab delimiter."""
        super().__init__(delimiter="\\t")

'''
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    if "class TSVFormatter" not in content:
        content += code
        with open(file_path, 'w') as f:
            f.write(content)
        print("✓ Added TSVFormatter to formatters.py")

def main():
    print("="*70)
    print("Final Missing Stubs")
    print("="*70)
    
    try:
        force_add_configuration_error()
        add_output_stage()
        force_add_validate_chromosome()
        add_tsv_formatter()
        
        print("\n✅ Final stubs added!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
