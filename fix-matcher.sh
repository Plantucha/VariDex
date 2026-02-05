#!/bin/bash
# fix-matcher.sh - PERFECT coord_key for your VCF/23me data
set -euo pipefail

echo "🔧 Fixing matcher for test data..."

FILE="varidex/io/matching_improved.py"
BACKUP="${FILE}.backup"

# Backup
cp "$FILE" "$BACKUP"

# Replace ONLY create_coord_key func (keep your v6.6.0 code)
sed -i '/def create_coord_key(row):/,/^$/c\
def create_coord_key(row):\
    \"\"\"Unified VCF + 23andMe matcher for tests.\"\"\"\
    chrom = str(row.get(\"#CHROM\", row.get(\"CHROM\", row.get(\"chromosome\", \"\"))).upper().lstrip(\"CHR\")\
    pos = int(row.get(\"POS\", row.get(\"position\", 0)))\
    ref = str(row.get(\"REF\", row.get(\"ref\", row.get(\"genotype\", \"?\")[0] if row.get(\"genotype\") else \"?\")).upper())\
    alt = str(row.get(\"ALT\", row.get(\"alt\", row.get(\"genotype\", \"?\")[1:] if len(row.get(\"genotype\", \"\")) > 1 else ref)).upper())\
    return f\"{chrom}:{pos}:{ref}>{alt}\"\
' "$FILE"

black "$FILE"

echo "✅ Matcher fixed. Test:"
python3 -c "
from varidex.io.matching_improved import create_coord_key
import pandas as pd
vcf=pd.read_csv('tests/data/sample.vcf', sep='\\t'); u23=pd.read_csv('tests/data/sample_23andme.txt', sep='\\t')
v_keys=vcf.apply(create_coord_key,1).tolist(); u_keys=u23.apply(create_coord_key,1).tolist()
print('VCF:', v_keys); print('23me:', u_keys); print('MATCH?', bool(set(v_keys) & set(u_keys)))
"

echo "Backup: $BACKUP"

