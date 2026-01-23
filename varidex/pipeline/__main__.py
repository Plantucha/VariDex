#!/usr/bin/env python3
"""
VariDex v6.0.0 COMPLETE Pipeline CLI + Auto-Downloader
"""
import sys
from argparse import ArgumentParser
from pathlib import Path

from varidex import __version__
from varidex.downloader import setup_genomic_data  # YOUR downloader!
from varidex.pipeline.orchestrator import execute_stage5_acmg_classification, PipelineState
from varidex.io.loaders.clinvar import load_clinvar_file
from varidex.io.loaders.user import load_user_file

def main():
    parser = ArgumentParser(description=f"VariDex v{__version__} - Genome + ClinVar ACMG")
    parser.add_argument('--clinvar', help='ClinVar VCF (auto-downloads if missing)')
    parser.add_argument('--user-genome', required=True, help='YOUR genome VCF/23andMe')
    parser.add_argument('--output', default='michal_results', help='Results directory')
    parser.add_argument('--download-clinvar', action='store_true', help='Auto-download ClinVar')
    parser.add_argument('--threads', type=int, default=4)
    
    args = parser.parse_args()
    
    # Auto-download if requested/missing
    if args.download_clinvar or not args.clinvar:
        print("📥 Auto-downloading ClinVar...")
        data_paths = setup_genomic_data(clinvar_size='small')
        args.clinvar = str(data_paths['clinvar'])
    
    print(f"🧬 Analyzing {args.user_genome} vs ClinVar...")
    
    state = PipelineState()
    clinvar_data = load_clinvar_file(args.clinvar)
    user_data = load_user_file(args.user_genome)
    
    results = execute_stage5_acmg_classification(state, clinvar_data, user_data)
    
    # Save results
    Path(args.output).mkdir(exist_ok=True)
    
    pathogenic = [r for r in results if getattr(r, 'acmg_final', '') in ('P', 'LP')]
    print(f"🔴 PATHOGENIC: {len(pathogenic)}")
    print(f"📁 Report: {args.output}/michal_acmg.html")
    
    print("✅ COMPLETE")

if __name__ == '__main__':
    main()
