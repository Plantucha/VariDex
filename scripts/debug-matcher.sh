#!/bin/bash
# debug-matcher.sh - Debug no matches with logs
set -euo pipefail

SAMPLE_VCF="tests/data/sample.vcf"
SAMPLE_23="tests/data/sample_23andme.txt"
OUT_LOG="matcher_debug.log"

echo "=== Matcher Debug ==="

python -c "
from varidex.io.matching_improved import create_coord_key
import pandas as pd
vcf_df = pd.read_csv('$SAMPLE_VCF', sep='\t')
user_df = pd.read_csv('$SAMPLE_23', sep='\t')
print('VCF keys:', vcf_df.apply(create_coord_key, axis=1).tolist()[:5])
print('User keys:', user_df.apply(create_coord_key, axis=1).tolist()[:5])
" > "$OUT_LOG"

echo "Debug log: $OUT_LOG"
grep -i "no match\|key" "$OUT_LOG" || echo "Add print statements first"

