#!/usr/bin/env python3
"""Final fixes for last 4 failing tests."""

def fix_validate_variant_raise():
    """Make validate_variant() actually raise when raise_on_error=True."""
    
    validators_file = "varidex/pipeline/validators.py"
    
    with open(validators_file, 'r') as f:
        content = f.read()
    
    # Replace the validate_variant function to handle raise_on_error properly
    old_func = '''def validate_variant(variant, raise_on_error: bool = False) -> bool:
    """
    Validate complete variant object.
    
    Works with VariantData model: ref_allele, alt_allele (not reference/alternate).
    """
    try:
        if not hasattr(variant, "chromosome"):
            return False
        if not hasattr(variant, "position"):
            return False
        
        if not validate_chromosome(variant.chromosome):
            return False
        
        try:
            pos = int(variant.position)
            if pos < 1:
                return False
        except (ValueError, TypeError):
            return False
        
        chrom_norm = str(variant.chromosome).upper().replace("CHR", "")
        max_pos = CHROMOSOME_LENGTHS.get(chrom_norm, 300000000)
        if pos > max_pos:
            return False
        
        # Check assembly attribute (not a parameter in GenomicVariant)
        if hasattr(variant, "assembly") and variant.assembly:
            if not validate_assembly(variant.assembly):
                return False
        
        # VariantData uses ref_allele and alt_allele
        if hasattr(variant, "ref_allele") and variant.ref_allele:
            if not validate_reference_allele(variant.ref_allele):
                return False
        
        if hasattr(variant, "alt_allele") and variant.alt_allele:
            if not validate_alternate_allele(variant.alt_allele):
                return False
        
        return True
        
    except Exception:
        return False'''
    
    new_func = '''def validate_variant(variant, raise_on_error: bool = False) -> bool:
    """
    Validate complete variant object.
    
    Works with VariantData model: ref_allele, alt_allele (not reference/alternate).
    """
    try:
        if not hasattr(variant, "chromosome"):
            if raise_on_error:
                raise ValidationError("Missing chromosome attribute")
            return False
        if not hasattr(variant, "position"):
            if raise_on_error:
                raise ValidationError("Missing position attribute")
            return False
        
        if not validate_chromosome(variant.chromosome):
            if raise_on_error:
                raise ValidationError(f"Invalid chromosome: {variant.chromosome}")
            return False
        
        try:
            pos = int(variant.position)
            if pos < 1:
                if raise_on_error:
                    raise ValidationError(f"Invalid position: {pos}")
                return False
        except (ValueError, TypeError):
            if raise_on_error:
                raise ValidationError(f"Position must be integer: {variant.position}")
            return False
        
        chrom_norm = str(variant.chromosome).upper().replace("CHR", "")
        max_pos = CHROMOSOME_LENGTHS.get(chrom_norm, 300000000)
        if pos > max_pos:
            if raise_on_error:
                raise ValidationError(f"Position exceeds chromosome length")
            return False
        
        # Check assembly
        if hasattr(variant, "assembly") and variant.assembly:
            if not validate_assembly(variant.assembly):
                if raise_on_error:
                    raise ValidationError(f"Invalid assembly: {variant.assembly}")
                return False
        
        # Validate alleles - if alt is present, ref must also be present
        has_ref = hasattr(variant, "ref_allele") and variant.ref_allele
        has_alt = hasattr(variant, "alt_allele") and variant.alt_allele
        
        if has_alt and not has_ref:
            if raise_on_error:
                raise ValidationError("Alternate allele present but missing reference allele")
            return False
        
        if has_ref:
            if not validate_reference_allele(variant.ref_allele):
                if raise_on_error:
                    raise ValidationError(f"Invalid reference allele: {variant.ref_allele}")
                return False
        
        if has_alt:
            if not validate_alternate_allele(variant.alt_allele):
                if raise_on_error:
                    raise ValidationError(f"Invalid alternate allele: {variant.alt_allele}")
                return False
        
        return True
        
    except ValidationError:
        raise
    except Exception as e:
        if raise_on_error:
            raise ValidationError(f"Validation error: {e}")
        return False'''
    
    content = content.replace(old_func, new_func)
    
    with open(validators_file, 'w') as f:
        f.write(content)
    
    return "✓ Updated validate_variant() to raise exceptions when raise_on_error=True"


if __name__ == "__main__":
    import subprocess
    
    print("=" * 70)
    print("Final Fixes for Last 4 Tests")
    print("=" * 70)
    print()
    
    print(fix_validate_variant_raise())
    print()
    
    print("Formatting...")
    subprocess.run(["black", "varidex/pipeline/validators.py"], capture_output=True)
    print("✓ Formatted")
    print()
    
    print("=" * 70)
    print("FINAL TEST RUN")
    print("=" * 70)
    result = subprocess.run([
        "pytest", "tests/test_pipeline_validators.py", "-v"
    ])
    
    print()
    if result.returncode == 0:
        print()
        print("=" * 80)
        print(" " * 15 + "🎉 🎉 🎉  ALL 42 TESTS PASSING!  🎉 🎉 🎉")
        print("=" * 80)
        print()
        print("Validators Module: COMPLETE ✅")
        print()
        print("Test Coverage:")
        print("  ✓ Chromosome validation (5 tests)")
        print("  ✓ Coordinate validation (6 tests)")
        print("  ✓ Reference allele validation (8 tests)")
        print("  ✓ Assembly validation (5 tests)")
        print("  ✓ Variant validation (6 tests)")
        print("  ✓ VCF file validation (6 tests)")
        print("  ✓ Edge cases (5 tests)")
        print("  ✓ Performance (2 tests)")
        print()
        print("Ready to commit!")
        print("  git add -A")
        print("  git commit -m 'Complete validators implementation - 42/42 tests passing'")
        print()
    else:
        print("=" * 70)
        print("Check remaining failures above")
        print("=" * 70)
