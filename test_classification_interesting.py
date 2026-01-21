#!/usr/bin/env python3
"""
test_classification_interesting.py - Test ACMG on clinically interesting variants
Tests variants that should trigger evidence codes (LOF, pathogenic, benign)
"""

import sys
from pathlib import Path
import pandas as pd

print("="*70)
print("ACMG CLASSIFICATION TEST - INTERESTING VARIANTS")
print("="*70)
print()

# Check if matched variants file exists
matched_file = Path("test_output/matched_variants.csv")
if not matched_file.exists():
    print("❌ No matched variants found!")
    print(f"   Expected: {matched_file}")
    sys.exit(1)

print(f"✓ Found matched variants: {matched_file}")
print()

# Load matched variants
print("Loading matched variants...")
matched_df = pd.read_csv(matched_file)
print(f"✓ Loaded {len(matched_df):,} matched variants")
print()

# Import classification components
print("Importing VariDex classifier...")
try:
    from varidex.core.models import VariantData
    from varidex.core.classifier.engine import ACMGClassifier
    from varidex.core.classifier.config import ACMGConfig
    from varidex.core.config import LOF_GENES, MISSENSE_RARE_GENES
    print("✓ Classifier imported successfully")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)
print()

# Helper functions
def extract_molecular_consequence(info_str):
    """Extract molecular consequence from INFO field."""
    if 'MC=' not in str(info_str):
        return ''
    mc_full = str(info_str).split('MC=')[-1].split(';')[0]
    if '|' in mc_full:
        return mc_full.split('|')[1]
    return mc_full

def extract_gene(info_str):
    """Extract gene symbol from GENEINFO field."""
    if 'GENEINFO=' not in str(info_str):
        return ''
    gene_info = str(info_str).split('GENEINFO=')[-1].split(';')[0]
    return gene_info.split(':')[0]

def extract_variant_type(info_str):
    """Extract variant type from CLNVC field."""
    if 'CLNVC=' not in str(info_str):
        return ''
    return str(info_str).split('CLNVC=')[-1].split(';')[0]

# Select interesting variants
print("Selecting clinically interesting variants...")
print()

# Add helper columns
matched_df['gene_extracted'] = matched_df['INFO'].apply(extract_gene)
matched_df['mc_extracted'] = matched_df['INFO'].apply(extract_molecular_consequence)

# Define test cases
test_variants = []

# 1. PVS1: LOF in SDHB (frameshift + pathogenic + LOF gene)
print("1. Looking for PVS1 candidates (LOF in LOF genes)...")
lof_sdhb = matched_df[
    (matched_df['rsid'] == 'rs587781266') |  # SDHB frameshift
    ((matched_df['gene_extracted'].isin(LOF_GENES)) & 
     (matched_df['mc_extracted'].str.contains('frameshift|nonsense', case=False, na=False)))
].head(3)
print(f"   Found {len(lof_sdhb)} PVS1 candidates")
test_variants.extend(lof_sdhb['rsid'].tolist())

# 2. PP2: Pathogenic missense in missense-rare genes
print("2. Looking for PP2 candidates (pathogenic missense in rare genes)...")
pp2_candidates = matched_df[
    (matched_df['gene_extracted'].isin(MISSENSE_RARE_GENES)) &
    (matched_df['mc_extracted'].str.contains('missense', case=False, na=False)) &
    (matched_df['clinical_sig'].str.contains('Pathogenic', case=False, na=False))
].head(2)
print(f"   Found {len(pp2_candidates)} PP2 candidates")
test_variants.extend(pp2_candidates['rsid'].tolist())

# 3. BP1: Benign missense in LOF genes
print("3. Looking for BP1 candidates (benign missense in LOF genes)...")
bp1_candidates = matched_df[
    (matched_df['gene_extracted'].isin(LOF_GENES)) &
    (matched_df['mc_extracted'].str.contains('missense', case=False, na=False)) &
    (matched_df['clinical_sig'].str.contains('Benign', case=False, na=False))
].head(2)
print(f"   Found {len(bp1_candidates)} BP1 candidates")
test_variants.extend(bp1_candidates['rsid'].tolist())

# 4. General pathogenic variants
print("4. Looking for pathogenic variants...")
pathogenic = matched_df[
    (matched_df['clinical_sig'] == 'Pathogenic')
].head(2)
print(f"   Found {len(pathogenic)} pathogenic variants")
test_variants.extend(pathogenic['rsid'].tolist())

# 5. General benign variants
print("5. Looking for benign variants...")
benign = matched_df[
    (matched_df['clinical_sig'] == 'Benign')
].head(2)
print(f"   Found {len(benign)} benign variants")
test_variants.extend(benign['rsid'].tolist())

print()
print(f"✓ Selected {len(test_variants)} interesting variants")
print()

# Initialize classifier
print("Initializing ACMG classifier...")
config = ACMGConfig(
    enable_pvs1=True,
    enable_pm4=True,
    enable_pp2=True,
    enable_ba1=True,
    enable_bs1=True,
    enable_bp1=True,
    enable_bp3=True,
    enable_metrics=True
)
classifier = ACMGClassifier(config=config)
print("✓ Classifier initialized")
print()

# Classify selected variants
print("="*70)
print("CLASSIFYING INTERESTING VARIANTS")
print("="*70)
print()

results = []
test_df = matched_df[matched_df['rsid'].isin(test_variants)]

for idx, (_, row) in enumerate(test_df.iterrows(), 1):
    # Extract fields
    info = str(row.get('INFO', ''))
    gene = extract_gene(info)
    molecular_consequence = extract_molecular_consequence(info)
    variant_type = extract_variant_type(info)

    # Create VariantData object
    variant = VariantData(
        rsid=str(row.get('rsid', '')),
        chromosome=str(row.get('CHROM', row.get('chromosome_clinvar', ''))),
        position=str(row.get('POS', row.get('position_clinvar', ''))),
        gene=gene,
        genotype=str(row.get('genotype', '')),
        clinical_sig=str(row.get('clinical_sig', '')),
        review_status=str(row.get('review_status', '')),
        molecular_consequence=molecular_consequence,
        variant_type=variant_type,
        num_submitters=0
    )

    # Classify
    try:
        classification, confidence, evidence, duration = classifier.classify_variant(variant)

        result = {
            'rsid': variant.rsid,
            'gene': variant.gene,
            'molecular_consequence': variant.molecular_consequence,
            'clinvar_sig': variant.clinical_sig,
            'acmg_classification': classification,
            'confidence': confidence,
            'pvs': len(evidence.pvs),
            'ps': len(evidence.ps),
            'pm': len(evidence.pm),
            'pp': len(evidence.pp),
            'ba': len(evidence.ba),
            'bs': len(evidence.bs),
            'bp': len(evidence.bp),
            'evidence_codes': [],
            'duration_ms': round(duration * 1000, 2)
        }

        # Collect evidence codes
        evidence_codes = []
        if evidence.pvs: evidence_codes.extend(list(evidence.pvs))
        if evidence.ps: evidence_codes.extend(list(evidence.ps))
        if evidence.pm: evidence_codes.extend(list(evidence.pm))
        if evidence.pp: evidence_codes.extend(list(evidence.pp))
        if evidence.ba: evidence_codes.extend(list(evidence.ba))
        if evidence.bs: evidence_codes.extend(list(evidence.bs))
        if evidence.bp: evidence_codes.extend(list(evidence.bp))
        result['evidence_codes'] = evidence_codes

        results.append(result)

        # Print result
        evidence_str = ', '.join(evidence_codes) if evidence_codes else 'No evidence'

        # Determine expected evidence
        expected = []
        if gene in LOF_GENES and any(x in molecular_consequence.lower() for x in ['frameshift', 'nonsense']):
            expected.append('PVS1')
        if gene in MISSENSE_RARE_GENES and 'missense' in molecular_consequence.lower() and 'pathogenic' in variant.clinical_sig.lower():
            expected.append('PP2')
        if gene in LOF_GENES and 'missense' in molecular_consequence.lower() and 'benign' in variant.clinical_sig.lower():
            expected.append('BP1')

        expected_str = f" [Expected: {', '.join(expected)}]" if expected else ""
        match = "✓" if all(e in evidence_codes for e in expected) else "⚠" if expected else ""

        print(f"{match} {idx}. {variant.rsid} ({variant.gene})")
        print(f"   MC: {variant.molecular_consequence}")
        print(f"   ClinVar: {variant.clinical_sig}")
        print(f"   ACMG: {classification} ({confidence})")
        print(f"   Evidence: {evidence_str}{expected_str}")
        print(f"   Time: {duration*1000:.1f}ms")
        print()

    except Exception as e:
        print(f"❌ Classification failed for {variant.rsid}: {e}")
        import traceback
        traceback.print_exc()
        print()

# Summary
print("="*70)
print("SUMMARY")
print("="*70)
print()

if results:
    results_df = pd.DataFrame(results)

    print(f"Total classified: {len(results)}")
    print()

    # Classification breakdown
    print("Classification breakdown:")
    class_counts = results_df['acmg_classification'].value_counts()
    for classification, count in class_counts.items():
        print(f"  {classification}: {count}")
    print()

    # Evidence breakdown
    print("Evidence codes assigned:")
    total_pvs = results_df['pvs'].sum()
    total_ps = results_df['ps'].sum()
    total_pm = results_df['pm'].sum()
    total_pp = results_df['pp'].sum()
    total_ba = results_df['ba'].sum()
    total_bs = results_df['bs'].sum()
    total_bp = results_df['bp'].sum()
    total = total_pvs + total_ps + total_pm + total_pp + total_ba + total_bs + total_bp

    print(f"  Pathogenic: PVS={total_pvs} PS={total_ps} PM={total_pm} PP={total_pp}")
    print(f"  Benign: BA={total_ba} BS={total_bs} BP={total_bp}")
    print(f"  Total: {total} evidence codes")
    print()

    # Average processing time
    avg_time = results_df['duration_ms'].mean()
    print(f"Average processing time: {avg_time:.2f}ms per variant")
    print()

    # Save results
    output_file = Path("test_output/classified_interesting.csv")
    results_df.to_csv(output_file, index=False)
    print(f"✓ Saved results: {output_file}")
    print()

print("="*70)
print("✅ TEST COMPLETE")
print("="*70)
