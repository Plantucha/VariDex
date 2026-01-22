#!/usr/bin/env python3
import os
import re
from pathlib import Path

# Fix F541 f-strings
for py_file in Path("varidex").rglob("*.py"):
    content = py_file.read_text()
    # Replace f"static text" -> "static text"
    fixed = re.sub(r'f"([^"]*)"', r'"\1"', content)
    if fixed != content:
        py_file.write_text(fixed)
        print(f"Fixed f-string: {py_file}")

# Fix bare except
for py_file in Path("varidex").rglob("*.py"):
    content = py_file.read_text()
    fixed = re.sub(r"except:\s*", 'except Exception as e:\n        logger.exception(e)\n        raise', content)
    if fixed != content:
        py_file.write_text(fixed)
        print(f"Fixed bare except: {py_file}")
