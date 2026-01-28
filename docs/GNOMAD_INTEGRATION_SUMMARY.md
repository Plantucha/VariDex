# gnomAD Integration Summary

**Date**: January 28, 2026  
**Version**: 6.4.0-dev

## Overview
Integrated gnomAD v2.1.1 exomes database (59GB, 125,748 samples) to enable population frequency-based ACMG variant classification.

## ACMG Criteria Implemented

| Criterion | Threshold | Strength | Count |
|-----------|-----------|----------|-------|
| BA1 | >5% | Stand-alone Benign | 4,431 |
| BS1 | >1% | Strong Benign | 644 |
| PM2 | <0.01% | Moderate Pathogenic | 1,611 |
| PVS1 | LOF | Very Strong Pathogenic | 2,015 |
| BP7 | Synonymous | Supporting Benign | 2,403 |

## Results
- 8,297/17,458 variants annotated (47.5%)
- 1,987 pathogenic variants identified
- 102 VUS upgraded with new evidence
- 35 cancer predisposition variants

## Technical Details
- Query speed: ~80 variants/second
- Database format: Tabix-indexed VCF
- Dependencies: pysam, pandas, tqdm
