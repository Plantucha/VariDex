#!/usr/bin/env python3
"""Final fix for remaining ACMG test issues."""

import re

def final_acmg_fix():
    """Fix remaining constructor calls in ACMG tests."""
    
    test_file = "tests/test_acmg_classification.py"
    
    with open(test_file, 'r') as f:
        content = f.read()
    
    print("Searching for ACMGCriteria/ACMGEvidenceSet calls with old syntax...")
    print()
    
    # Find all ACMGCriteria and ACMGEvidenceSet constructor calls
    # They can span multiple lines
    
    # Pattern to match multiline constructor calls
    pattern = r'(ACMGCriteria|ACMGEvidenceSet)\s*\(((?:[^()]+|\([^()]*\))*?)\)'
    
    def fix_constructor(match):
        class_name = match.group(1)
        args_str = match.group(2)
        
        # Find all criterion=True patterns
        criteria_dict = {
            'pvs': set(), 'ps': set(), 'pm': set(), 'pp': set(),
            'ba': set(), 'bs': set(), 'bp': set()
        }
        
        # Extract all criterion names
        for m in re.finditer(r'(\w+)\s*=\s*True', args_str):
            criterion = m.group(1)
            criterion_upper = criterion.upper()
            
            # Determine category
            for category in ['pvs', 'ps', 'pm', 'pp', 'ba', 'bs', 'bp']:
                if criterion_upper.startswith(category.upper()):
                    criteria_dict[category].add(criterion_upper)
                    break
        
        # Build new arguments
        new_args = []
        for category in ['pvs', 'ps', 'pm', 'pp', 'ba', 'bs', 'bp']:
            if criteria_dict[category]:
                criteria_list = sorted(list(criteria_dict[category]))
                criteria_str = '{' + ', '.join(f'"{c}"' for c in criteria_list) + '}'
                new_args.append(f'{category}={criteria_str}')
        
        if new_args:
            # Preserve indentation for multiline
            if '\n' in args_str:
                indent = '        '  # Common indentation for test functions
                result = f'{class_name}(\n{indent}{(",\n" + indent).join(new_args)}\n    )'
            else:
                result = f'{class_name}({", ".join(new_args)})'
        else:
            result = f'{class_name}()'
        
        return result
    
    # Apply fixes
    fixed_content = re.sub(pattern, fix_constructor, content, flags=re.DOTALL)
    
    # Count how many replacements
    original_matches = len(re.findall(pattern, content, flags=re.DOTALL))
    fixed_matches = len(re.findall(r'pvs=\{', fixed_content))
    
    print(f"Found {original_matches} constructor calls")
    print(f"Fixed {fixed_matches} to use set syntax")
    print()
    
    with open(test_file, 'w') as f:
        f.write(fixed_content)
    
    return True


if __name__ == "__main__":
    import subprocess
    
    print("=" * 70)
    print("Final ACMG Test Fix")
    print("=" * 70)
    print()
    
    final_acmg_fix()
    
    print("Formatting...")
    subprocess.run(["black", "tests/test_acmg_classification.py"], capture_output=True)
    print("✓ Formatted")
    print()
    
    print("=" * 70)
    print("Testing All ACMG Classification Tests")
    print("=" * 70)
    result = subprocess.run([
        "pytest", "tests/test_acmg_classification.py", "-v", "--tb=short"
    ])
    
    if result.returncode == 0:
        print()
        print("=" * 70)
        print("🎉 All ACMG Classification Tests Passing!")
        print("=" * 70)
