#!/usr/bin/env python3
"""Complete fix for matching.py - adds import and column reconciliation"""

from pathlib import Path

matching_file = Path("varidex/io/matching.py")
content = matching_file.read_text()

# Step 1: Add 're' import if missing
if "import re" not in content:
    # Find the imports section (after initial docstring)
    import_section_end = content.find("from varidex.io.normalization")
    if import_section_end == -1:
        import_section_end = content.find("logger = logging.getLogger")
    
    # Insert before the first from/logger line
    insert_pos = content.rfind("\n", 0, import_section_end)
    content = content[:insert_pos] + "\nimport re" + content[insert_pos:]
    print("✅ Added 'import re'")

# Step 2: Check if column reconciliation already exists
if "Reconcile column names for classification" in content:
    print("✅ Column reconciliation already present")
    matching_file.write_text(content)
    exit(0)

# Step 3: Add column reconciliation before final return
insert_point = content.rfind("return combined, rsid_count, coord_count")

if insert_point == -1:
    print("❌ Could not find insertion point")
    exit(1)

fix_code = '''
    # Reconcile column names for classification
    if 'chromosome_clinvar' in combined.columns and 'chromosome' not in combined.columns:
        combined['chromosome'] = combined['chromosome_clinvar']
    
    if 'position_clinvar' in combined.columns and 'position' not in combined.columns:
        combined['position'] = combined['position_clinvar']
    
    # Extract gene from INFO field if missing
    if 'gene' not in combined.columns or combined['gene'].isna().all():
        def extract_gene(info_str):
            if pd.isna(info_str):
                return None
            match = re.search(r'GENEINFO=([^:;]+)', str(info_str))
            return match.group(1) if match else None
        
        combined['gene'] = combined['INFO'].apply(extract_gene)
    
    # Ensure molecular_consequence exists
    if 'molecular_consequence' not in combined.columns:
        def extract_consequence(info_str):
            if pd.isna(info_str):
                return ''
            match = re.search(r'MC=([^;]+)', str(info_str))
            return match.group(1) if match else ''
        
        combined['molecular_consequence'] = combined['INFO'].apply(extract_consequence)
    
    # Ensure variant_type exists
    if 'variant_type' not in combined.columns:
        def extract_variant_type(info_str):
            if pd.isna(info_str):
                return 'single_nucleotide_variant'
            match = re.search(r'CLNVC=([^;]+)', str(info_str))
            return match.group(1).replace('_', ' ') if match else 'single_nucleotide_variant'
        
        combined['variant_type'] = combined['INFO'].apply(extract_variant_type)

'''

# Insert the fix
new_content = content[:insert_point] + fix_code + "\n    " + content[insert_point:]

# Write back
matching_file.write_text(new_content)
print("✅ Added column reconciliation")
print("\n🎯 matching.py is now fully patched!")
