#!/usr/bin/env python3
"""
debug_evidence_assignment.py - Step-by-step trace of evidence assignment
"""

# Mock variant data
class MockVariant:
    def __init__(self):
        self.rsid = "rs202075563"
        self.gene = "ISG15"
        self.molecular_consequence = "missense_variant"
        self.clinical_sig = "Uncertain_significance"
        self.review_status = "criteria_provided,_single_submitter"
        self.variant_type = "single_nucleotide_variant"
        self.num_submitters = 0

variant = MockVariant()

print("="*70)
print("DEBUG: EVIDENCE ASSIGNMENT LOGIC")
print("="*70)
print()

print("Variant:")
print(f"  rsid: {variant.rsid}")
print(f"  gene: {variant.gene}")
print(f"  molecular_consequence: {variant.molecular_consequence}")
print(f"  clinical_sig: {variant.clinical_sig}")
print()

# Simulate normalization
def normalize_text(text):
    if not text:
        return ""
    return str(text).strip().lower()

sig_lower = normalize_text(variant.clinical_sig)
genes = set([variant.gene])  # Simulated gene set
consequence = normalize_text(variant.molecular_consequence)

print("Normalized:")
print(f"  sig_lower: '{sig_lower}'")
print(f"  genes: {genes}")
print(f"  consequence: '{consequence}'")
print()

# Load gene lists from config
print("Loading gene lists from config...")
try:
    from varidex.core.config import LOF_GENES, MISSENSE_RARE_GENES
    print(f"✓ LOF_GENES: {len(LOF_GENES)} genes")
    print(f"✓ MISSENSE_RARE_GENES: {len(MISSENSE_RARE_GENES)} genes")
    print()

    # Check if ISG15 is in any gene list
    print("Gene list membership:")
    print(f"  ISG15 in LOF_GENES: {variant.gene in LOF_GENES}")
    print(f"  ISG15 in MISSENSE_RARE_GENES: {variant.gene in MISSENSE_RARE_GENES}")
    print()

    if variant.gene in LOF_GENES:
        print("  → ISG15 is a LOF gene")
    if variant.gene in MISSENSE_RARE_GENES:
        print("  → ISG15 is a missense-rare gene")
    print()

except ImportError as e:
    print(f"❌ Failed to load gene lists: {e}")
    print()

# Check PP2 criteria
print("PP2 CHECK (Missense in missense-rare genes):")
print("-" * 70)
print(f"1. Is 'missense' in consequence? {'missense' in consequence}")
print(f"2. Is gene in MISSENSE_RARE_GENES? {variant.gene in MISSENSE_RARE_GENES}")
print(f"3. Is 'pathogenic' in sig_lower? {'pathogenic' in sig_lower}")
print()

if 'missense' in consequence:
    print("✓ Step 1 passed: missense in consequence")
    matching_genes = genes.intersection(MISSENSE_RARE_GENES)
    print(f"  Matching genes: {matching_genes}")

    if matching_genes:
        print("✓ Step 2 passed: gene in MISSENSE_RARE_GENES")
        if 'pathogenic' in sig_lower:
            print("✓ Step 3 passed: pathogenic in clinical sig")
            print("  → PP2 SHOULD BE ASSIGNED")
        else:
            print("✗ Step 3 FAILED: 'pathogenic' NOT in clinical sig")
            print(f"  clinical_sig = '{sig_lower}'")
            print("  → PP2 NOT assigned (requires pathogenic)")
    else:
        print("✗ Step 2 FAILED: gene NOT in MISSENSE_RARE_GENES")
else:
    print("✗ Step 1 FAILED: 'missense' NOT in consequence")
print()

# Check BP1 criteria
print("BP1 CHECK (Missense in LOF genes):")
print("-" * 70)
print(f"1. Is 'missense' in consequence? {'missense' in consequence}")
print(f"2. Is gene in LOF_GENES? {variant.gene in LOF_GENES}")
print(f"3. Is 'benign' in sig_lower? {'benign' in sig_lower}")
print()

if 'missense' in consequence:
    print("✓ Step 1 passed: missense in consequence")
    matching_genes = genes.intersection(LOF_GENES)
    print(f"  Matching genes: {matching_genes}")

    if matching_genes:
        print("✓ Step 2 passed: gene in LOF_GENES")
        if 'benign' in sig_lower:
            print("✓ Step 3 passed: benign in clinical sig")
            print("  → BP1 SHOULD BE ASSIGNED")
        else:
            print("✗ Step 3 FAILED: 'benign' NOT in clinical sig")
            print(f"  clinical_sig = '{sig_lower}'")
            print("  → BP1 NOT assigned (requires benign)")
    else:
        print("✗ Step 2 FAILED: gene NOT in LOF_GENES")
else:
    print("✗ Step 1 FAILED: 'missense' NOT in consequence")
print()

print("="*70)
print("DIAGNOSIS")
print("="*70)
print()
print("The variant has 'missense_variant' molecular consequence,")
print("but ClinVar classification is 'Uncertain_significance'.")
print()
print("Evidence codes require specific ClinVar classifications:")
print("  - PP2: requires 'pathogenic' in clinical_sig")
print("  - BP1: requires 'benign' in clinical_sig")
print("  - BA1: requires 'common' AND 'polymorphism' in clinical_sig")
print("  - BS1: requires frequency-related terms in clinical_sig")
print()
print("Since this variant is VUS in ClinVar, no evidence codes match.")
print()
print("To see evidence assignment working, test with:")
print("  - A pathogenic missense variant (for PP2)")
print("  - A benign variant (for BP1, BA1, BS1)")
print("  - A frameshift/nonsense variant (for PVS1)")
