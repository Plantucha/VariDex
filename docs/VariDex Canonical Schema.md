# VariDex Canonical Schema (v6)

Purpose: define ONE internal schema for package-mode runtime.
All modules may accept many input headers, but must map them into this schema.
No module should invent new column names or VariantData field names.

This contract is designed to support:
- v6 ACMG 2015 rule-based outputs
- future v7 extensions (ACMG 2015 full coverage and/or ACMG 2024 points) as OPTIONAL fields

## Canonical VariantData fields
Source of truth: `varidex.core.models.VariantData`.

Required for classification (v6)
- rsid (str)
- chromosome (str)
- position (str/int)
- genotype (str)
- gene (str)
- clinical_sig (str)
- review_status (str)
- num_submitters (int)
- variant_type (str)
- molecular_consequence (str)

Optional but recommended
- ref_allele (str)
- alt_allele (str)
- star_rating (int)
- normalized_genotype (str)
- genotype_class (str)
- zygosity (str)

Optional (future-proof; DO NOT require in v6)
- acmg_version (str)  # e.g. "2015" or "2024"
- total_points (int)  # points-based systems
- point_breakdown (str)  # "PVS1:8|PS1:4"
- gnomad_af (float)  # population AF
- population_af (float)  # alias of gnomad_af if desired
- gnomad_mode (str)  # "api" or "local"
- in_silico_scores (str/JSON)  # REVEL/CADD/etc

## Canonical DataFrame schemas

### 1) ClinVar DataFrame (stage2 output)
Must contain (additional columns allowed)
- chromosome (string)
- position (Int64 or int)
- ref_allele (string)
- alt_allele (string)
- coord_key (string)  # canonical join key

Strongly recommended if available
- rsid
- gene
- clinical_sig
- review_status
- variant_type
- molecular_consequence
- num_submitters
- star_rating

Optional future (not required)
- gnomad_af
- in_silico_scores

### 2) User DataFrame (stage3 output)
Must contain
- chromosome
- position
- genotype

At least one of
- rsid
- (ref_allele and alt_allele)

Recommended
- coord_key (if ref/alt known)
- zygosity
- normalized_genotype

### 3) Matched DataFrame (stage4 output)
Must contain everything needed to build VariantData
- rsid (can be empty if coordinate-only match)
- chromosome
- position
- genotype
- gene
- clinical_sig
- review_status
- variant_type
- molecular_consequence

Recommended
- ref_allele
- alt_allele
- coord_key
- num_submitters
- star_rating

Optional future (not required)
- acmg_version
- total_points
- point_breakdown
- gnomad_af
- in_silico_scores

## Alias policy
Each boundary module implements a local alias map to convert input headers into canonical columns.
- Do not delete input columns.
- Do not rename canonical columns downstream.
- If multiple candidate columns exist, prefer the one closest to VCF/ClinVar standards.

## Validation policy
Every stage boundary should validate minimal required columns before returning.
Fail fast with `varidex.exceptions.ValidationError`.
