"""
VariDex Pipeline Module
=======================

7-stage variant analysis pipeline orchestration.

Stages:
    1. Load ClinVar data
    2. Load user genome data  
    3. Match variants (hybrid rsID + coordinates)
    4. Classify variants (ACMG 2015)
    5. Generate reports
    6. Save checkpoints
    7. Cleanup

Usage:
    from varidex.pipeline import run_pipeline

    results = run_pipeline(
        clinvar_file="clinvar.vcf.gz",
        user_file="genome.txt",
        output_dir="./results"
    )
"""

from varidex.version import get_version

__version__ = get_version("pipeline")

def run_pipeline(*args, **kwargs):
    """Run the complete variant analysis pipeline. Lazy import wrapper."""
    from varidex.pipeline.orchestrator import run_pipeline as _run
    return _run(*args, **kwargs)

__all__ = ["run_pipeline"]
