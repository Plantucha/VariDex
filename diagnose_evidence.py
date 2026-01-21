#!/usr/bin/env python3
"""
diagnose_evidence.py - Check why no evidence codes are being assigned
"""

import pandas as pd

print("="*70)
print("EVIDENCE EXTRACTION DIAGNOSTIC")
print("="*70)
print()

# Load matched variants
matched_df = pd.read_csv('test_output/matched_variants.csv', nrows=3)

print(f"Loaded {len(matched_df)} variants for analysis")
print()

# Check first variant in detail
print("VARIANT 1: rs202075563 (ISG15)")
print("-" * 70)
row = matched_df.iloc[0]

print("\nINFO field content:")
info = str(row['INFO'])
print(info[:500])
print()

# Parse molecular consequence
if 'MC=' in info:
    mc_full = info.split('MC=')[1].split(';')[0]
    print(f"Molecular Consequence (MC): {mc_full}")

    # Split into parts
    if '|' in mc_full:
        parts = mc_full.split('|')
        print(f"  SO ID: {parts[0]}")
        if len(parts) > 1:
            print(f"  Term: {parts[1]}")
else:
    print("❌ No MC= in INFO field")
print()

# Parse gene
if 'GENEINFO=' in info:
    gene_info = info.split('GENEINFO=')[1].split(';')[0]
    print(f"GENEINFO: {gene_info}")
    gene = gene_info.split(':')[0]
    print(f"  Gene symbol: {gene}")
else:
    print("❌ No GENEINFO= in INFO field")
print()

# Check clinical significance
print(f"Clinical Significance: {row['clinical_sig']}")
print()

# Show what test_classification.py is extracting
print("\nEXTRACTED VALUES (from test_classification.py logic):")
print("-" * 70)

# Gene extraction
gene_extracted = str(row.get('INFO', '')).split('GENEINFO=')[-1].split(';')[0].split(':')[0] if 'GENEINFO=' in str(row.get('INFO', '')) else ''
print(f"gene: '{gene_extracted}'")

# Molecular consequence extraction  
mc_extracted = str(row.get('INFO', '')).split('MC=')[-1].split(';')[0] if 'MC=' in str(row.get('INFO', '')) else ''
print(f"molecular_consequence: '{mc_extracted}'")

# Variant type extraction
vt_extracted = str(row.get('INFO', '')).split('CLNVC=')[-1].split(';')[0] if 'CLNVC=' in str(row.get('INFO', '')) else ''
print(f"variant_type: '{vt_extracted}'")

print(f"clinical_sig: '{row.get('clinical_sig', '')}'")
print(f"review_status: '{row.get('review_status', '')}'")
print()

# Check if molecular consequence would match any evidence criteria
print("\nEVIDENCE MATCHING CHECK:")
print("-" * 70)
mc_lower = mc_extracted.lower()

print(f"Molecular consequence (lowercase): '{mc_lower}'")
print()

# Check LOF indicators
lof_indicators = ['frameshift', 'nonsense', 'stop-gain', 'stop-gained',
                  'canonical-splice', 'splice-donor', 'splice-acceptor',
                  'start-lost', 'stop-lost', 'initiator-codon']

lof_match = any(ind in mc_lower for ind in lof_indicators)
print(f"LOF match: {lof_match}")
if lof_match:
    matches = [ind for ind in lof_indicators if ind in mc_lower]
    print(f"  Matched: {matches}")
print()

# Check other patterns
print("Pattern checks:")
print(f"  'missense' in mc: {'missense' in mc_lower}")
print(f"  'inframe' in mc: {'inframe' in mc_lower}")
print(f"  'in-frame' in mc: {'in-frame' in mc_lower}")
print(f"  'deletion' in mc: {'deletion' in mc_lower}")
print(f"  'insertion' in mc: {'insertion' in mc_lower}")
print()

# Check ClinVar significance
sig_lower = str(row['clinical_sig']).lower()
print(f"Clinical sig (lowercase): '{sig_lower}'")
print(f"  'pathogenic' in sig: {'pathogenic' in sig_lower}")
print(f"  'benign' in sig: {'benign' in sig_lower}")
print(f"  'uncertain' in sig: {'uncertain' in sig_lower}")
print()

print("="*70)
print("ANALYSIS COMPLETE")
print("="*70)
print()
print("The molecular consequence format from ClinVar is:")
print("  MC=SO:0001583|missense_variant")
print()
print("We need to extract just 'missense_variant' part after the |")
