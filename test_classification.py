#!/usr/bin/env python3
"""
test_classification.py - Test ACMG Classification on Matched Variants
Run ACMG classification on the matched variants from test_real_data.sh
"""

import sys
from pathlib import Path
import pandas as pd

print("="*70)
print("ACMG CLASSIFICATION TEST")
print("="*70)
print()

# Check if matched variants file exists
matched_file = Path("test_output/matched_variants.csv")
if not matched_file.exists():
    print("❌ No matched variants found!")
    print(f"   Expected: {matched_file}")
    print()
    print("Run this first:")
    print("  bash test_real_data.sh")
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
    print("✓ Classifier imported successfully")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)
print()

# Initialize classifier
print("Initializing ACMG classifier...")
config = ACMGConfig(
    enable_pvs1=True,  # LOF in LOF genes
    enable_pm4=True,   # Protein length changes
    enable_pp2=True,   # Missense in missense-rare genes
    enable_ba1=True,   # Common polymorphism
    enable_bs1=True,   # High frequency
    enable_bp1=True,   # Missense in LOF genes
    enable_bp3=True,   # In-frame indel in repeat
    enable_metrics=True
)
classifier = ACMGClassifier(config=config)
print("✓ Classifier initialized")
print()

# Helper function to extract molecular consequence properly
def extract_molecular_consequence(info_str):
    """Extract molecular consequence from INFO field.

    Format: MC=SO:0001583|missense_variant
    Returns: missense_variant
    """
    if 'MC=' not in str(info_str):
        return ''

    mc_full = str(info_str).split('MC=')[-1].split(';')[0]

    # Split by | and take the term (not the SO ID)
    if '|' in mc_full:
        return mc_full.split('|')[1]  # Get 'missense_variant' part

    return mc_full

# Helper function to extract gene
def extract_gene(info_str):
    """Extract gene symbol from GENEINFO field.

    Format: GENEINFO=ISG15:9636
    Returns: ISG15
    """
    if 'GENEINFO=' not in str(info_str):
        return ''

    gene_info = str(info_str).split('GENEINFO=')[-1].split(';')[0]
    return gene_info.split(':')[0]

# Helper function to extract variant type
def extract_variant_type(info_str):
    """Extract variant type from CLNVC field.

    Format: CLNVC=single_nucleotide_variant
    Returns: single_nucleotide_variant
    """
    if 'CLNVC=' not in str(info_str):
        return ''

    return str(info_str).split('CLNVC=')[-1].split(';')[0]

# Classify a sample of variants (first 10 for testing)
print("="*70)
print("CLASSIFYING SAMPLE VARIANTS (first 10)")
print("="*70)
print()

sample_size = min(10, len(matched_df))
results = []

for idx, row in matched_df.head(sample_size).iterrows():
    # Extract fields properly
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

    # Classify variant
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
            'duration_ms': round(duration * 1000, 2)
        }
        results.append(result)

        # Print result
        evidence_codes = []
        if evidence.pvs: evidence_codes.extend(list(evidence.pvs))
        if evidence.ps: evidence_codes.extend(list(evidence.ps))
        if evidence.pm: evidence_codes.extend(list(evidence.pm))
        if evidence.pp: evidence_codes.extend(list(evidence.pp))
        if evidence.ba: evidence_codes.extend(list(evidence.ba))
        if evidence.bs: evidence_codes.extend(list(evidence.bs))
        if evidence.bp: evidence_codes.extend(list(evidence.bp))

        evidence_str = ', '.join(evidence_codes) if evidence_codes else 'No evidence'

        print(f"{idx+1}. {variant.rsid} ({variant.gene})")
        print(f"   MC: {variant.molecular_consequence}")
        print(f"   ClinVar: {variant.clinical_sig}")
        print(f"   ACMG: {classification} ({confidence})")
        print(f"   Evidence: {evidence_str}")
        print(f"   Counts: PVS={len(evidence.pvs)} PS={len(evidence.ps)} PM={len(evidence.pm)} PP={len(evidence.pp)} | BA={len(evidence.ba)} BS={len(evidence.bs)} BP={len(evidence.bp)}")
        print(f"   Time: {duration*1000:.1f}ms")
        print()

    except Exception as e:
        print(f"❌ Classification failed for {variant.rsid}: {e}")
        import traceback
        traceback.print_exc()
        print()

# Summary
print("="*70)
print("CLASSIFICATION SUMMARY")
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

    print(f"  Pathogenic: PVS={total_pvs} PS={total_ps} PM={total_pm} PP={total_pp}")
    print(f"  Benign: BA={total_ba} BS={total_bs} BP={total_bp}")
    print()

    # Average processing time
    avg_time = results_df['duration_ms'].mean()
    print(f"Average processing time: {avg_time:.2f}ms per variant")
    print()

    # Save results
    output_file = Path("test_output/classified_sample.csv")
    results_df.to_csv(output_file, index=False)
    print(f"✓ Saved results: {output_file}")
    print()

    # Comparison with ClinVar
    print("ClinVar vs ACMG comparison (sample):")
    for _, row in results_df.head(5).iterrows():
        print(f"  {row['rsid']}: {row['clinvar_sig']} → {row['acmg_classification']}")
    print()

print("="*70)
print("✅ CLASSIFICATION TEST COMPLETE")
print("="*70)
print()
print("Next steps:")
print("  1. Review: test_output/classified_sample.csv")
print("  2. Run full classification on all 34,875 variants")
print("  3. Generate reports")
print()
