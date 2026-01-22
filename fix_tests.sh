#!/bin/bash

# Backup the file
cp tests/test_gnomad_integration.py tests/test_gnomad_integration.py.bak

# Fix 1: Replace _extract_coordinates with _extract_variant_coordinates
sed -i 's/_extract_coordinates(variant)/_extract_variant_coordinates(variant)/g' tests/test_gnomad_integration.py

echo "✅ Fixed method name: _extract_coordinates -> _extract_variant_coordinates"

# Fix 2: We need to look at the gnomad_client.py to see what structure it expects
# For now, let's check the test
