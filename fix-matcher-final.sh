#!/bin/bash
# fix-matcher-final.sh - Working coord_key for test data
set -euo pipefail

echo "🔧 Fixing matcher coord_key..."

FILE="varidex/io/matching_improved.py"

# Remove broken func at end
sed -i '/^def create_coord_key(row):$/,/return f"{chrom}:{pos}:{ref}>{alt}"$/d' "$FILE"

# Add correct version
cat >> "$FILE" << 'ENDFIX'

def create_coord_key(row):
    """v6.6.1: Handles VCF (#CHROM/POS/REF/ALT) + 23me (chromosome/position/genotype)."""
    chrom = str(row.get('#CHROM', row.get('CHROM', row.get('chromosome', '')))).upper().lstrip('CHR')
    pos = int(row.get('POS', row.get('position', 0)))
    ref_col = row.get('REF', row.get('ref', ''))
    alt_col = row.get('ALT', row.get('alt', ''))
    geno = row.get('genotype', '')
    
    # VCF has REF/ALT, 23me has genotype
    ref = str(ref_col if ref_col else (geno[0] if geno else '?')).upper()
    alt = str(alt_col if alt_col else (geno[1:] if len(geno) > 1 else ref)).upper()
    
    return f"{chrom}:{pos}:{ref}>{alt}"
ENDFIX

black "$FILE"
echo "✅ Fixed. Testing..."

python3 << 'PYTEST'
from varidex.io.matching_improved import create_coord_key
import pandas as pd
vcf = pd.read_csv('tests/data/sample.vcf', sep='\t')
u23 = pd.read_csv('tests/data/sample_23andme.txt', sep='\t')
v = vcf.apply(create_coord_key, axis=1).tolist()
u = u23.apply(create_coord_key, axis=1).tolist()
print(f"VCF: {v}")
print(f"23me: {u}")
print(f"MATCH: {bool(set(v) & set(u))}")
PYTEST
