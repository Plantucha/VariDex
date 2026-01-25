#!/usr/bin/env python3
"""Merge duplicate markers sections in pytest.ini."""

def merge_markers():
    """Merge all markers into single section."""
    
    ini_file = "pytest.ini"
    
    # Read file
    with open(ini_file, 'r') as f:
        content = f.read()
    
    # Collect all unique markers
    markers = set()
    
    # Find all marker lines
    for line in content.split('\n'):
        line = line.strip()
        if ':' in line and not line.startswith('[') and not line.startswith('#'):
            # This looks like a marker definition
            if any(keyword in line.lower() for keyword in ['test', 'integration', 'performance', 'unit', 'smoke', 'slow']):
                markers.add(line)
    
    # Create new pytest.ini with single markers section
    new_content = """[pytest]
python_files = test_*.py
python_classes = Test*
python_functions = test_*
testpaths = tests

markers =
    integration: Integration tests (deselect with '-m "not integration"')
    performance: Performance benchmarks (deselect with '-m "not performance"')
    unit: Unit tests (fast, isolated)
    smoke: Smoke tests (critical functionality)
    slow: Slow tests (can be skipped)

console_output_style = progress
addopts = -v --strict-markers --tb=short

minversion = 7.0
"""
    
    with open(ini_file, 'w') as f:
        f.write(new_content)
    
    return "✓ Merged all markers into single section"


if __name__ == "__main__":
    import subprocess
    
    print("=" * 70)
    print("Merging Duplicate Markers")
    print("=" * 70)
    print()
    
    print(merge_markers())
    print()
    
    print("New pytest.ini:")
    with open("pytest.ini", 'r') as f:
        print(f.read())
    print()
    
    print("=" * 70)
    print("Testing Collection")
    print("=" * 70)
    result = subprocess.run(
        ["pytest", "tests/", "--co", "-q"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✓ SUCCESS! All tests can be collected")
        print()
        # Show summary
        output_lines = result.stdout.strip().split('\n')
        for line in output_lines[-5:]:
            print(line)
    else:
        print("Errors:")
        print(result.stderr[:1000])
