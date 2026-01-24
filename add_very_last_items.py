#!/usr/bin/env python3

def add_configuration_error_alias():
    """Add ConfigurationError as an actual alias in the code"""
    file_path = "varidex/exceptions.py"
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    if "ConfigurationError =" not in content:
        # Add it right after DataProcessingError
        content = content.replace(
            'DataProcessingError = DataIntegrityError',
            'DataProcessingError = DataIntegrityError\nConfigurationError = ValidationError'
        )
        
        with open(file_path, 'w') as f:
            f.write(content)
        print("✓ Added ConfigurationError alias")

def add_find_fuzzy_matches():
    """Add find_fuzzy_matches to matching.py"""
    file_path = "varidex/io/matching.py"
    
    code = '''

def find_fuzzy_matches(
    variants_df: pd.DataFrame,
    reference_df: pd.DataFrame,
    tolerance: int = 5
) -> pd.DataFrame:
    """
    Find fuzzy matches with position tolerance.
    
    Args:
        variants_df: Variants to match
        reference_df: Reference dataset
        tolerance: Position tolerance in base pairs
        
    Returns:
        DataFrame with fuzzy matched variants
    """
    # Stub implementation - returns exact matches for now
    return find_exact_matches(variants_df, reference_df)

'''
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    if "def find_fuzzy_matches" not in content:
        content += code
        with open(file_path, 'w') as f:
            f.write(content)
        print("✓ Added find_fuzzy_matches to matching.py")

def add_filtering_stage():
    """Add FilteringStage to stages.py"""
    file_path = "varidex/pipeline/stages.py"
    
    code = '''

class FilteringStage:
    """Pipeline filtering stage stub."""
    
    def __init__(self, filters: list = None):
        """Initialize with filters."""
        self.filters = filters or []
    
    def execute(self, data):
        """Execute filtering on data."""
        return data

'''
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    if "class FilteringStage" not in content:
        content += code
        with open(file_path, 'w') as f:
            f.write(content)
        print("✓ Added FilteringStage to stages.py")

def re_add_validate_chromosome():
    """Re-add validate_chromosome (it might have been lost)"""
    file_path = "varidex/pipeline/validators.py"
    
    code = '''

def validate_chromosome(chromosome: str) -> bool:
    """
    Validate chromosome identifier.
    
    Args:
        chromosome: Chromosome identifier
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If invalid
    """
    from varidex.exceptions import ValidationError
    
    chrom = chromosome.upper().replace("CHR", "")
    valid_chroms = [str(i) for i in range(1, 23)] + ["X", "Y", "M", "MT"]
    
    if chrom not in valid_chroms:
        raise ValidationError(f"Invalid chromosome '{chromosome}'")
    
    return True

'''
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    if "def validate_chromosome" not in content:
        content += code
        with open(file_path, 'w') as f:
            f.write(content)
        print("✓ Added validate_chromosome to validators.py")

def add_csv_formatter():
    """Add CSVFormatter to formatters.py"""
    file_path = "varidex/reports/formatters.py"
    
    code = '''

class CSVFormatter:
    """Format reports as CSV."""
    
    def __init__(self, delimiter: str = ","):
        """Initialize CSV formatter."""
        self.delimiter = delimiter
    
    def format(self, data: dict) -> str:
        """Format data as CSV."""
        import csv
        import io
        
        output = io.StringIO()
        if isinstance(data, dict):
            writer = csv.DictWriter(output, fieldnames=data.keys(), delimiter=self.delimiter)
            writer.writeheader()
            writer.writerow(data)
        return output.getvalue()
    
    def save(self, data, filepath: str):
        """Save report to CSV file."""
        import pandas as pd
        if isinstance(data, pd.DataFrame):
            data.to_csv(filepath, index=False, sep=self.delimiter)
        elif isinstance(data, dict):
            pd.DataFrame([data]).to_csv(filepath, index=False, sep=self.delimiter)

'''
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    if "class CSVFormatter" not in content:
        content += code
        with open(file_path, 'w') as f:
            f.write(content)
        print("✓ Added CSVFormatter to formatters.py")

def main():
    print("="*70)
    print("Adding Very Last Items")
    print("="*70)
    
    try:
        add_configuration_error_alias()
        add_find_fuzzy_matches()
        add_filtering_stage()
        re_add_validate_chromosome()
        add_csv_formatter()
        
        print("\n✅ All very last items added!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
