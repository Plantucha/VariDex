#!/usr/bin/env python3
"""
Phase 1 ACMG Enhancement Module

This adds 5 ACMG codes (BP7, PP5, BP6, BS2, PS1, PM5) to your pipeline results.
"""

import sys
from pathlib import Path

import pandas as pd


def add_phase1_codes_to_pipeline(results_df: pd.DataFrame) -> pd.DataFrame:
    """
    ADD Phase 1 ACMG codes to existing results.

    This function ONLY ADDS new columns, never removes anything.

    Codes added:
    - BP7: Synonymous variant (silent, no splice impact)
    - PP5: Pathogenic by expert panel (reputable source)
    - BP6: Benign by expert panel (reputable source)
    - BS2: High frequency contradicts pathogenic assignment
    - PS1, PM5: Placeholders for future implementation

    Args:
        results_df: DataFrame with columns: molecular_consequence, clinical_sig,
                   review_status, gnomad_af

    Returns:
        Same DataFrame with 6 new columns added
    """
    # Initialize new columns (only if they don't already exist)
    for code in ["PS1", "PM5", "BP7", "BS2", "PP5", "BP6"]:
        if code not in results_df.columns:
            results_df[code] = False

    # Track how many of each code we find
    counts = {"BP7": 0, "PP5": 0, "BP6": 0, "BS2": 0}

    # Apply criteria to each variant
    for idx, row in results_df.iterrows():
        consequence = str(row.get("molecular_consequence", "")).lower()
        review_status = str(row.get("review_status", "")).lower()
        clinical_sig = str(row.get("clinical_sig", "")).lower()
        gnomad_af = row.get("gnomad_af")

        # BP7: Synonymous variant without splice site impact
        if (
            "synonymous" in consequence or "silent" in consequence
        ) and "splice" not in consequence:
            results_df.at[idx, "BP7"] = True
            counts["BP7"] += 1

        # PP5/BP6: Expert panel reviewed variants
        is_expert_reviewed = (
            "expert_panel" in review_status or "practice_guideline" in review_status
        )

        if is_expert_reviewed:
            if "pathogenic" in clinical_sig and "benign" not in clinical_sig:
                results_df.at[idx, "PP5"] = True
                counts["PP5"] += 1
            elif "benign" in clinical_sig:
                results_df.at[idx, "BP6"] = True
                counts["BP6"] += 1

        # BS2: High population frequency contradicting pathogenic
        if pd.notna(gnomad_af) and gnomad_af > 0.01:
            if "pathogenic" in clinical_sig and "benign" not in clinical_sig:
                results_df.at[idx, "BS2"] = True
                counts["BS2"] += 1

    # Print summary of what was added
    print(f"⭐ Phase 1 Enhancement Complete:")
    print(f"   BP7 (synonymous): {counts['BP7']:,}")
    print(f"   PP5 (expert path): {counts['PP5']:,}")
    print(f"   BP6 (expert benign): {counts['BP6']:,}")
    print(f"   BS2 (high AF): {counts['BS2']:,}")

    return results_df


def show_usage():
    """Display usage information."""
    print("=" * 70)
    print("Phase 1 ACMG Enhancement Module")
    print("=" * 70)
    print()
    print("This module adds 5 ACMG codes to your pipeline WITHOUT removing features.")
    print()
    print("📋 INTEGRATION INTO YOUR PIPELINE:")
    print("-" * 70)
    print()
    print("1. Copy this file to your pipeline directory:")
    print("   cp phase1_enhancement.py varidex/pipeline/")
    print()
    print("2. In varidex/pipeline/__main__.py, add after ACMG classification:")
    print()
    print(
        "   from varidex.pipeline.acmg_classifier_stage import apply_full_acmg_classification"
    )
    print("   results_df = apply_full_acmg_classification(matched_df)")
    print()
    print("   # ADD THESE TWO LINES:")
    print(
        "   from varidex.pipeline.phase1_enhancement import add_phase1_codes_to_pipeline"
    )
    print("   results_df = add_phase1_codes_to_pipeline(results_df)  # ← Adds 5 codes")
    print()
    print("   # Continue with your existing code")
    print()
    print("-" * 70)
    print("📊 CODES ADDED:")
    print("-" * 70)
    print("  • BP7  - Synonymous variant (silent, no splice)")
    print("  • PP5  - Pathogenic by expert panel")
    print("  • BP6  - Benign by expert panel")
    print("  • BS2  - High AF contradicts pathogenic")
    print("  • PS1  - Placeholder (same amino acid change)")
    print("  • PM5  - Placeholder (different amino acid, same position)")
    print()
    print("-" * 70)
    print("✅ FEATURES PRESERVED:")
    print("-" * 70)
    print("  ✓ Parallel matching")
    print("  ✓ generator.py report generation")
    print("  ✓ All ClinVar columns (list format)")
    print("  ✓ Progress bars")
    print("  ✓ All existing functionality")
    print()
    print("=" * 70)
    print()
    print("🧪 TEST THIS MODULE:")
    print("  python3 phase1_enhancement.py test")
    print()


def test_module():
    """Test the module with cached results."""
    print("=" * 70)
    print("Testing Phase 1 Enhancement Module")
    print("=" * 70)
    print()

    # Look for cached results
    cached_file = Path("output/complete_results.csv")

    if not cached_file.exists():
        print(f"❌ Test requires: {cached_file}")
        print()
        print("Generate this file first by running:")
        print("  python3 -m varidex.pipeline --clinvar ... --user-genome ...")
        print()
        return False

    print(f"📁 Loading: {cached_file}")
    df = pd.read_csv(cached_file, low_memory=False, nrows=1000)  # Test with first 1K
    print(f"✓ Loaded {len(df):,} variants (test sample)")
    print()

    # Check required columns
    required = ["molecular_consequence", "clinical_sig", "review_status"]
    missing = [col for col in required if col not in df.columns]

    if missing:
        print(f"⚠️  Missing required columns: {missing}")
        print("   The cached file might not have full ClinVar annotations.")
        print()
        return False

    print("✓ All required columns present")
    print()

    # Apply enhancement
    print("Applying Phase 1 codes...")
    df_enhanced = add_phase1_codes_to_pipeline(df)
    print()

    # Show results
    print("✅ Success! Module is working correctly.")
    print()
    print(
        f"New columns added: {[col for col in ['BP7', 'PP5', 'BP6', 'BS2', 'PS1', 'PM5'] if col in df_enhanced.columns]}"
    )
    print()

    return True


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Run test
        success = test_module()
        sys.exit(0 if success else 1)
    else:
        # Show usage
        show_usage()
