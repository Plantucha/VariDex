# VariDex v6.0.0 - PRODUCTION READY (Feb 1, 2026)

## Working Command
python3 -m varidex.pipeline \
    --user-genome data/rawM.txt \
    --gnomad-dir gnomad/ \
    --output resultsFINAL/ \
    --force-reload

## Expected Output
- 17,449 matched variants
- gnomAD: BA1=4433, BS1=644, PM2=1609
- Files: results_13codes.csv, PRIORITY_PVS1.csv, PRIORITY_PM2.csv

## Key Files (Keep These)
- varidex/pipeline/__main__.py (current version)
- varidex/pipeline/gnomad_stage.py (current version)
