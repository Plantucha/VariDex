#!/bin/bash
# Complete workflow: Liftover + ClinVar analysis

echo "🧬 VariDex Complete Workflow: Liftover + Analysis"
echo "=================================================="

# Step 1: Liftover GRCh37 to GRCh38
echo "Step 1: Converting coordinates GRCh37 → GRCh38..."
python3 varidex/utils/liftover.py data/rawM.txt --target GRCh38

# Step 2: Run ClinVar analysis
echo -e "\nStep 2: Running ClinVar analysis..."
python3 -m varidex.pipeline.orchestrator \
    clinvar_GRCh38.vcf \
    "varidex/utils/liftover_output/rawM_liftover_GRCh38.txt"

echo -e "\n✅ Workflow complete! Check results/ directory"
