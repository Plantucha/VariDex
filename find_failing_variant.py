#!/usr/bin/env python3
"""Find which variant in the performance test is failing."""

from varidex.core.models import GenomicVariant
from varidex.pipeline.validators import validate_variant

print("=" * 70)
print("Finding the Invalid Variant in Performance Test")
print("=" * 70)
print()

# Replicate the test's variant generation
variants = [
    GenomicVariant(
        chromosome=f"chr{i % 22 + 1}",
        position=1000 * i,
        ref_allele="A",
        alt_allele="G",
        assembly="GRCh38",
    )
    for i in range(1000)
]

print(f"Generated {len(variants)} variants")
print()

# Find which ones fail
failing = []
for i, v in enumerate(variants):
    if not validate_variant(v, raise_on_error=False):
        failing.append((i, v))

print(f"Found {len(failing)} failing variant(s):")
print()

for i, v in failing:
    print(f"Variant #{i}:")
    print(f"  chromosome: {v.chromosome}")
    print(f"  position: {v.position}")
    print(f"  ref_allele: {v.ref_allele}")
    print(f"  alt_allele: {v.alt_allele}")
    print(f"  assembly: {v.assembly}")
    print()
    
    # Try to figure out why it fails
    from varidex.pipeline.validators import validate_chromosome, validate_coordinates
    
    print(f"  validate_chromosome('{v.chromosome}'): {validate_chromosome(v.chromosome)}")
    
    # Check if position exceeds chromosome length
    from varidex.pipeline.validators import CHROMOSOME_LENGTHS
    chrom_num = v.chromosome.replace("chr", "")
    max_pos = CHROMOSOME_LENGTHS.get(chrom_num, "unknown")
    print(f"  Max position for {chrom_num}: {max_pos}")
    print(f"  Variant position: {v.position}")
    print(f"  Position > max: {v.position > max_pos if isinstance(max_pos, int) else 'N/A'}")

print()
print("=" * 70)
print("Solution:")
print("=" * 70)

if failing:
    i, v = failing[0]
    print(f"Variant #{i} at position {v.position} exceeds chromosome {v.chromosome} length")
    print()
    print("The test generates: position = 1000 * i")
    print(f"For i=0, position=0 which is < 1 (invalid!)")
    print()
    print("Fix: Change test to start from i=1 or use position = 1000 * (i + 1)")
