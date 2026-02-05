#!/bin/bash
# quick-matcher-fix.sh - Normalize chrom/pos in matcher
set -euo pipefail

echo "=== Matcher Coord Norm Fix ==="

# Edit matching_improved.py: strip 'chr', upper alleles
sed -i 's/chrom = str(row\[.*\]).*/chrom = str(row[\"CHROM\"]).upper().lstrip(\"chr\")/' \
    varidex/io/matching_improved.py || true

sed -i 's/ref = row\[.*\]/ref = row[\"REF\"].upper()/' \
    varidex/io/matching_improved.py || true

sed -i 's/pos = row\[.*\]/pos = int(row[\"POS\"])/' \
    varidex/io/matching_improved.py || true

black varidex/io/matching_improved.py

echo "Matcher normalized. Run: ./scripts/debug-matcher.sh"
