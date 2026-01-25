#!/usr/bin/env python3
"""Quick test suite overview - run from VariDex directory."""

import subprocess
import sys
import time

def run_overview():
    """Run tests and provide overview of pass/fail status."""
    
    print("=" * 70)
    print("VariDex Test Suite Overview")
    print("=" * 70)
    print()
    
    # First, count total tests
    print("Collecting tests...")
    result = subprocess.run(
        ["pytest", "tests/", "--co", "-q"],
        capture_output=True,
        text=True
    )
    
    lines = result.stdout.strip().split('\n')
    for line in lines[-3:]:
        if 'test' in line.lower():
            print(f"  {line}")
    
    print()
    print("=" * 70)
    print("Running Tests (stopping after 20 failures for quick overview)")
    print("=" * 70)
    print()
    
    start_time = time.time()
    
    # Run tests with maxfail to get quick overview
    result = subprocess.run(
        ["pytest", "tests/", "--maxfail=20", "--tb=line", "-v"],
        capture_output=True,
        text=True
    )
    
    elapsed = time.time() - start_time
    
    # Parse output
    output = result.stdout
    lines = output.split('\n')
    
    # Find summary section
    print("\nTest Results Summary:")
    print("-" * 70)
    
    in_summary = False
    for line in lines:
        if '=====' in line and 'passed' in line.lower() or 'failed' in line.lower():
            in_summary = True
        if in_summary:
            print(line)
    
    print()
    print(f"⏱️  Time taken: {elapsed:.2f} seconds")
    print()
    
    # Show first few failures
    print("=" * 70)
    print("First Failures (if any):")
    print("=" * 70)
    
    failure_count = 0
    for line in lines:
        if "FAILED" in line:
            print(line)
            failure_count += 1
            if failure_count >= 10:
                print("... (showing first 10 failures)")
                break
    
    if failure_count == 0:
        print("🎉 No failures detected!")
    
    print()
    print("=" * 70)
    print("Next Steps:")
    print("=" * 70)
    print()
    print("Run specific test files:")
    print("  pytest tests/test_pipeline_validators.py -v  # We know this passes!")
    print("  pytest tests/test_core_models.py -v")
    print("  pytest tests/test_acmg_classification.py -v")
    print()
    print("Run without stopping on failures:")
    print("  pytest tests/ -v --tb=short")
    print()
    print("Get coverage report:")
    print("  pytest tests/ --cov=varidex --cov-report=html")


if __name__ == "__main__":
    run_overview()
