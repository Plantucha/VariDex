#!/usr/bin/env bash
set -euo pipefail

python3 -c "
from pathlib import Path
from collections import Counter
from varidex.io.loaders.clinvar import load_clinvar_file
from varidex.io.loaders.user import load_user_file
from varidex.io import matching
import pandas as pd

print('📥 MICHAL PIPELINE v6.3.0 - CLINVAR DIRECT 🔥')
print('=' * 70)

print('LOADING VCF: clinvar_GRCh37.vcf')
c = load_clinvar_file('clinvar/clinvar_GRCh37.vcf')

print('LOADING USER: data/raw.txt')
u = load_user_file('data/raw.txt')

print(f'🔬 ClinVar: {len(c):,} | 🧬 23andMe: {len(u):,}')

print('🔗 Hybrid matching...')
m = matching.match_variants_hybrid(c, u, 'vcf', '23andme')[0]
print(f'✅ Matched: {len(m):,} variants')

m['acmg_classification'] = m['clinical_sig'].str.replace('_', ' ', regex=False)

classification_map = {
    'Pathogenic': 'P',
    'Pathogenic/Likely pathogenic': 'P',
    'Likely pathogenic': 'LP',
    'Benign': 'B',
    'Benign/Likely benign': 'B',
    'Likely benign': 'LB', 
    'Uncertain significance': 'VUS',
    'not provided': 'VUS'
}

m['acmg_final'] = m['acmg_classification'].map(classification_map).fillna('VUS')

print('\n🏥 MICHAL CLINICAL REPORT (ClinVar Direct)')
print('=' * 60)
counter = Counter(m['acmg_final'])
emoji_map = {'P': '🔴', 'LP': '🟠', 'VUS': '🟡', 'LB': '🟢', 'B': '🟢'}
for cat in ['P', 'LP', 'VUS', 'LB', 'B']:
    print(f'{emoji_map[cat]} {cat:<12}: {counter.get(cat, 0):>5,}')
print(f'📊 TOTAL: {len(m):>5,}')
print('=' * 60)

output_dir = Path('output')
output_dir.mkdir(parents=True, exist_ok=True)

csv_path = output_dir / 'michal_clinvar_direct.csv'
m.to_csv(csv_path, index=False)
print(f'✅ {csv_path} SAVED!')
print('🏥 P/LP = clinical priority')
"
