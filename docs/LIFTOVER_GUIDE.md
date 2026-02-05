# VariDex Liftover Guide (Development)

## Overview

The VariDex liftover utility converts genomic coordinates between reference genome builds (GRCh37 ↔ GRCh38) for 23andMe raw data files.

## Why Liftover?

- **23andMe uses GRCh37**: Most 23andMe raw data is in GRCh37 (hg19) coordinates
- **ClinVar uses GRCh38**: Modern ClinVar releases use GRCh38 (hg38) coordinates
- **Coordinate matching fails**: Direct comparison requires same reference build

## Installation

```bash
pip install pyliftover





q
