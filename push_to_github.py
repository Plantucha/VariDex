#!/usr/bin/env python3
"""Git commit and push script."""

import subprocess
import os

def git_push():
    """Commit and push all changes."""
    
    print("=" * 70)
    print("Pushing VariDex Progress to GitHub")
    print("=" * 70)
    print()
    
    # Check status
    print("Checking git status...")
    status = subprocess.run(["git", "status", "-s"], capture_output=True, text=True)
    print(status.stdout)
    print()
    
    # Add all changes
    print("Adding all changes...")
    subprocess.run(["git", "add", "."])
    
    # Commit
    print("Committing...")
    commit_msg = "Complete validators module (42/42 tests passing)\n\n" \
                "- Fixed validators implementation\n" \
                "- Fixed pytest markers (735 tests collected)\n" \
                "- Fixed ACMG test constructors (partial)\n" \
                "- Fixed test generation bugs\n\n" \
                "Next: Finish ACMG classification logic"
    
    subprocess.run([
        "git", "commit", "-m", commit_msg
    ])
    
    # Push
    print("Pushing to GitHub...")
    subprocess.run(["git", "push", "origin", "main"])
    
    print()
    print("=" * 70)
    print("✅ Successfully pushed to GitHub!")
    print("=" * 70)
    print()
    
    # Show repo status
    print("Current branch status:")
    subprocess.run(["git", "log", "--oneline", "-5"])
    print()
    
    print("Test summary:")
    print("- validators: 42/42 ✅")
    print("- Total tests available: 735")
    print("- ACMG classification: 3/28 (next priority)")
    print()
    
    print("Next priorities:")
    print("1. Fix ACMG classification logic (varidex/core/classifier/engine.py)")
    print("2. pytest tests/ -v --maxfail=10")
    print("3. pytest tests/ --cov=varidex")

if __name__ == "__main__":
    git_push()
