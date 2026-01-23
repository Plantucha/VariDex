#!/bin/bash
python3 -c "
from varidex.io.loaders.clinvar import load_clinvar_file
from varidex.io.loaders.user import load_user_file
from varidex.io import matching
import pandas as pd
from collections import Counter

print('📥 MICHAL PIPELINE v6.3.0 - CLINVAR DIRECT 🔥')

c = load_clinvar_file('clinvar/clinvar_GRCh37.vcf')
u = load_user_file('data/raw.txt')
print(f'🔬 ClinVar: {len(c):,} | 🧬 23andMe: {len(u):,}')

print('🔗 Hybrid matching...')
m = matching.match_variants_hybrid(c, u)[0]
print(f'✅ Matched: {len(m):,} variants')

# USE CLINVAR CLASSIFICATIONS DIRECTLY
m['acmg_classification'] = m['clinical_sig'].str.replace('_', ' ')

# Map to standard ACMG format
classification_map = {
    'Pathogenic': 'P',
    'Pathogenic/Likely pathogenic': 'P',
    'Likely pathogenic': 'LP',
    'Benign': 'B',
    'Benign/Likely benign': 'B',
    'Likely benign': 'LB',
    'Uncertain significance': 'VUS'
}

m['acmg_final'] = m['acmg_classification'].map(classification_map).fillna('VUS')

print('\n🏥 MICHAL CLINICAL REPORT (ClinVar Direct)')
print('='*60)
counter = Counter(m['acmg_final'])
emoji_map = {'P':'🔴','LP':'🟠','VUS':'🟡','LB':'🟢','B':'🟢'}
for cat in ['P','LP','VUS','LB','B']:
    print(f'{emoji_map[cat]} {cat.ljust(12)}: {counter.get(cat,0):,}')

print(f'📊 TOTAL: {len(m):,}')
m.to_csv('output/michal_clinvar_direct.csv', index=False)
print('✅ output/michal_clinvar_direct.csv SAVED!')
print('🏥 P/LP = clinical priority')
"
